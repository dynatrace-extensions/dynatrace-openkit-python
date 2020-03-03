from abc import ABC, abstractmethod
import time
from typing import TYPE_CHECKING

from requests import Response

if TYPE_CHECKING:
    from core.beacon_sender import BeaconSendingContext


MAX_INITIAL_STATUS_REQUEST_RETRIES = 5
INITIAL_RETRY_SLEEP_TIME_MILLISECONDS = 1000

REINIT_DELAY_MILLISECONDS = [
    1 * 60 * 1000,  # 1 minute
    5 * 60 * 1000,  # 5 minutes
    15 * 60 * 1000,  # 15 minutes
    1 * 60 * 60 * 1000,  # 1 hour
    2 * 60 * 60 * 1000,  # 2 hours
]


def is_successfull(response: Response):
    return response.status_code < 400


def send_status_request(context: "BeaconSendingContext", num_retries: int, init_retry_delay: int):

    retries = 0
    sleep_time = init_retry_delay
    while True:
        response = context.http_client.send_status_request(context)
        if response.status_code <= 400 or response.status_code == 429 or retries >= num_retries or context.shutdown_requested:
            break

        context.sleep(sleep_time)
        sleep_time *= 2
        retries += 1

    return response


class AbstractBeaconSendingState(ABC):
    def __init__(self):
        self.terminal_state = None

    def execute(self, context: "BeaconSendingContext"):
        try:
            self.do_execute(context)
        except Exception as e:
            print(f"Exception: {e}")
            context.shutdown_requested = True

        if context.shutdown_requested:
            context.next_state = self.get_shutdown_state()

    @abstractmethod
    def do_execute(self, context: "BeaconSendingContext"):
        pass

    @abstractmethod
    def get_shutdown_state(self):
        pass


class BeaconSendingCaptureOnState(AbstractBeaconSendingState):
    def __init__(self):
        super().__init__()
        self.terminal = False

    def do_execute(self, context: "BeaconSendingContext"):
        print("Running BeaconSendingCaptureOnState")
        pass

    def get_shutdown_state(self):
        pass


class BeaconSendingCaptureOffState(AbstractBeaconSendingState):
    def __init__(self):
        super().__init__()
        self.terminal = False

    def do_execute(self, context: "BeaconSendingContext"):
        pass

    def get_shutdown_state(self):
        pass


class BeaconSendingTerminalState(AbstractBeaconSendingState):
    def do_execute(self, context: "BeaconSendingContext"):
        context.shutdown_requested = True

    def get_shutdown_state(self):
        return self

    def __init__(self):
        super().__init__()
        self.terminal = True


class BeaconSendingInitState(AbstractBeaconSendingState):
    def __init__(self):
        super().__init__()
        self.terminal = False
        self.reinitialize_delay_index = 0

    def do_execute(self, context: "BeaconSendingContext"):
        r = self.execute_status_request(context)

        if context.shutdown_requested:
            context.init_succeeded = False
        elif r.status_code <= 400:
            context.handle_response(r)
            context.next_state = BeaconSendingCaptureOnState() if context.capture_on else BeaconSendingCaptureOffState()
            context.init_succeeded = True

    def execute_status_request(self, context: "BeaconSendingContext"):

        while True:
            current_timestamp = time.time() * 1000
            context.last_open_session_beacon_send_time = current_timestamp
            context.last_status_check_time = current_timestamp

            r = send_status_request(context, MAX_INITIAL_STATUS_REQUEST_RETRIES, INITIAL_RETRY_SLEEP_TIME_MILLISECONDS)
            if context.shutdown_requested or r.status_code <= 400:
                break

            sleep_time = REINIT_DELAY_MILLISECONDS[self.reinitialize_delay_index]
            if r.status_code == 429:
                if "retry-after" in r.headers:
                    sleep_time = int(r.headers.get("retry-after")) * 1000
                    # TODO: Implement disable capturing

            context.sleep(sleep_time)
            self.reinitialize_delay_index = min(self.reinitialize_delay_index + 1, len(REINIT_DELAY_MILLISECONDS) - 1)

        return r

    def get_shutdown_state(self):
        return BeaconSendingTerminalState()
