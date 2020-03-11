from .beacon_abstract import AbstractBeaconSendingState


class BeaconSendingTerminalState(AbstractBeaconSendingState):
    def __init__(self):
        super().__init__()
        self.terminal = True

    def do_execute(self, context: "BeaconSendingContext"):
        context.shutdown_requested = True

    def get_shutdown_state(self):
        return self
