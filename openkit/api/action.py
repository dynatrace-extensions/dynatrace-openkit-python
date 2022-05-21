from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Union

from .openkit_object import OpenKitObject
from .web_request_tracer import WebRequestTracer


class Action(ABC, OpenKitObject):

    @abstractmethod
    def report_event(self, event_name: str, timestamp: Optional[datetime] = None) -> "Action":
        pass

    @abstractmethod
    def report_value(self, value_name: str, value: Union[str, int, float], timestamp: Optional[datetime] = None) -> "Action":
        pass

    @abstractmethod
    def report_error(self, error_name: str, error_code: int, reason: str, timestamp: Optional[datetime] = None) -> "Action":
        pass

    @abstractmethod
    def trace_web_request(self, url: str, timestamp: Optional[datetime] = None) -> WebRequestTracer:
        pass

    @abstractmethod
    def leave_action(self, timestamp: Optional[datetime] = None) -> Optional["Action"]:
        pass

    @abstractmethod
    def cancel_action(self) -> Optional["Action"]:
        pass

    @abstractmethod
    def get_duration_in_milliseconds(self) -> int:
        pass
