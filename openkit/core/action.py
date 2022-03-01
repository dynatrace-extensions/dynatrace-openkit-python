from abc import ABC, abstractmethod
import logging
from datetime import datetime
from threading import RLock
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from api.openkit import OpenKitComposite
    from protocol.beacon import Beacon


class Action(ABC):
    def __init__(self, logger, parent: OpenKitComposite, name, beacon: Beacon, start_time: datetime = None):
        self.logger = logger
        self.parent = parent
        self.parent_action_id = parent._action_id

        self.id = beacon.create_id()
        self.name = name

        if start_time is None:
            self.start_time = beacon.current_timestamp
        else:
            self.start_time = int(start_time.timestamp() * 1000)

        self.sequence_number = beacon.next_sequence_number

        self.action_left = False
        self.beacon = beacon

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


class NullRootAction(Action):
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


class RootAction(Action):
    def __init__(self, logger, parent_session, name, beacon, parent: OpenKitComposite):
        super().__init__(logger, parent, name, beacon)

    def enter_action(self, name):
        # TODO: Leaf Action
        pass

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


class BaseActionImpl(Action):
    def __init__(self, logger: logging.Logger, parent: "OpenKitComposite", name: str, beacon: "Beacon"):
        super().__init__(logger, parent, name, beacon)
        self._lock = RLock()

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
