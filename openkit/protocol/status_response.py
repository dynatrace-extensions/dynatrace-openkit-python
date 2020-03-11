from typing import TYPE_CHECKING, Optional


RESPONSE_KEY_AGENT_CONFIG = "mobileAgentConfig"
RESPONSE_KEY_MAX_BEACON_SIZE_IN_KB = "maxBeaconSizeKb"
RESPONSE_KEY_MAX_SESSION_DURATION_IN_MIN = "maxSessionDurationMins"
RESPONSE_KEY_MAX_EVENTS_PER_SESSION = "maxEventsPerSession"
RESPONSE_KEY_SESSION_TIMEOUT_IN_SEC = "sessionTimeoutSec"
RESPONSE_KEY_SEND_INTERVAL_IN_SEC = "sendIntervalSec"
RESPONSE_KEY_VISIT_STORE_VERSION = "visitStoreVersion"

RESPONSE_KEY_APP_CONFIG = "appConfig"
RESPONSE_KEY_CAPTURE = "capture"
RESPONSE_KEY_REPORT_CRASHES = "reportCrashes"
RESPONSE_KEY_REPORT_ERRORS = "reportErrors"

RESPONSE_KEY_DYNAMIC_CONFIG = "dynamicConfig"
RESPONSE_KEY_MULTIPLICITY = "multiplicity"
RESPONSE_KEY_SERVER_ID = "serverId"

RESPONSE_KEY_TIMESTAMP_IN_MILLIS = "timestamp"

if TYPE_CHECKING:
    from requests import Response


class StatusResponse:
    def __init__(self, response: Optional["Response"]):
        self.http_response = response
        self.max_beacon_size = 150 * 1024
        self.max_session_duration = 6 * 60 * 60 * 1000  # 6 hours
        self.max_events_per_session = 200
        self.session_timeout = 10 * 60 * 1000  # 10 minutes
        self.send_interval = 2 * 60 * 1000  # 2 minutes
        self.visit_store_version = 1
        self.capture = True
        self.capture_crashes = True
        self.capture_errors = True
        self.multiplicity = 1
        self.server_id = 1
        self.timestamp = 0

        if response is not None and response.status_code < 400:
            json_response: dict = response.json()

            # AGENT Configuration
            agent_config: dict = json_response.get(RESPONSE_KEY_AGENT_CONFIG)

            if agent_config is not None:
                max_beacon_size = agent_config.get(RESPONSE_KEY_MAX_BEACON_SIZE_IN_KB)
                if max_beacon_size is not None:
                    self.max_beacon_size = int(max_beacon_size) * 1024  # We need bytes, server responds in KB

                max_session_duration = agent_config.get(RESPONSE_KEY_MAX_SESSION_DURATION_IN_MIN)
                if max_session_duration is not None:
                    self.max_session_duration = int(max_session_duration) * 60 * 1000  # We need ms, server responds in m

                self.max_events_per_session = agent_config.get(RESPONSE_KEY_MAX_EVENTS_PER_SESSION, self.max_events_per_session)

                session_timeout = agent_config.get(RESPONSE_KEY_SESSION_TIMEOUT_IN_SEC)
                if session_timeout is not None:
                    self.session_timeout = int(session_timeout) * 1000  # We need ms, server responds in s

                send_interval = agent_config.get(RESPONSE_KEY_SEND_INTERVAL_IN_SEC)
                if send_interval is not None:
                    self.send_interval = int(send_interval) * 1000  # We need ms, server responds in s

                self.visit_store_version = agent_config.get(RESPONSE_KEY_VISIT_STORE_VERSION, self.visit_store_version)

            # APPLICATION Configuration
            app_config = json_response.get(RESPONSE_KEY_APP_CONFIG)
            if app_config is not None:
                self.capture = bool(app_config.get(RESPONSE_KEY_CAPTURE, self.capture))
                self.capture_crashes = bool(app_config.get(RESPONSE_KEY_REPORT_CRASHES, self.capture_crashes))
                self.capture_errors = bool(app_config.get(RESPONSE_KEY_REPORT_ERRORS, self.capture_errors))

            # DYNAMIC Configuration
            dynamic_config = json_response.get(RESPONSE_KEY_DYNAMIC_CONFIG)
            if dynamic_config is not None:
                self.multiplicity = json_response.get(RESPONSE_KEY_MULTIPLICITY, self.multiplicity)
                self.server_id = json_response.get(RESPONSE_KEY_SERVER_ID, self.server_id)

            self.timestamp = int(json_response.get(RESPONSE_KEY_TIMESTAMP_IN_MILLIS, self.timestamp))
