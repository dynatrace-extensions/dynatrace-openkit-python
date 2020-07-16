from abc import ABC, abstractmethod
import logging
from datetime import datetime
from threading import RLock
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from api.openkit import OpenKitComposite
    from protocol.beacon import Beacon


class Action(ABC):
    @abstractmethod
    def report_event(self, event_name) -> "Action":
        pass

    @abstractmethod
    def report_value(self, value_name: str, value: Union[str, int, float]) -> "Action":
        pass

    @abstractmethod
    def report_error(self, error_name: str, error_code: int, reason: str) -> "Action":
        pass

    @abstractmethod
    def trace_web_request(self, url: str):
        pass

    @abstractmethod
    def leave_action(self) -> "Action":
        pass


class BaseActionImpl(Action):
    def __init__(self, logger: logging.Logger, parent: "OpenKitComposite", name: str, beacon: "Beacon"):
        self.logger = logger
        self.parent = parent
        self.parent_action_id = parent.action_id

        self.id = beacon.next_id
        self.name = name

        self.start_time: datetime = datetime.now()
        self.start_seq_no = beacon.next_sequence_number

        self.is_action_left = False
        self.beacon = beacon

        self._lock = RLock()
        self.end_time: datetime = datetime.now()
        self.end_sequence_number = -1

    def report_event(self, event_name) -> "Action":
        if not event_name:
            self.logger("report_event: event_name must not be null or empty")
            return

        self.logger.debug(f"report_event({event_name})")

        self.beacon.report_event(self.id, event_name)

    def report_value(self, value_name: str, value: Union[str, int, float]) -> "Action":
        if not value_name:
            self.logger("report_value: value_name must not be null or empty")
            return

        self.logger.debug(f"report_value({value_name},{value})")

        self.beacon.report_value(self.id, value_name, value)

    def report_error(self, error_name: str, error_code: int, reason: str) -> "Action":
        if not error_name:
            self.logger("report_error: error_name must not be null or empty")
            return
        
        self.logger.debug(f"report_error({error_name},{error_code},{reason})")

        self.beacon.report_error(self.id, error_name, error_code, reason)

    def trace_web_request(self, url: str):
        from core.web_request_tracer import WebRequestTracer
        tracer = WebRequestTracer(
            parent=self, url=url, beacon=self.beacon)
        return tracer

    def leave_action(self) -> "Action":
        self.end_time: datetime = datetime.now()
        self.end_sequence_no = self.beacon.next_sequence_number
        self.beacon.add_action(self)

        if hasattr(self.parent, "id"):
            return self.parent.id
        else:
            return None
