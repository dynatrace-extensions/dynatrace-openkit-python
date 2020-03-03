import logging
import time
from threading import Thread, Event
from typing import Optional

from core.communication.beacon_states import BeaconSendingInitState, AbstractBeaconSendingState

from requests import Response


from protocol.http_client import HttpClient


class BeaconSendingContext:
    def __init__(self, logger: logging.Logger, http_client: HttpClient):
        self.logger = logger
        self.http_client = http_client
        self.terminal_state = False
        self.last_open_session_beacon_send_time = None
        self.last_status_check_time = None
        self.shutdown_requested = False
        self.init_succeded = False
        self.last_response_attributes = None  # TODO: This is a class protocol.ResponseAttributes

        self.current_state: AbstractBeaconSendingState = BeaconSendingInitState()
        self.next_state = None
        self.capture_on = True

    def execute_current_state(self):
        self.next_state = None
        self.current_state.execute(self)

        if self.next_state is not None and self.next_state != self.current_state:
            self.logger.debug(f"State change from {self.current_state} to {self.next_state}")

        self.current_state = self.next_state

    def sleep(self, millis):
        time.sleep(millis / 1000)

    def handle_response(self, response: Response):

        if response is None or response.status_code >= 400:
            return

        # TODO: Implement server response parsing

    def get_configuration_timestamp(self):
        return 0


class BeaconSenderThread(Thread):
    def __init__(self, logger: logging.Logger, context: BeaconSendingContext):
        Thread.__init__(self)
        self.logger = logger
        self.shutdown_flag = Event()
        self.context = context

    def run(self):
        self.logger.debug("BeaconSenderThread - Running")
        while not self.context.terminal_state:
            self.context.execute_current_state()
            if self.shutdown_flag.is_set():
                break

        self.logger.debug("BeaconSenderThread - Exiting")


class BeaconSender:
    def __init__(self, logger: logging.Logger, http_client: HttpClient):
        self.logger = logger
        self.context = BeaconSendingContext(logger, http_client)
        self.thread: Optional[BeaconSenderThread] = None

    def initalize(self):
        self.thread = BeaconSenderThread(self.logger, self.context)
        self.thread.start()

    def shutdown(self):
        if self.thread is not None:
            self.thread.shutdown_flag.set()
