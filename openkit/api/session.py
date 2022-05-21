from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from .openkit_object import OpenKitObject
from .root_action import RootAction
from .web_request_tracer import WebRequestTracer


class Session(ABC, OpenKitObject):
    @abstractmethod
    def enter_action(self, name: str, timestamp: Optional[datetime] = None) -> RootAction:
        pass

    @abstractmethod
    def identify_user(self, name: str, timestamp: Optional[datetime] = None) -> None:
        pass

    @abstractmethod
    def report_crash(self, error_name, reason: str, stacktrace: str, timestamp: Optional[datetime] = None) -> None:
        pass

    @abstractmethod
    def trace_web_request(self, url: str, timestamp: Optional[datetime] = None) -> WebRequestTracer:
        pass

    @abstractmethod
    def end(self, send_end_event: bool = True, timestamp: Optional[datetime] = None):
        pass

    # TODO - send_biz_event
