import logging
from datetime import datetime
from threading import RLock
from typing import Optional

from .session import SessionImpl
from .session_creator import SessionCreator
from ..beacon_sender import BeaconSender
from ..configuration import ServerConfiguration
from ..configuration.server_configuration import ServerConfigurationUpdateCallback
from ...api.openkit_object import OpenKitObject
from ...api.root_action import RootAction
from ...api.session import Session
from ...api.web_request_tracer import WebRequestTracer


class SessionProxy(ServerConfigurationUpdateCallback, Session):

    def __init__(self,
                 logger: logging.Logger,
                 parent: OpenKitObject,
                 session_creator: SessionCreator,
                 beacon_sender: BeaconSender,
                 device_id: Optional[int] = None,
                 timestamp: Optional[datetime] = None):
        super().__init__()

        self.current_session = None
        self.logger = logger
        self.parent = parent
        self.session_creator = session_creator
        self.beacon_sender = beacon_sender
        self.device_id = device_id
        self.timestamp = timestamp

        self.last_interaction_time: datetime = datetime.now()
        self.top_level_action_count = 0

        self.finished = False
        self.last_user_tag = None

        self.server_config: Optional[ServerConfiguration] = None
        current_server_config = beacon_sender.last_server_configuration
        self.create_and_assign_current_session(current_server_config, None)

        self.lock = RLock()

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
        pass

    def identify_user(self, name: str, timestamp: Optional[datetime] = None) -> None:
        pass

    def report_crash(self, error_name, reason: str, stacktrace: str, timestamp: Optional[datetime] = None) -> None:
        pass

    def trace_web_request(self, url: str, timestamp: Optional[datetime] = None) -> WebRequestTracer:
        pass

    def end(self, send_end_event: bool = True, timestamp: Optional[datetime] = None):
        pass

    def close(self):
        pass

    def _on_child_closed(self, child: OpenKitObject):
        pass

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
        pass

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

        # TODO sessionWatchdog.closeOrEnqueueForClosing(currentSession, closeGracePeriodInMillis);
