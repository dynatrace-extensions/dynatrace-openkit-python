from typing import TYPE_CHECKING

import openkit.core.communication as comm

if TYPE_CHECKING:
    from ..beacon_sender import BeaconSendingContext


class BeaconSendingFlushSessionsState(comm.AbstractBeaconSendingState):
    def __init__(self):
        super().__init__()
        self.terminal = False

    def do_execute(self, context: "BeaconSendingContext"):
        # Get all sessions that are not configured
        not_configured_sessions = context.get_all_not_configured_sessions()
        for new_session in not_configured_sessions:
            # Enable capturing to send the data
            new_session.enable_capture()

        # Finish all sessions
        open_sessions = context.get_all_open_and_configured_sessions()
        for open_session in open_sessions:
            open_session.end(send_end_event=False)

        too_many_requests = False

        finished_sessions = context.get_all_finished_and_configured_sessions()
        for finished_session in finished_sessions:
            if not too_many_requests and finished_session.data_sending_allowed:
                response = finished_session.send_beacon(context.http_client, context)
                if response.status_code == 429:
                    too_many_requests = True

            finished_session.clear_captured_data()
            context.remove_session(finished_session)

        context.next_state = comm.BeaconSendingTerminalState()

    def get_shutdown_state(self):
        return comm.BeaconSendingTerminalState()

    def __repr__(self):
        return "Flush sessions"
