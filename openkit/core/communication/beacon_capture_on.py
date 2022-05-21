from typing import TYPE_CHECKING

from ...vendor.mureq.mureq import Response

from ...protocol.status_response import StatusResponse
from .beacon_abstract import AbstractBeaconSendingState

# from .beacon_flush import BeaconSendingFlushSessionsState
from .beacon_capture_off import BeaconSendingCaptureOffState

from ...core.configuration.server_configuration import ServerConfiguration

if TYPE_CHECKING:
    from ...core.beacon_sender import BeaconSendingContext


class BeaconSendingCaptureOnState(AbstractBeaconSendingState):
    def __init__(self):
        super().__init__()
        self.terminal = False

    def do_execute(self, context: "BeaconSendingContext"):
        context.sleep(1000)

        new_sessions_response = self.send_new_session_requests(context)
        if new_sessions_response is not None and new_sessions_response.status_code == 429:
            context.next_state = BeaconSendingCaptureOffState()
            return

        finished_sessions_response = self.send_finished_sessions(context)
        if finished_sessions_response is not None and finished_sessions_response.status_code == 429:
            context.next_state = BeaconSendingCaptureOffState()
            return

        open_sessions_response = self.send_open_sessions(context)
        if finished_sessions_response is not None and finished_sessions_response.status_code == 429:
            context.next_state = BeaconSendingCaptureOffState()
            return

        last_status_response = new_sessions_response or open_sessions_response or finished_sessions_response
        self.handle_status_response(context, last_status_response)

    def get_shutdown_state(self):
        return BeaconSendingFlushSessionsState()

    def send_new_session_requests(self, context: "BeaconSendingContext"):

        response = None
        not_configured_sessions = [session for session in context.sessions if not session.configured]
        context.logger.debug(f"Sending requests for {len(not_configured_sessions)} not configured sessions")

        for session in not_configured_sessions:
            response = context.http_client.send_new_session_request(context)

            if response.status_code < 400:
                status_response = StatusResponse(response)
                updated_attributes = context.update_from(status_response)
                new_server_config = ServerConfiguration.create_from(updated_attributes)
                session.update_server_configuration(new_server_config)
        return response

    def send_finished_sessions(self, context: "BeaconSendingContext"):

        response = None
        finished_sessions = [session for session in context.sessions if session.configured and session.finished]
        context.logger.debug(f"Sending requests for {len(finished_sessions)} finished sessions")

        for session in finished_sessions:

            if session.data_sending_allowed:
                response = session.send_beacon(context.http_client, context)

            context.sessions.remove(session)
            session.remove_captured_data()

        return response

    def send_open_sessions(self, context: "BeaconSendingContext"):
        response = None

        current_time = context.current_timestamp()

        send_open_sessions = current_time > context.last_open_session_beacon_send_time + context.send_interval
        context.logger.debug(f"Send open sessions? {'Yes' if send_open_sessions else 'No'}")
        if not send_open_sessions:
            return

        open_sessions = [session for session in context.sessions if session.configured and not session.finished]
        context.logger.debug(f"Sending requests for {len(open_sessions)} open sessions")

        for session in open_sessions:
            if session.data_sending_allowed:
                response = session.send_beacon(context.http_client, context)
            else:
                session.clear_captured_data()

        context.last_open_session_beacon_send_time = current_time
        return response

    def handle_status_response(self, context: "BeaconSendingContext", response: Response):

        if response is None:
            return
        status_response = StatusResponse(response)
        context.handle_response(status_response)

        if not context.capture_on:
            context.next_state = BeaconSendingCaptureOffState()
