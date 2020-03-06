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

        self.id = beacon.next_id()
        self.name = name

        self.start_time: datetime = datetime.now()
        self.start_seq_no = beacon.next_sequence_number()

        self.is_action_left = False
        self.beacon = beacon

        self._lock = RLock()
        self.end_time: datetime = datetime.now()
        self.end_sequence_number = -1

    def report_event(self, event_name) -> "Action":
        pass

    def report_value(self, value_name: str, value: Union[str, int, float]) -> "Action":
        pass

    def report_error(self, error_name: str, error_code: int, reason: str) -> "Action":
        pass

    def trace_web_request(self, url: str):
        pass

    def leave_action(self) -> "Action":
        pass
