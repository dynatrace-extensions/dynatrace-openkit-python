import logging
from urllib.parse import quote
from enum import Enum
from typing import Optional

from ..vendor.mureq import mureq as requests


REQUEST_TYPE_MOBILE = "type=m"

QUERY_KEY_SERVER_ID = "srvid"
QUERY_KEY_APPLICATION = "app"
QUERY_KEY_VERSION = "va"
QUERY_KEY_PLATFORM_TYPE = "pt"
QUERY_KEY_AGENT_TECHNOLOGY_TYPE = "tt"
QUERY_KEY_RESPONSE_TYPE = "resp"
QUERY_KEY_CONFIG_TIMESTAMP = "cts"
QUERY_KEY_NEW_SESSION = "ns"

OPENKIT_VERSION = "7.0.0000"
PROTOCOL_VERSION = 3
PLATFORM_TYPE_OPENKIT = 1
AGENT_TECHNOLOGY_TYPE = "okpython"
ERROR_TECHNOLOGY_TYPE = "c"
RESPONSE_TYPE = "json"
DEFAULT_SERVER_ID = 1


class RequestType(Enum):
    STATUS = "Status"
    BEACON = "Beacon"
    NEW_SESSION = "NewSession"


class HttpClient:
    def __init__(self, logger: logging.Logger, base_url: str, server_id: int, application_id: str):
        self.logger = logger
        self.server_id = server_id
        self.monitor_url = self.build_monitor_url(base_url, application_id, server_id)
        self.new_session_url = self.build_session_url()

    def send_request(self, request_type: RequestType, url: str, client_ip_address: Optional[str], data: Optional[str], method: str):
        self.logger.debug(f"Sending request type {request_type} ({url})")

        headers = {}
        if client_ip_address is not None:
            headers = {"X-Client-IP": client_ip_address}
        r = requests.request(method, url, body=data, headers=headers)
        self.logger.debug(f"Response for {request_type} ({url}): {r.status_code}: {r.content}")
        return r

    def build_monitor_url(self, base_url, application_id, server_id) -> str:
        url_parts = [
            f"{base_url}?{REQUEST_TYPE_MOBILE}",
            self.append_parameter(QUERY_KEY_SERVER_ID, str(server_id)),
            self.append_parameter(QUERY_KEY_APPLICATION, application_id),
            self.append_parameter(QUERY_KEY_VERSION, OPENKIT_VERSION),
            self.append_parameter(QUERY_KEY_PLATFORM_TYPE, str(PLATFORM_TYPE_OPENKIT)),
            self.append_parameter(QUERY_KEY_AGENT_TECHNOLOGY_TYPE, AGENT_TECHNOLOGY_TYPE),
            self.append_parameter(QUERY_KEY_RESPONSE_TYPE, RESPONSE_TYPE),
        ]

        return "".join(url_parts)

    def build_session_url(self) -> str:

        url_parts = [self.monitor_url, self.append_parameter(QUERY_KEY_NEW_SESSION, "1")]
        return "".join(url_parts)

    def send_status_request(self, additional_params):
        url = self.append_additional_query_parameters(self.monitor_url, additional_params)
        return self.send_request(RequestType.STATUS, url, None, None, "GET")

    def send_new_session_request(self, additional_params):
        url = self.append_additional_query_parameters(self.new_session_url, additional_params)
        return self.send_request(RequestType.NEW_SESSION, url, None, None, "GET")

    def send_beacon_request(self, client_ip: str, data: str, additional_params):
        url = self.append_additional_query_parameters(self.monitor_url, additional_params)
        return self.send_request(RequestType.BEACON, url, client_ip, data, "POST")

    def append_additional_query_parameters(self, base_url: str, params):
        if params is None:
            return ""

        url_parts = [base_url, self.append_parameter(QUERY_KEY_CONFIG_TIMESTAMP, str(params.get_configuration_timestamp()))]

        return "".join(url_parts)

    @staticmethod
    def append_parameter(key, value) -> str:
        return f"&{key}={quote(value)}"
