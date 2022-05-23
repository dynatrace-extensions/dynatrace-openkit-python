from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class WebRequestTracer(ABC):

    @abstractmethod
    def get_tag(self) -> str:
        pass

    @abstractmethod
    def set_bytes_sent(self, bytes_sent: int) -> "WebRequestTracer":
        pass

    @abstractmethod
    def set_bytes_received(self, bytes_received: int) -> "WebRequestTracer":
        pass

    @abstractmethod
    def start(self, timestamp: Optional[datetime] = None) -> "WebRequestTracer":
        pass

    @abstractmethod
    def stop(self, response_code: int, timestamp: Optional[datetime] = None) -> "WebRequestTracer":
        pass
