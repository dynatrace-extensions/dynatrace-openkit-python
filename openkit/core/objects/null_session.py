from datetime import datetime
from typing import Optional

from .null_root_action import NullRootAction
from .null_web_request_tracer import NullWebRequestTracer
from ...api.root_action import RootAction
from ...api.session import Session
from ...api.web_request_tracer import WebRequestTracer


class NullSession(Session):

    def enter_action(self, name: str, timestamp: Optional[datetime] = None) -> RootAction:
        return NullRootAction()

    def identify_user(self, name: str, timestamp: Optional[datetime] = None) -> None:
        pass

    def report_crash(self, error_name, reason: str, stacktrace: str, timestamp: Optional[datetime] = None) -> None:
        pass

    def trace_web_request(self, url: str, timestamp: Optional[datetime] = None) -> WebRequestTracer:
        return NullWebRequestTracer()

    def end(self, send_end_event: bool = True, timestamp: Optional[datetime] = None):
        pass

    def close(self):
        pass
