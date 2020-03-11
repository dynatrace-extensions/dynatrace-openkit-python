from typing import TYPE_CHECKING

from requests import Response

from core.communication import AbstractBeaconSendingState


if TYPE_CHECKING:
    from core.beacon_sender import BeaconSendingContext


class BeaconSendingFlushSessionsState(AbstractBeaconSendingState):
    def __init__(self):
        super().__init__()
        self.terminal = False

    def do_execute(self, context: "BeaconSendingContext"):
        pass

    def get_shutdown_state(self):
        pass
