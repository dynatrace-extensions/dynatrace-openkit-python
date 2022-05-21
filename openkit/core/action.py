from abc import ABC, abstractmethod
import logging
from datetime import datetime
from threading import RLock
from typing import Union, TYPE_CHECKING, Optional

from .composite import OpenKitComposite

if TYPE_CHECKING:
    from ..protocol.beacon import Beacon


class Action(ABC):
    def __init__(self, logger: logging.Logger, parent: OpenKitComposite, name: str, beacon: "Beacon", start_time: datetime = None):
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
    def leave_action(self, timestamp: Optional[datetime] = None) -> "Action":
        pass


class RootAction(Action):
    def __init__(self, logger: logging.Logger, parent: OpenKitComposite, name: str, beacon: "Beacon", start_time: datetime = None):
        super().__init__(logger, parent, name, beacon, start_time)

    @abstractmethod
    def enter_action(self, name: str):
        pass


class ActionImpl(Action, OpenKitComposite):
    def __init__(self, logger: logging.Logger, parent: OpenKitComposite, name: str, beacon: "Beacon", start_time: datetime = None):
        self.lock = RLock()
        super(ActionImpl, self).__init__(logger, parent, name, beacon, start_time)

    def report_event(self, event_name) -> "Action":
        raise NotImplementedError("report_event is not implemented")

    def report_value(self, value_name: str, value: Union[str, int, float]) -> "Action":
        raise NotImplementedError("report_value is not implemented")

    def report_error(self, error_name: str, error_code: int, reason: str) -> "Action":
        raise NotImplementedError("report_error is not implemented")

    def trace_web_request(self, url: str):
        raise NotImplementedError("trace_web_request is not implemented")
        pass

    def leave_action(self, timestamp: Optional[datetime] = None) -> "Action":
        # com.dynatrace.openkit.core.objects.BaseActionImpl#doLeaveAction

        # get a copy of self._children
        with self.lock:
            children = self._children.copy()
            for child in children:
                child.close(timestamp)

    def close(self, timestamp: Optional[datetime] = None):
        self.leave_action(timestamp)

    def _on_child_closed(self, child: OpenKitComposite):
        raise NotImplementedError("_on_child_closed is not implemented")


class NullRootAction(RootAction):
    def __init__(self):
        super().__init__(None, None, None, None)

    def report_event(self, event_name) -> "Action":
        pass

    def report_value(self, value_name: str, value: Union[str, int, float]) -> "Action":
        pass

    def report_error(self, error_name: str, error_code: int, reason: str) -> "Action":
        pass

    def trace_web_request(self, url: str):
        pass

    def leave_action(self, timestamp: Optional[datetime] = None) -> "Action":
        pass

    def enter_action(self, name: str):
        pass


class RootActionImpl(ActionImpl, RootAction):
    def __init__(self, logger: logging.Logger, parent: OpenKitComposite, name: str, beacon: "Beacon", start_time: datetime = None):
        super(RootActionImpl, self).__init__(logger, parent, name, beacon, start_time)

    def enter_action(self, name):
        raise NotImplemented("enter_action is not implemented")
