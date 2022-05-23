from datetime import datetime
from typing import Optional

from ...api.web_request_tracer import WebRequestTracer


class NullWebRequestTracer(WebRequestTracer):
    def get_tag(self) -> str:
        return ""

    def set_bytes_sent(self, bytes_sent: int) -> "WebRequestTracer":
        return self

    def set_bytes_received(self, bytes_received: int) -> "WebRequestTracer":
        return self

    def start(self, timestamp: Optional[datetime] = None) -> "WebRequestTracer":
        return self

    def stop(self, response_code: int, timestamp: Optional[datetime] = None) -> "WebRequestTracer":
        return self
