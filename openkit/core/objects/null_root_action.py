from datetime import datetime
from typing import Optional, Union

from .base_action import Action
from .null_action import NullAction
from .root_action import RootAction
from .web_request_tracer import WebRequestTracer


class NullRootAction(RootAction):

    def enter_action(self, name: str):
        return NullAction(self)

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
        # TODO - Return NullWebRequestTracer
        pass

    def leave_action(self, timestamp: Optional[datetime] = None) -> Optional["Action"]:
        return None

    def cancel_action(self) -> Optional["Action"]:
        return None

    def get_duration_in_milliseconds(self) -> int:
        return 0

    def _close(self):
        pass
