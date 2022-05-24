import logging
from datetime import datetime
from threading import RLock
from typing import Optional

from .null_root_action import NullRootAction
from .null_web_request_tracer import NullWebRequestTracer
from .root_action import RootActionImpl
from .web_request_tracer import WebRequestTracerImpl
from ...api.composite import OpenKitComposite
from ...api.openkit_object import OpenKitObject
from ...api.root_action import RootAction
from ...api.session import Session
from ...api.web_request_tracer import WebRequestTracer
from ...protocol.beacon import Beacon


class SessionImpl(Session, OpenKitComposite):

    def __init__(self, logger: logging.Logger, parent: OpenKitComposite, beacon: Beacon):
        super().__init__()
        self.state = SessionState(self)
        self.logger = logger
        self.parent = parent
        self.beacon = beacon

        self._split_by_events_grace_period_end_time: Optional[datetime] = None
        self.beacon.start_session()

    def enter_action(self, name: str, timestamp: Optional[datetime] = None) -> RootAction:
        if not name:
            self.logger.warning("action name must not be empty")
            return NullRootAction()

        self.logger.debug(f"enter_action({name})")

        if not self.state.is_finishing_or_finished:
            action = RootActionImpl(self.logger, self, name, self.beacon, timestamp)
            self._store_child_in_list(action)
            return action

        return NullRootAction()

    def identify_user(self, name: str, timestamp: Optional[datetime] = None) -> None:
        self.logger.debug(f"identify_user({name}, {timestamp})")
        if not self.state.is_finishing_or_finished:
            self.beacon.identify_user(name, timestamp)

    def report_crash(self, error_name, reason: str, stacktrace: str, timestamp: Optional[datetime] = None) -> None:
        if not error_name:
            self.logger.warning("error name must not be empty")
            return

        self.logger.debug(f"report_crash({error_name}, {reason}, {stacktrace})")
        if not self.state.is_finishing_or_finished:
            # .beacon.report_crash(error_name, reason, stacktrace, timestamp)
            # TODO - beacon.report_crash
            raise NotImplementedError

    def trace_web_request(self, url: str, timestamp: Optional[datetime] = None) -> WebRequestTracer:
        if not url:
            self.logger.warning("url must not be empty")
            return NullWebRequestTracer()

        self.logger.debug(f"trace_web_request({url})")
        if not self.state.is_finishing_or_finished:
            tracer = WebRequestTracerImpl(self.logger, self, url, self.beacon, timestamp)
            self._store_child_in_list(tracer)
            return tracer

        return NullWebRequestTracer()

    def end(self, send_end_event: bool = True, timestamp: Optional[datetime] = None):
        self.logger.debug("end()")

        if not self.state.mark_as_finishing():
            return

        children = self._copy_children()
        for child in children:
            child._close()

        if send_end_event:
            self.beacon.end_session()

        self.state.mark_as_finished()
        self.parent._on_child_closed(self)
        self.parent = None

    def try_end(self) -> bool:
        if self.state.is_finishing_or_finished:
            return True

        if self._child_count == 0:
            self.end(send_end_event=False)
            return True

        self.state.mark_was_tried_for_ending()
        return False

    # TODO - Send Biz event
    # TODO - Other beacon and config methods

    def _close(self):
        self.end()

    def _on_child_closed(self, child: OpenKitObject):
        self._remove_child_from_list(child)

        if self.state.was_tried_for_ending and self._child_count == 0:
            self.end(False)

    def initialize_server_config(self, initial_config):
        self.beacon.initialize_server_config(initial_config)

    def update_server_config(self, updated_config):
        self.beacon.update_server_config(updated_config)

    def clear_captured_data(self):
        self.beacon.clear_data()

    def update_server_configuration(self, new_server_config):
        self.beacon.update_server_configuration(new_server_config)

    @property
    def data_sending_allowed(self) -> bool:
        return self.state.is_configured and self.beacon.data_capturing_enabled

    def send_beacon(self, http_client, context):
        return self.beacon.send(http_client, context)

    def enable_capture(self):
        self.beacon.enable_capture()

    @property
    def split_by_events_grace_period_end_time(self) -> datetime:
        return self._split_by_events_grace_period_end_time


class SessionState:

    def __init__(self, session: SessionImpl):
        self.session = session
        self._is_finishing: bool = False
        self._is_finished: bool = False
        self._was_tried_for_ending: bool = False

        self._lock = RLock()

    @property
    def was_tried_for_ending(self) -> bool:
        with self._lock:
            return self._was_tried_for_ending

    @property
    def is_configured(self) -> bool:
        with self._lock:
            return self.session.beacon.server_configuration_set

    @property
    def is_configured_and_finished(self) -> bool:
        return self.is_configured and self.is_finished

    @property
    def is_configured_and_open(self) -> bool:
        return self.is_configured and not self.is_finished

    @property
    def is_finished(self) -> bool:
        with self._lock:
            return self._is_finished

    @property
    def is_finishing_or_finished(self) -> bool:
        with self._lock:
            return self._is_finishing or self._is_finished

    def mark_as_finishing(self) -> bool:
        if self.is_finishing_or_finished:
            return False
        with self._lock:
            self._is_finishing = True
            return True

    def mark_as_finished(self):
        with self._lock:
            self._is_finished = True

    def mark_was_tried_for_ending(self):
        with self._lock:
            self._was_tried_for_ending = True
