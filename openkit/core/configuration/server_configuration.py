from ...protocol.status_response import StatusResponse


class ServerConfiguration:
    def __init__(
        self,
        capture_enabled: bool = True,
        crash_reporting_enabled: bool = True,
        error_reporting_enabled: bool = True,
        server_id: int = 1,
        beacon_size_in_bytes: int = 150 * 1024,
        multiplicity: int = 1,
        max_session_duration_in_milliseconds=6 * 60 * 60 * 1000,  # 6 hours
        session_split_by_session_duration_enabled=True,
        max_events_per_session=200,
        session_split_by_events_enabled=True,
        session_timeout_in_milliseconds=10 * 60 * 1000,  # 10 minutes
        session_split_by_idle_timeout_enabled=True,
        visit_store_version=1,
    ):
        self.capture_enabled = capture_enabled
        self.crash_reporting_enabled = crash_reporting_enabled
        self.error_reporting_enabled = error_reporting_enabled
        self.server_id = server_id
        self.beacon_size_in_bytes = beacon_size_in_bytes
        self.multiplicity = multiplicity
        self.max_session_duration_in_milliseconds = max_session_duration_in_milliseconds
        self.session_split_by_session_duration_enabled = session_split_by_session_duration_enabled
        self.max_events_per_session = max_events_per_session
        self.session_split_by_events_enabled = session_split_by_events_enabled
        self.session_timeout_in_milliseconds = session_timeout_in_milliseconds
        self.session_split_by_idle_timeout_enabled = session_split_by_idle_timeout_enabled
        self.visit_store_version = visit_store_version

    @staticmethod
    def create_from(status_response: StatusResponse) -> "ServerConfiguration":
        return ServerConfiguration(
            status_response.capture,
            status_response.capture_crashes,
            status_response.capture_errors,
            status_response.server_id,
            status_response.max_beacon_size,
            status_response.multiplicity,
            status_response.max_session_duration,
            status_response.max_session_duration is not None,
            status_response.max_events_per_session,
            status_response.max_events_per_session is not None,
            status_response.session_timeout,
            status_response.session_timeout is not None,
            status_response.visit_store_version,
        )

    def __str__(self):
        return str(self.__dict__)
