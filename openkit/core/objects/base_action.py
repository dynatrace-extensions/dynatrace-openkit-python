import logging
from datetime import datetime
from threading import RLock
from typing import Optional, Union

from .null_web_request_tracer import NullWebRequestTracer
from .web_request_tracer import WebRequestTracer, WebRequestTracerImpl
from ...api.action import Action
from ...api.composite import OpenKitComposite
from ...api.openkit_object import CancelableOpenKitObject, OpenKitObject
from ...protocol.beacon import Beacon


class BaseAction(OpenKitComposite, CancelableOpenKitObject, Action):

    def __init__(self, logger: logging.Logger, parent: OpenKitComposite, name: str, beacon: Beacon,
                 timestamp: Optional[datetime] = None):
        super().__init__()
        self.logger: logging.Logger = logger
        self.parent: OpenKitComposite = parent
        self.parent_action_id: int = parent.id

        self.id: int = beacon.create_id()
        self.end_sequence_number: int = -1
        self.name: str = name

        if timestamp is None:
            timestamp = datetime.now()
        self.start_time: datetime = timestamp
        self.end_time: Optional[datetime] = None

        self.start_sequence_number: int = beacon.next_sequence_number
        self.was_left = False

        self.beacon = beacon
        self.lock = RLock()

    def _on_child_closed(self, child: OpenKitObject):
        with self.lock:
            self._remove_child_from_list(child)

    def _cancel(self):
        self._cancel_action()

    def _close(self):
        self.leave_action()

    def report_event(self, event_name: str, timestamp: Optional[datetime] = None) -> "Action":
        if not event_name:
            self.logger.warning(f"event_name must not be empty")
            return self

        self.logger.debug(f"report_event({event_name})")
        with self.lock:
            if not self.was_left:
                self.beacon.report_event(self.id, event_name, timestamp)

    def report_value(self,
                     value_name: str,
                     value: Union[str, int, float],
                     timestamp: Optional[datetime] = None) -> "Action":
        if not value_name:
            self.logger.warning(f"value_name must not be empty")
            return self

        self.logger.debug(f"report_value({value_name}, {value})")
        with self.lock:
            if not self.was_left:
                self.beacon.report_value(self.id, value_name, value, timestamp)

    def report_error(self,
                     error_name: str,
                     error_code: int,
                     reason: str,
                     timestamp: Optional[datetime] = None) -> "Action":
        if not error_name:
            self.logger.warning(f"error_name must not be empty")
            return self

        self.logger.debug(f"report_error({error_name}, {error_code}, {reason})")
        with self.lock:
            if not self.was_left:
                self.beacon.report_error(self.id, error_name, error_code, reason, timestamp)

    def trace_web_request(self, url: str, timestamp: Optional[datetime] = None) -> WebRequestTracer:
        if not url:
            self.logger.warning(f"url must not be empty")
            return NullWebRequestTracer()

        self.logger.debug(f"trace_web_request({url})")
        with self.lock:
            if not self.was_left:
                web_request_tracer = WebRequestTracerImpl(self.logger, self, url, self.beacon, timestamp)
                self._store_child_in_list(web_request_tracer)
                return web_request_tracer

        return NullWebRequestTracer()

    def leave_action(self, timestamp: Optional[datetime] = None) -> Optional["Action"]:
        self.logger.debug(f"leave_action({self.name})")
        return self.do_leave_action(False, timestamp)

    def _cancel_action(self) -> Optional["Action"]:
        self.logger.debug(f"cancel_action({self.name})")
        return self.do_leave_action(True)

    def _get_duration_in_milliseconds(self) -> int:
        with self.lock:
            if self.was_left:
                return int((self.end_time - self.start_time).total_seconds() * 1000)
            return int((datetime.now() - self.start_time).total_seconds() * 1000)

    def do_leave_action(self, discard: bool, timestamp: Optional[datetime] = None) -> Optional["Action"]:
        with self.lock:
            if self.was_left:
                return None
            self.was_left = True

        children = self._copy_children()
        for child in children:
            if discard:
                if isinstance(child, CancelableOpenKitObject):
                    child._cancel()
                else:
                    self.logger.warning(f"closing non cancelable child {child}")
                    child._close()
            else:
                child._close()

        if timestamp is None:
            timestamp = datetime.now()

        self.end_time = timestamp
        self.end_sequence_number = self.beacon.next_sequence_number

        if not discard:
            self.beacon.add_action(self)

        self.parent._on_child_closed(self)
        self.parent = None

        return None
