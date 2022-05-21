from abc import ABC, abstractmethod
from datetime import datetime
import logging
from threading import RLock
from typing import TYPE_CHECKING, Optional, List

from .action import RootAction
from .composite import OpenKitComposite
from ..protocol.beacon import Beacon
from ..core.configuration.beacon_configuration import BeaconConfiguration
from ..core.action import NullRootAction, RootActionImpl, ActionImpl, Action


if TYPE_CHECKING:
    from ..core.beacon_sender import BeaconSender
    from ..core.configuration import ServerConfiguration
    from .. import Openkit


class Session(ABC):
    @abstractmethod
    def enter_action(self, name: str, timestamp: Optional[datetime] = None) -> RootAction:
        pass

    @abstractmethod
    def identify_user(self, name: str):
        pass

    @abstractmethod
    def report_crash(self, error_name, reson: str, stacktrace: str):
        pass

    @abstractmethod
    def trace_web_request(self, string):
        pass

    @abstractmethod
    def end(self, end_time: Optional[datetime] = None):
        pass


class NullSession(Session):
    def enter_action(self, name: str, timestamp: Optional[datetime] = None) -> RootAction:
        pass

    def identify_user(self, name: str):
        pass

    def report_crash(self, error_name, reson: str, stacktrace: str):
        pass

    def trace_web_request(self, string):
        pass

    def end(self, end_time: Optional[datetime] = None):
        pass


class SessionImpl(OpenKitComposite, Session):
    def __init__(self, logger: logging.Logger, parent: OpenKitComposite, beacon: Beacon):
        super().__init__()
        self.finishing = False
        self.finished = False
        self.was_tried_for_ending = False
        self.logger = logger
        self.parent = parent
        self.beacon = beacon

        self.children = []

        self._lock = RLock()

        self.beacon.start_session()

    def enter_action(self, name: str, timestamp: Optional[datetime]) -> RootAction:
        self.logger.debug(f"SessionImpl.enter_action({name})")
        with self._lock:
            if not (self.finished or self.finishing):
                root_action = RootActionImpl(self.logger, self, name, self.beacon, timestamp)
                self._store_child_in_list(root_action)
                return root_action

        return NullRootAction()

    def identify_user(self, name: str):
        pass

    def report_crash(self, error_name, reson: str, stacktrace: str):
        pass

    def trace_web_request(self, string):
        pass

    @property
    def configured(self):
        return self.beacon.configuration.server_configured

    @property
    def data_sending_allowed(self):
        return self.configured and self.beacon.configuration.server_configuration.capture_enabled

    def send_beacon(self, http_client, additional_params):
        return self.beacon.send(http_client, additional_params)

    def end(self, end_time: Optional[datetime] = None):
        self.logger.debug(f"Ending session {self}")

        if self.finishing or self.finished:
            return

        for child in self._children:
            try:
                child.close(end_time)
            except Exception as e:
                self.logger.exception(f"Could not close {child}: {e}")

        self.beacon.end_session(end_time)
        self.finished = True
        self.parent._on_child_closed(self)
        self.parent = None

    def update_server_configuration(self, server_configuration):
        self.beacon.update_server_configuration(server_configuration)

    def remove_captured_data(self):
        self.beacon.beacon_cache.delete_cache_entry(self.beacon.beacon_key)

    def clear_captured_data(self):
        self.beacon.beacon_cache.delete_cache_entry(self.beacon.beacon_key)

    def __eq__(self, other):
        return self.beacon.beacon_key == other.beacon.beacon_key


class SessionProxy(OpenKitComposite, Session):
    def __init__(self, parent: "Openkit", beacon_sender: "BeaconSender", ip_address: str, device_id=None, start_time=None):

        super().__init__()
        self.logger = parent._logger
        self.beacon_sender = beacon_sender
        self.ip_address = ip_address

        self.parent = parent
        self.openkit_configuration = parent._openkit_configuration
        self.beacon_cache = parent._beacon_cache

        self.server_id = beacon_sender.server_id

        self.is_finishing = False
        self.is_finished = False
        self.was_tried_for_ending = False
        self.session_sequence_number: int = 0

        self.last_interaction_time = None
        self.top_level_action_count = 0

        self._lock = RLock()

        server_configuration: ServerConfiguration = beacon_sender.last_server_configuration
        self.current_session = self.create_initial_session(server_configuration, device_id=device_id, start_time=start_time)

    def create_session(
        self,
        server_configuration: "ServerConfiguration",
        updated_server_configuration: Optional["ServerConfiguration"],
        device_id=None,
        start_time=None,
    ) -> SessionImpl:
        beacon_configuration: BeaconConfiguration = BeaconConfiguration(
            self.openkit_configuration, self.server_id, self.parent._data_collection_level, self.parent._crash_reporting_level
        )
        beacon: Beacon = Beacon(self, beacon_configuration, device_id=None, session_start_time=start_time)
        session: SessionImpl = SessionImpl(self.logger, self, beacon)

        # TODO: beacon.setServerConfigurationUpdateCallback

        self._store_child_in_list(session)
        self.last_interaction_time = session.beacon.session_start_time
        self.top_level_action_count = 0

        self.beacon_sender.add_session(session)
        self.session_sequence_number += 1
        return session

    def create_initial_session(self, server_configuration: "ServerConfiguration", device_id=None, start_time=None) -> SessionImpl:
        session = self.create_session(server_configuration, None, device_id=device_id, start_time=start_time)

        return session

    def enter_action(self, name: str, timestamp: Optional[datetime] = None) -> RootAction:
        self.logger.debug(f"SessionProxy.enter_action({name})")
        with self._lock:
            if not self.is_finished:
                # TODO: getOrSplitCurrentSessionByEvents
                session = self.current_session
                self.record_top_action_event()
                return session.enter_action(name, timestamp)

        return NullRootAction()

    def record_top_action_event(self):
        self.top_level_action_count += 1
        self.record_top_level_event_interaction()

    def record_top_level_event_interaction(self):
        self.last_interaction_time = int(datetime.now().timestamp() * 1000)

    def identify_user(self, name: str):
        self.current_session.beacon.identify_user(name)

    def report_crash(self, error_name, reson: str, stacktrace: str):
        pass

    def trace_web_request(self, string):
        pass

    def end(self, end_time: Optional[datetime] = None):
        if end_time is None:
            end_time = datetime.now()
        self.logger.debug(f"Ending session {self}")

        with self._lock:
            if self.is_finished:
                return
            self.is_finished = True

        self._children: List[SessionImpl]
        for child in self._children:
            try:
                child.end(end_time)
            except Exception as e:
                self.logger.exception(f"Could not close {child}: {e}")

        self.parent._on_child_closed(self)

    def on_child_closed(self, child):
        with self._lock:
            self._children.remove(child)
