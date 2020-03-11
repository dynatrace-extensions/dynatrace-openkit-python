from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import traceback

if TYPE_CHECKING:
    from core.beacon_sender import BeaconSendingContext


class AbstractBeaconSendingState(ABC):
    def __init__(self):
        self.terminal = None

    def execute(self, context: "BeaconSendingContext"):
        try:
            self.do_execute(context)
        except Exception as e:
            print(f"Exception: {e}")
            traceback.print_exc()
            context.shutdown_requested = True

        if context.shutdown_requested:
            context.next_state = self.get_shutdown_state()

    @abstractmethod
    def do_execute(self, context: "BeaconSendingContext"):
        pass

    @abstractmethod
    def get_shutdown_state(self):
        pass
