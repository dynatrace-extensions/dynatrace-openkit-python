import logging
import time
from threading import Event, RLock, Thread
from typing import List, Optional, TYPE_CHECKING

from .communication import AbstractBeaconSendingState, BeaconSendingInitState
from .communication.countdown_latch import CountDownLatch
from .configuration.server_configuration import ServerConfiguration
from ..protocol.http_client import HttpClient
from ..protocol.status_response import StatusResponse

if TYPE_CHECKING:
    from .objects.session import SessionImpl


class BeaconSendingContext:
    def __init__(self, logger: logging.Logger, http_client: HttpClient):
        self.logger = logger
        self.http_client = http_client
        self.server_configuration = ServerConfiguration()  # Default Values
        self.last_response_attributes = StatusResponse(None)

        self.sessions: List[SessionImpl] = []

        self.last_open_session_beacon_send_time = None
        self.last_status_check_time = None
        self.shutdown_requested = False
        self.init_succeeded = False

        self.countdown_latch = CountDownLatch()

        self.current_state: AbstractBeaconSendingState = BeaconSendingInitState()
        self.next_state = None

        self._lock = RLock()

    @property
    def terminal(self):
        return self.current_state.terminal

    @property
    def server_id(self):
        return self.http_client.server_id

    @property
    def capture_on(self) -> bool:
        with self._lock:
            return self.server_configuration.capture_enabled

    @property
    def last_server_configuration(self) -> ServerConfiguration:
        with self._lock:
            return self.server_configuration

    def disable_capture(self):
        with self._lock:
            self.server_configuration.capture_enabled = False

    def clear_all_session_data(self):
        self.logger.debug(f"Deleting all session data from cache")
        sessions = self.sessions.copy()
        for session in sessions:
            session.clear_captured_data()
            if session.state.is_finished:
                self.sessions.remove(session)

    def execute_current_state(self):
        self.next_state = None
        self.current_state.execute(self)

        if self.next_state is not None and self.next_state != self.current_state:
            self.logger.debug(f"State change from {self.current_state} to {self.next_state}")
            self.current_state = self.next_state

    def sleep(self, millis):
        time.sleep(millis / 1000)

    def handle_response(self, response: StatusResponse):

        if response is None or response.http_response.status_code >= 400:
            self.disable_capture()
            self.clear_all_session_data()
            return

        self.update_from(response)

        if not self.capture_on:
            self.clear_all_session_data()

    def get_configuration_timestamp(self):
        return 0

    def add_session(self, session):
        self.sessions.append(session)

    def update_from(self, status_response: StatusResponse):
        self.last_response_attributes = status_response
        self.server_configuration = ServerConfiguration.create_from(status_response)
        self.logger.debug(f"Received new server configuration: {self.server_configuration}")
        self.http_client.server_id = self.server_configuration.server_id
        return self.last_response_attributes

    @staticmethod
    def current_timestamp():
        return int(time.time() * 1000)

    @property
    def send_interval(self):
        with self._lock:
            return self.last_response_attributes.send_interval

    def init_completed(self, success: bool):
        self.init_succeeded = success
        self.countdown_latch.count_down()

    def disable_capture_and_clear(self):
        self.disable_capture()
        self.clear_all_session_data()

    def get_all_not_configured_sessions(self) -> List["SessionImpl"]:
        sessions = []
        for session in self.sessions:
            if not session.state.is_configured:
                sessions.append(session)
        return sessions

    def get_all_finished_and_configured_sessions(self) -> List["SessionImpl"]:
        sessions = []
        for session in self.sessions:
            if session.state.is_configured_and_finished:
                sessions.append(session)
        return sessions

    def get_all_open_and_configured_sessions(self):
        sessions = []
        for session in self.sessions:
            if session.state.is_configured_and_open:
                sessions.append(session)
        return sessions

    def remove_session(self, finished_session):
        return self.sessions.remove(finished_session)

    def wait_for_init_completion(self, timeout_ms):
        self.countdown_latch.wait(timeout_ms)


class BeaconSenderThread(Thread):
    def __init__(self, logger: logging.Logger, context: BeaconSendingContext):
        Thread.__init__(self, name="BeaconSenderThread", daemon=True)
        self.logger = logger
        self.shutdown_flag = Event()
        self.context = context

    def run(self):
        self.logger.debug("BeaconSenderThread - Running")
        while not self.context.terminal:
            self.context.execute_current_state()

        self.logger.debug("BeaconSenderThread - Exiting")


class BeaconSender:
    def __init__(self, logger: logging.Logger, http_client: HttpClient):
        self.logger = logger
        self.context = BeaconSendingContext(logger, http_client)
        self.thread: Optional[BeaconSenderThread] = None

    @property
    def server_id(self):
        return self.context.server_id

    def initialize(self):
        self.thread = BeaconSenderThread(self.logger, self.context)
        self.thread.start()

    def shutdown(self):
        self.context.shutdown_requested = True
        if self.thread is not None:
            self.thread.shutdown_flag.set()

    def add_session(self, session):
        self.logger.debug(f"Adding session {session}")
        self.context.add_session(session)

    @property
    def last_server_configuration(self):
        return self.context.last_server_configuration

    def wait_for_init_completion(self, timeout_ms):
        self.context.wait_for_init_completion(timeout_ms)

    def initialized(self):
        return self.context.init_succeeded
