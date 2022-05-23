import logging
from datetime import datetime
from threading import RLock
from typing import Optional

from ...api.composite import OpenKitComposite
from ...api.openkit_object import CancelableOpenKitObject
from ...api.web_request_tracer import WebRequestTracer
from ...protocol.beacon import Beacon


class WebRequestTracerImpl(WebRequestTracer, CancelableOpenKitObject):

    def __init__(self,
                 logger: logging.Logger,
                 parent: OpenKitComposite,
                 url: str,
                 beacon: Beacon,
                 timestamp: Optional[datetime] = None):
        self.logger = logger
        self.parent = parent
        self.url = url
        self.beacon = beacon
        self.parent_action_id = parent.id
        self.start_seq_no = self.beacon.next_sequence_number
        self.tag = self.beacon.create_tag(self.parent_action_id, self.start_seq_no)
        if timestamp is None:
            timestamp = datetime.now()
        self.start_time = timestamp
        self.end_time: Optional[datetime] = None

        self.bytes_sent = 0
        self.bytes_received = 0
        self.response_code = -1
        self.end_seq_no = -1

        self.lock = RLock()

    def get_tag(self) -> str:
        self.logger.debug(f"get_tag() -> {self.tag}")
        return self.tag

    def set_bytes_sent(self, bytes_sent: int) -> "WebRequestTracer":
        with self.lock:
            if not self.is_stopped:
                self.bytes_sent = bytes_sent
        return self

    def set_bytes_received(self, bytes_received: int) -> "WebRequestTracer":
        with self.lock:
            if not self.is_stopped:
                self.bytes_received = bytes_received
        return self

    def start(self, timestamp: Optional[datetime] = None) -> "WebRequestTracer":
        self.logger.debug(f"start()")
        with self.lock:
            if not self.is_stopped:
                if timestamp is None:
                    timestamp = datetime.now()
                self.start_time = timestamp
        return self

    def stop(self,
             response_code: int,
             timestamp: Optional[datetime] = None,
             discard_data: bool = False) -> "WebRequestTracer":
        self.logger.debug(f"stop({response_code})")
        with self.lock:
            if self.is_stopped:
                return self
        self.response_code = response_code
        self.end_seq_no = self.beacon.next_sequence_number
        if timestamp is None:
            timestamp = datetime.now()
        self.end_time = timestamp

        if not discard_data:
            self.beacon.add_web_request(self.parent_action_id, self)

        self.parent._on_child_closed(self)
        self.parent = None

    def _cancel(self):
        self.stop(self.response_code, discard_data=True)

    def _close(self):
        self.stop(self.response_code)

    @property
    def is_stopped(self) -> bool:
        return self.end_time is not None

    def __repr__(self):
        return f"WebRequestTracer [sn='{self.beacon.session_number}', id='{self.parent_action_id}', url='{self.url}']"
