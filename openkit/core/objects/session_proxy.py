import logging
from datetime import datetime, timedelta
from threading import RLock
from typing import Optional, TYPE_CHECKING

from .null_root_action import NullRootAction
from .null_web_request_tracer import NullWebRequestTracer
from .session import SessionImpl
from .session_creator import SessionCreator
from ..beacon_sender import BeaconSender
from ..configuration import ServerConfiguration
from ..configuration.server_configuration import ServerConfigurationUpdateCallback
from ...api.composite import OpenKitComposite
from ...api.openkit_object import OpenKitObject
from ...api.root_action import RootAction
from ...api.session import Session
from ...api.web_request_tracer import WebRequestTracer

if TYPE_CHECKING:
    from ..session_watchdog import SessionWatchdog


class SessionProxy(ServerConfigurationUpdateCallback, Session):

    def __init__(self,
                 logger: logging.Logger,
                 parent: OpenKitComposite,
                 session_creator: SessionCreator,
                 beacon_sender: BeaconSender,
                 session_watchdog: "SessionWatchdog",
                 device_id: Optional[int] = None,
                 timestamp: Optional[datetime] = None):
        super().__init__()

        self.current_session: Optional[SessionImpl] = None
        self.logger = logger
        self.parent = parent
        self.session_creator = session_creator
        self.beacon_sender = beacon_sender
        self.session_watchdog = session_watchdog
        self.device_id = device_id
        self.timestamp = timestamp

        self.last_interaction_time: datetime = datetime.now()
        self.top_level_action_count = 0

        self.finished = False
        self.last_user_tag = None
        self.lock = RLock()

        self.server_config: Optional[ServerConfiguration] = None
        current_server_config = beacon_sender.last_server_configuration
        self.create_and_assign_current_session(current_server_config, None)

    def create_and_assign_current_session(self,
                                          initial_config: Optional[ServerConfiguration],
                                          updated_config: Optional[ServerConfiguration]):
        session = self.session_creator.create_session(self, self.device_id, self.timestamp)
        beacon = session.beacon
        beacon.set_server_config_update_callback(self)
        self._store_child_in_list(session)

        self.last_interaction_time = beacon.session_start_time
        self.top_level_action_count = 0

        if initial_config is not None:
            session.initialize_server_config(initial_config)

        if updated_config is not None:
            session.update_server_config(updated_config)

        with self.lock:
            self.current_session = session

        self.beacon_sender.add_session(session)

    def on_server_configuration_update(self, server_configuration: ServerConfiguration):
        # TODO - Implement Merge
        pass

    def enter_action(self, name: str, timestamp: Optional[datetime] = None) -> RootAction:
        if not name:
            self.logger.warning("action name must not be empty")
            return NullRootAction()

        self.logger.debug(f"enter_action({name}, {timestamp})")
        with self.lock:
            if not self.finished:
                session = self.get_or_split_current_session_by_events()
                return session.enter_action(name, timestamp)

        return NullRootAction()

    def identify_user(self, name: str, timestamp: Optional[datetime] = None) -> None:
        self.logger.debug(f"identify_user({name}, {timestamp})")
        with self.lock:
            if not self.finished:
                session = self.get_or_split_current_session_by_events()
                self.record_top_level_event_interaction()
                session.identify_user(name, timestamp)
                self.last_user_tag = name

    def report_crash(self, error_name, reason: str, stacktrace: str, timestamp: Optional[datetime] = None) -> None:
        raise NotImplementedError

    def trace_web_request(self, url: str, timestamp: Optional[datetime] = None) -> WebRequestTracer:
        if not url:
            self.logger.warning("url must not be empty")
            return NullWebRequestTracer()

        self.logger.debug(f"trace_web_request({url}, {timestamp})")

        with self.lock:
            if not self.finished:
                session = self.get_or_split_current_session_by_events()
                self.record_top_level_event_interaction()
                return session.trace_web_request(url, timestamp)

        return NullWebRequestTracer()

    def end(self, send_end_event: bool = True, timestamp: Optional[datetime] = None):
        self.logger.debug("end()")
        with self.lock:
            if self.finished:
                return

        self.close_child_objects(timestamp)
        self.parent._on_child_closed(self)
        self.session_watchdog.remove_from_split_by_timeout(self)

    def _close(self):
        self.end()

    def _on_child_closed(self, child: OpenKitObject):
        with self.lock:
            self._remove_child_from_list(child)
            if isinstance(child, SessionImpl):
                self.session_watchdog.dequeue_from_closing(child)

    def record_top_level_event_interaction(self):
        self.last_interaction_time = datetime.now()

    def record_top_action_event(self):
        self.top_level_action_count += 1
        self.record_top_level_event_interaction()

    def retag_current_session(self):
        if not self.last_user_tag or self.current_session is None:
            return
        self.current_session.identify_user(self.last_user_tag)

    def get_or_split_current_session_by_events(self) -> SessionImpl:
        if self.split_by_event_required():
            self.close_or_enqueue_current_session_for_closing()
            self.create_split_session_and_make_current()
            self.retag_current_session()

        return self.current_session

    def split_by_event_required(self) -> bool:
        if not self.server_config or not self.server_config.session_split_by_events_enabled:
            return False
        return self.server_config.max_events_per_session <= self.top_level_action_count

    def close_or_enqueue_current_session_for_closing(self):
        close_grace_period = 0
        if self.server_config.session_timeout_in_milliseconds > 0:
            close_grace_period = self.server_config.session_timeout_in_milliseconds / 2
        else:
            close_grace_period = self.server_config.send_interval_in_milliseconds

        self.session_watchdog.close_or_enqueue_for_closing(self.current_session, close_grace_period)

    def create_split_session_and_make_current(self):
        self.create_and_assign_current_session(None, self.server_config)

    def close_child_objects(self, timestamp: Optional[datetime] = None):
        children = self._copy_children()

        for child in children:
            if isinstance(child, SessionImpl):
                child.end(child == self.current_session, timestamp)
            else:
                child._close()

    def split_session_by_time(self) -> datetime:
        with self.lock:
            if self.finished:
                return datetime(1970, 1, 1)

        next_split_time = self.calculate_next_split_time()
        now = datetime.now()
        if next_split_time > now:
            return next_split_time

        self.split_and_create_initial_session()
        return self.calculate_next_split_time()

    def calculate_next_split_time(self) -> datetime:
        if self.server_config is None:
            return datetime(1970, 1, 1)

        split_by_idle_timeout = self.server_config.session_split_by_idle_timeout_enabled
        split_by_session_duration = self.server_config.session_split_by_session_duration_enabled

        idle_timeout = self.last_interaction_time + timedelta(milliseconds=self.server_config.session_timeout_in_milliseconds)
        session_max_time = self.current_session.beacon.session_start_time + timedelta(milliseconds=self.server_config.max_session_duration_in_milliseconds)

        self.logger.debug(f"calculate_next_split_time: idle_timeout={idle_timeout}, session_max_time={session_max_time}")

        if split_by_idle_timeout and split_by_session_duration:
            return min(idle_timeout, session_max_time)
        elif split_by_idle_timeout:
            return idle_timeout
        elif split_by_session_duration:
            return session_max_time

        return datetime(1970, 1, 1)

    def split_and_create_initial_session(self):
        self.close_or_enqueue_current_session_for_closing()

        self.session_creator.reset()
        self.create_initial_session_and_make_current(self.server_config)
        self.retag_current_session()

    def create_initial_session_and_make_current(self, server_config):
        self.create_and_assign_current_session(server_config, None)
