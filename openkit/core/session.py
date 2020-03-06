from abc import ABC, abstractmethod
from datetime import datetime
import logging
from threading import RLock
from typing import TYPE_CHECKING, Optional

from protocol.beacon import Beacon
from core.configuration.beacon_configuration import BeaconConfiguration


if TYPE_CHECKING:
    from core.beacon_sender import BeaconSender
    from core.configuration.server_configuration import ServerConfiguration
    from api.openkit import Openkit


class OpenKitComposite(ABC):
    DEFAULT_ACTION_ID = 0

    def __init__(self):
        self._children = []

    def _store_child_in_list(self, child):
        self._children.append(child)

    @property
    def action_id(self):
        return self.DEFAULT_ACTION_ID


class Session(ABC):
    @abstractmethod
    def enter_action(self):
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
    def enter_action(self):
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
        self.is_finishing = False
        self.is_finished = False
        self.was_tried_for_ending = False
        self.logger = logger
        self.parent = parent
        self.beacon = beacon

        self.beacon.start_session()

    def enter_action(self):
        pass

    def identify_user(self, name: str):
        pass

    def report_crash(self, error_name, reson: str, stacktrace: str):
        pass

    def trace_web_request(self, string):
        pass

    @property
    def configured(self):
        # TODO: Implement Server Configuration Set
        # TODO: This comes from the StatusResponse I think
        pass

    def end(self, end_time: Optional[datetime] = None):
        self.logger.debug(f"Ending session {self}")

        if self.is_finishing or self.is_finished:
            return

        for child in self._children:
            try:
                child.end(end_time)
            except Exception as e:
                self.logger.error(f"Could not close {child}: {e}")

        self.beacon.end_session(end_time)
        self.is_finished = True
        self.parent.on_child_closed(self)
        self.parent = None


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

    def enter_action(self):
        pass

    def identify_user(self, name: str):
        pass

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

        for child in self._children:
            try:
                child.end(end_time)
            except Exception as e:
                self.logger.error(f"Could not close {child}: {e}")

        self.parent.on_child_closed(self)

    def on_child_closed(self, child):
        with self._lock:
            self._children.remove(child)
