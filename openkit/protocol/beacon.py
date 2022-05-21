from datetime import datetime
from threading import get_ident, RLock
from typing import TYPE_CHECKING, Optional, Union
from urllib.parse import quote
from urllib.parse import quote_plus

from ..core.caching.key import BeaconKey
from ..core.action import Action, ActionImpl
from ..protocol.event_type import EventType
from ..protocol.http_client import (
    OPENKIT_VERSION,
    PROTOCOL_VERSION,
    PLATFORM_TYPE_OPENKIT,
    AGENT_TECHNOLOGY_TYPE,
    ERROR_TECHNOLOGY_TYPE,
)

if TYPE_CHECKING:
    from ..core.configuration.beacon_configuration import BeaconConfiguration
    from ..core.session import SessionProxy
    from ..core.caching.cache import BeaconCache
    from ..protocol.http_client import HttpClient


class Beacon:

    # basic data constants
    BEACON_KEY_PROTOCOL_VERSION = "vv"
    BEACON_KEY_OPENKIT_VERSION = "va"
    BEACON_KEY_APPLICATION_ID = "ap"
    BEACON_KEY_APPLICATION_NAME = "an"
    BEACON_KEY_APPLICATION_VERSION = "vn"
    BEACON_KEY_PLATFORM_TYPE = "pt"
    BEACON_KEY_AGENT_TECHNOLOGY_TYPE = "tt"
    BEACON_KEY_VISITOR_ID = "vi"
    BEACON_KEY_SESSION_NUMBER = "sn"
    BEACON_KEY_SESSION_SEQUENCE = "ss"
    BEACON_KEY_CLIENT_IP_ADDRESS = "ip"
    BEACON_KEY_MULTIPLICITY = "mp"
    BEACON_KEY_DATA_COLLECTION_LEVEL = "dl"
    BEACON_KEY_CRASH_REPORTING_LEVEL = "cl"
    BEACON_KEY_VISIT_STORE_VERSION = "vs"

    # device data constants
    BEACON_KEY_DEVICE_OS = "os"
    BEACON_KEY_DEVICE_MANUFACTURER = "mf"
    BEACON_KEY_DEVICE_MODEL = "md"

    # timestamp constants
    BEACON_KEY_SESSION_START_TIME = "tv"
    BEACON_KEY_TRANSMISSION_TIME = "tx"

    # Action related constants
    BEACON_KEY_EVENT_TYPE = "et"
    BEACON_KEY_NAME = "na"
    BEACON_KEY_THREAD_ID = "it"
    BEACON_KEY_ACTION_ID = "ca"
    BEACON_KEY_PARENT_ACTION_ID = "pa"
    BEACON_KEY_START_SEQUENCE_NUMBER = "s0"
    BEACON_KEY_TIME_0 = "t0"
    BEACON_KEY_END_SEQUENCE_NUMBER = "s1"
    BEACON_KEY_TIME_1 = "t1"

    # data, error & crash capture constants
    BEACON_KEY_VALUE = "vl"
    BEACON_KEY_ERROR_CODE = "ev"
    BEACON_KEY_ERROR_REASON = "rs"
    BEACON_KEY_ERROR_STACKTRACE = "st"
    BEACON_KEY_ERROR_TECHNOLOGY_TYPE = "tt"

    # web request constants
    BEACON_KEY_WEBREQUEST_RESPONSECODE = "rc"
    BEACON_KEY_WEBREQUEST_BYTES_SENT = "bs"
    BEACON_KEY_WEBREQUEST_BYTES_RECEIVED = "br"

    CHARSET = "UTF-8"

    MAX_NAME_LEN = 250
    TAG_PREFIX = "MT"
    BEACON_DATA_DELIMITER = "&"

    next_session_id = 0

    def __init__(
        self,
        beacon_initializer: "SessionProxy",
        beacon_configuration: "BeaconConfiguration",
        device_id=None,
        session_start_time=None,
    ):
        self.logger = beacon_initializer.logger
        self.beacon_cache: BeaconCache = beacon_initializer.beacon_cache
        self.session_sequence_number = beacon_initializer.session_sequence_number
        self.beacon_key = BeaconKey(self.session_number, self.session_sequence_number)
        self.configuration = beacon_configuration

        if session_start_time is None:
            session_start_time: datetime = datetime.now()
        self.session_start_time: datetime = session_start_time

        # This allows user to set a DeviceID per session
        if device_id is None:
            device_id = self.configuration.openkit_configuration.deviceID
        self.device_id = device_id

        ip_address = beacon_initializer.ip_address
        if ip_address is None:
            ip_address = ""
        self.ip_address = ip_address

        self._next_id = 0
        self._next_sequence_number = 0

        self._lock = RLock()

        self.immutable_beacon_data = self.create_immutable_beacon_data()

    @property
    def next_id(self):
        with self._lock:
            self._next_id += 1
            return self._next_id

    @property
    def next_sequence_number(self):
        with self._lock:
            self._next_sequence_number += 1
            return self._next_sequence_number

    @property
    def session_number(self) -> int:
        self.next_session_id += 1
        return self.next_session_id

    def create_immutable_beacon_data(self) -> str:
        openkit_config = self.configuration.openkit_configuration

        string_parts = [
            # version and application information
            self.add_key_value_pair(self.BEACON_KEY_PROTOCOL_VERSION, PROTOCOL_VERSION),
            self.add_key_value_pair(self.BEACON_KEY_OPENKIT_VERSION, OPENKIT_VERSION),
            self.add_key_value_pair(self.BEACON_KEY_APPLICATION_ID, openkit_config.application_id),
            self.add_key_value_pair(self.BEACON_KEY_APPLICATION_NAME, openkit_config.application_name),
            self.add_key_value_pair(self.BEACON_KEY_APPLICATION_VERSION, openkit_config.application_version),
            self.add_key_value_pair(self.BEACON_KEY_PLATFORM_TYPE, PLATFORM_TYPE_OPENKIT),
            self.add_key_value_pair(self.BEACON_KEY_AGENT_TECHNOLOGY_TYPE, AGENT_TECHNOLOGY_TYPE),
            # device/visitor ID, session number and IP address
            self.add_key_value_pair(self.BEACON_KEY_VISITOR_ID, self.device_id),
            self.add_key_value_pair(self.BEACON_KEY_SESSION_NUMBER, self.session_number),
            self.add_key_value_pair(self.BEACON_KEY_SESSION_SEQUENCE, self.session_sequence_number),
            self.add_key_value_pair(self.BEACON_KEY_CLIENT_IP_ADDRESS, self.ip_address),
            # platform information
            self.add_key_value_pair(self.BEACON_KEY_DEVICE_OS, openkit_config.operating_system),
            self.add_key_value_pair(self.BEACON_KEY_DEVICE_MANUFACTURER, openkit_config.manufacturer),
            self.add_key_value_pair(self.BEACON_KEY_DEVICE_MODEL, openkit_config.model_id),
            self.add_key_value_pair(self.BEACON_KEY_DATA_COLLECTION_LEVEL, self.configuration.data_collection_level),
            self.add_key_value_pair(self.BEACON_KEY_CRASH_REPORTING_LEVEL, self.configuration.crash_reporting_level),
        ]

        return "".join(string_parts)

    def start_session(self):
        if not self.configuration.server_configuration.capture_enabled:
            return

        string_parts = [
            Beacon.build_basic_event_data(EventType.SESSION_START, None),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_PARENT_ACTION_ID, "0"),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_START_SEQUENCE_NUMBER, self.next_sequence_number),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_TIME_0, "0"),
        ]

        self.add_event_data(self.session_start_time, "".join(string_parts))

    def create_tag(self, parent_action_id: int, tracer_seq_no: int):

        server_id = self.configuration.server_configuration.server_id

        string_parts = [
            Beacon.TAG_PREFIX,
            f"_{PROTOCOL_VERSION}",
            f"_{server_id}",
            f"_{self.device_id}",
            f"_{self.session_number}",
            f"-{self.session_sequence_number}" if self.configuration.server_configuration.visit_store_version > 1 else "",
            f"_{quote(self.configuration.openkit_configuration.application_id)}",
            f"_{parent_action_id}",
            f"_{get_ident() & 0xffffffff}",  # 32 bits
            f"_{tracer_seq_no}",
        ]

        return "".join(string_parts)

    def add_action(self, action: ActionImpl):

        if not self.configuration.server_configuration.capture_enabled:
            return

        string_data = [
            self.build_basic_event_data(EventType.ACTION, action.name),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_ACTION_ID, action.id),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_PARENT_ACTION_ID, action.parent_action_id),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_START_SEQUENCE_NUMBER, action.start_seq_no),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_TIME_0, self.time_since_session_started(action.start_time)),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_END_SEQUENCE_NUMBER, action.end_sequence_number),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_TIME_1, int((action.end_time - action.start_time).total_seconds() * 1000)),
        ]

        self.add_action_data(action.start_time, "".join(string_data))

    def end_session(self, end_time: Optional[datetime] = None):
        if not self.configuration.server_configuration.capture_enabled:
            return

        if end_time is None:
            end_time = datetime.now()

        string_parts = [
            Beacon.build_basic_event_data(EventType.SESSION_END, None),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_PARENT_ACTION_ID, 0),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_START_SEQUENCE_NUMBER, self.next_sequence_number),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_TIME_0, self.time_since_session_started(end_time)),
        ]

        self.add_event_data(end_time, "".join(string_parts))

    def report_value(self, parent_action_id, value_name: str, value: Union[str, int, float], timestamp: Optional[datetime] = None):
        if not self.configuration.server_configuration.capture_enabled:
            return

        type_to_event_type = {
            str: EventType.VALUE_STRING,
            int: EventType.VALUE_INT,
            float: EventType.VALUE_DOUBLE,
        }
        event_type = type_to_event_type[type(value)]

        event_time, event_string = self.build_event(event_type, value_name, parent_action_id)
        if timestamp is not None:
            event_time = timestamp
        string_parts = [event_string, Beacon.add_key_value_pair(Beacon.BEACON_KEY_VALUE, value)]

        self.add_event_data(event_time, "".join(string_parts))

    def report_event(self, parent_action_id: int, event_name: str, timestamp: Optional[datetime] = None):
        if not self.configuration.server_configuration.capture_enabled:
            return

        if timestamp is None:
            timestamp = datetime.now()

        string_parts = [
            self.build_basic_event_data(EventType.NAMED_EVENT, event_name),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_PARENT_ACTION_ID, parent_action_id),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_START_SEQUENCE_NUMBER, self.next_sequence_number),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_TIME_0, self.time_since_session_started(timestamp)),
        ]

        self.add_event_data(timestamp, "".join(string_parts))

    def identify_user(self, user_tag: str, timestamp: Optional[datetime] = None):
        if not self.configuration.server_configuration.capture_enabled:
            return

        if timestamp is None:
            timestamp = datetime.now()

        string_parts = [
            self.build_basic_event_data(EventType.IDENTIFY_USER, user_tag),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_PARENT_ACTION_ID, 0),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_START_SEQUENCE_NUMBER, self.next_sequence_number),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_TIME_0, self.time_since_session_started(timestamp)),
        ]

        self.add_event_data(timestamp, "".join(string_parts))

    def report_error(self, parent_action_id: int, error_name: str, error_code: int, reason: str, timestamp: Optional[datetime] = None):
        if not self.configuration.server_configuration.capture_enabled:
            return

        if timestamp is None:
            timestamp = datetime.now()

        string_parts = [
            self.build_basic_event_data(EventType.ERROR, error_name),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_PARENT_ACTION_ID, parent_action_id),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_START_SEQUENCE_NUMBER, self.next_sequence_number),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_TIME_0, self.time_since_session_started(timestamp)),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_ERROR_CODE, error_code),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_ERROR_REASON, reason),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_ERROR_TECHNOLOGY_TYPE, ERROR_TECHNOLOGY_TYPE),
        ]

        self.add_event_data(timestamp, "".join(string_parts))

    def build_event(self, event_type: EventType, name: str, parent_action_id: int, event_time: Optional[datetime] = None) -> (datetime, str):
        if event_time is None:
            event_time = datetime.now()

        string_data = [
            Beacon.build_basic_event_data(event_type, name),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_PARENT_ACTION_ID, parent_action_id),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_START_SEQUENCE_NUMBER, self.next_sequence_number),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_TIME_0, self.time_since_session_started(event_time)),
        ]

        return event_time, "".join(string_data)

    def add_event_data(self, timestamp: datetime, string: str):
        if self.configuration.server_configuration.capture_enabled:
            self.beacon_cache.add_event(self.beacon_key, timestamp, string)

    def add_action_data(self, timestamp: datetime, string: str):
        if self.configuration.server_configuration.capture_enabled:
            self.beacon_cache.add_action(self.beacon_key, timestamp, string)

    def add_web_request(self, parent_action_id, web_request_tracer):
        string_parts = [
            Beacon.build_basic_event_data(EventType.WEB_REQUEST, quote_plus(web_request_tracer.url)),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_PARENT_ACTION_ID, parent_action_id),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_START_SEQUENCE_NUMBER, web_request_tracer.start_sequence_no),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_TIME_0, self.time_since_session_started(web_request_tracer.start_time)),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_END_SEQUENCE_NUMBER, web_request_tracer.end_sequence_no),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_TIME_1, self.time_since_session_started(web_request_tracer.end_time)),
        ]
        if hasattr(web_request_tracer, "response_code"):
            string_parts.append(Beacon.add_key_value_pair(Beacon.BEACON_KEY_WEBREQUEST_RESPONSECODE, web_request_tracer.response_code))
        if hasattr(web_request_tracer, "bytes_received"):
            string_parts.append(Beacon.add_key_value_pair(Beacon.BEACON_KEY_WEBREQUEST_BYTES_RECEIVED, web_request_tracer.bytes_received))
        if hasattr(web_request_tracer, "bytes_sent"):
            string_parts.append(Beacon.add_key_value_pair(Beacon.BEACON_KEY_WEBREQUEST_BYTES_RECEIVED, web_request_tracer.bytes_sent))

        self.add_event_data(self.session_start_time, "".join(string_parts))

    @property
    def current_timestamp(self):
        return int(datetime.now().timestamp() * 1000)

    def time_since_session_started(self, timestamp: datetime):
        return int((timestamp - self.session_start_time).total_seconds() * 1000)

    def update_server_configuration(self, server_configuration):
        self.logger.debug(f"Received new server configuration: {server_configuration}")
        self.configuration.server_configuration = server_configuration
        self.configuration.server_configured = True

    def send(self, http_client: "HttpClient", additional_params):
        while True:

            string_parts = [
                self.immutable_beacon_data,
                self.append_mutable_beacon_data(),
            ]

            prefix = "".join(string_parts)

            chunk = self.beacon_cache.get_next_beacon_chunk(
                self.beacon_key,
                prefix,
                self.configuration.server_configuration.beacon_size_in_bytes - 1024,
                Beacon.BEACON_DATA_DELIMITER,
            )

            if chunk is None or not chunk:
                return

            encoded_chunk = b""
            try:
                encoded_chunk = chunk.encode("UTF-8")
            except Exception as e:
                self.logger.error(f"Could not decode beacon chunk: {e}")
                self.beacon_cache.reset_chunked_data(self.beacon_key)
                return

            response = http_client.send_beacon_request(self.ip_address, encoded_chunk, additional_params)
            if response is None or response.status_code > 400:
                self.beacon_cache.reset_chunked_data(self.beacon_key)
                break
            else:
                self.beacon_cache.remove_chunked_data(self.beacon_key)

        return response

    @property
    def visit_store_version(self):
        return self.configuration.server_configuration.visit_store_version

    def append_mutable_beacon_data(self):
        string_parts = [
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_VISIT_STORE_VERSION, self.visit_store_version),
            Beacon.BEACON_DATA_DELIMITER,
            self.create_timestamp_data(),
            Beacon.BEACON_DATA_DELIMITER,
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_MULTIPLICITY, self.configuration.server_configuration.multiplicity),
        ]

        return "".join(string_parts)

    def create_timestamp_data(self):
        string_parts = [
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_TRANSMISSION_TIME, self.current_timestamp),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_SESSION_START_TIME, int(self.session_start_time.timestamp() * 1000)),
        ]

        return "".join(string_parts)

    @staticmethod
    def build_basic_event_data(event_type: EventType, name: Optional[str]):

        string_parts = [
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_EVENT_TYPE, str(event_type.value)),
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_NAME, name.strip()) if name is not None else "",
            Beacon.add_key_value_pair(Beacon.BEACON_KEY_THREAD_ID, str(get_ident() & 0xFFFFFFFF)),
        ]

        return "".join(string_parts)

    @staticmethod
    def add_key_value_pair(key: str, value: Union[str, int, float]):
        string_parts = [Beacon.append_key(key), str(value)]
        return "".join(string_parts)

    @staticmethod
    def append_key(key: str):
        string_parts = ["&", key, "="]
        return "".join(string_parts)

    def create_id(self):
        return self.next_id
