from typing import TYPE_CHECKING

from .beacon_abstract import AbstractBeaconSendingState

if TYPE_CHECKING:
    from ...core.beacon_sender import BeaconSendingContext


class BeaconSendingTerminalState(AbstractBeaconSendingState):
    def __init__(self):
        super().__init__()
        self.terminal = True

    def do_execute(self, context: "BeaconSendingContext"):
        context.shutdown_requested = True

    def get_shutdown_state(self):
        return self
