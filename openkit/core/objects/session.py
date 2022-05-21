import logging
from datetime import datetime
from threading import RLock
from typing import Optional

from .composite import OpenKitComposite
from ...api.openkit_object import OpenKitObject
from ...api.root_action import RootAction
from ...api.session import Session
from ...api.web_request_tracer import WebRequestTracer
from ...protocol.beacon import Beacon


class SessionImpl(Session, OpenKitComposite):

    def __init__(self, logger: logging.Logger, parent: OpenKitComposite, beacon: Beacon):
        super().__init__()
        self._state = SessionState(self)
        self._logger = logger
        self._parent = parent
        self._beacon = beacon

        self._beacon.start_session()

    def enter_action(self, name: str, timestamp: Optional[datetime] = None) -> RootAction:
        raise NotImplementedError

    def identify_user(self, name: str, timestamp: Optional[datetime] = None) -> None:
        raise NotImplementedError

    def report_crash(self, error_name, reason: str, stacktrace: str, timestamp: Optional[datetime] = None) -> None:
        raise NotImplementedError

    def trace_web_request(self, url: str, timestamp: Optional[datetime] = None) -> WebRequestTracer:
        raise NotImplementedError

    def end(self, send_end_event: bool = True, timestamp: Optional[datetime] = None):
        self._logger.debug("end()")

        if not self._state.mark_as_finishing():
            return

        children = self._copy_children()
        for child in children:
            child.close()

        if send_end_event:
            self._beacon.end_session()

        self._state.mark_as_finished()
        self._parent._on_child_closed(self)
        self._parent = None

    # TODO - try_end for watchdog

    def close(self):
        self.end()

    def _on_child_closed(self, child: OpenKitObject):
        raise NotImplementedError


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
            raise NotImplementedError("is_configured() not implemented")

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
