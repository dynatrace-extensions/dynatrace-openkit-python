from datetime import datetime
from typing import Optional, Union

from .base_action import Action
from .web_request_tracer import WebRequestTracer


class NullAction(Action):

    def __init__(self, parent: Action):
        self.parent = parent

    def report_event(self, event_name: str, timestamp: Optional[datetime] = None) -> "Action":
        return self

    def report_value(self,
                     value_name: str,
                     value: Union[str, int, float],
                     timestamp: Optional[datetime] = None) -> "Action":
        return self

    def report_error(self,
                     error_name: str,
                     error_code: int,
                     reason: str,
                     timestamp: Optional[datetime] = None) -> "Action":
        return self

    def trace_web_request(self, url: str, timestamp: Optional[datetime] = None) -> WebRequestTracer:
        pass

    def leave_action(self, timestamp: Optional[datetime] = None) -> "Action":
        return self.parent

    def cancel_action(self) -> "Action":
        return self.parent

    def get_duration_in_milliseconds(self) -> int:
        return 0

    def _close(self):
        pass
