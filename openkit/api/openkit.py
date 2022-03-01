from datetime import datetime
from enum import Enum
import logging
from threading import RLock
from typing import Optional, List

from core.caching.beacon_cache import BeaconCache, BeaconCacheEvictor
from protocol.http_client import HttpClient, DEFAULT_SERVER_ID
from core.beacon_sender import BeaconSender
from core.session import OpenKitComposite, Session, SessionProxy, NullSession
from core.configuration.openkit_configuration import OpenkitConfiguration


class DataCollectionLevel(Enum):
    OFF = 0
    PERFORMANCE = 1
    USER_BEHAVIOR = 2


class CrashReportingLevel(Enum):
    OFF = 0
    OPT_OUT_CRASHES = 1
    OPT_IN_CRASHES = 2


DEFAULT_OPERATING_SYSTEM = "Openkit"
DEFAULT_MANUFACTURER = "Dynatrace"
DEFAULT_MODEL_ID = "OpenKitDevice"
DEFAULT_APPLICATION_VERSION = "Unknown version"
DEFAULT_MAX_RECORD_AGE_IN_MILLIS = 105 * 60 * 1000  # 1 hour, 45 minutes
DEFAULT_LOWER_MEMORY_BOUNDARY_IN_BYTES = 80 * 1024 * 1024  # 80 MB
DEFAULT_UPPER_MEMORY_BOUNDARY_IN_BYTES = 100 * 1024 * 1024  # 100 MB
DEFAULT_DATA_COLLECTION_LEVEL = DataCollectionLevel.USER_BEHAVIOR.value
DEFAULT_CRASH_REPORTING_LEVEL = CrashReportingLevel.OPT_IN_CRASHES.value


class Openkit(OpenKitComposite):
    def __init__(
        self,
        endpoint: str,
        application_id: str,
        device_id: str,
        logger: logging.Logger = None,
        os: str = DEFAULT_OPERATING_SYSTEM,
        manufacturer: str = DEFAULT_MANUFACTURER,
        version: str = DEFAULT_APPLICATION_VERSION,
        beacon_cache_max_age: int = DEFAULT_MAX_RECORD_AGE_IN_MILLIS,
        beacon_cache_lower_memory: int = DEFAULT_LOWER_MEMORY_BOUNDARY_IN_BYTES,
        beacon_cache_upper_memory: int = DEFAULT_UPPER_MEMORY_BOUNDARY_IN_BYTES,
        application_name="",
        data_collection_level=DEFAULT_DATA_COLLECTION_LEVEL,
        crash_reporting_level=DEFAULT_CRASH_REPORTING_LEVEL,
    ):
        super().__init__()
        self._endpoint = endpoint
        self._application_id = application_id
        self._device_id = device_id
        self._os = os
        self._manufacturer = manufacturer
        self._version = version
        self._application_name = application_name

        self._data_collection_level = data_collection_level
        self._crash_reporting_level = crash_reporting_level

        if logger is None:
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.WARNING)
            handler = logging.StreamHandler()
            handler.setLevel(logging.WARNING)
            logger.addHandler(handler)

        self._logger = logger
        self._shutdown = False

        # Sessions
        self._children: List[Session] = []

        # Cache
        self._beacon_cache = BeaconCache(logger)
        self._beacon_cache_evictor = BeaconCacheEvictor(
            logger, self._beacon_cache, beacon_cache_max_age, beacon_cache_lower_memory, beacon_cache_upper_memory
        )

        # HTTP Client
        self._http_client = HttpClient(self._logger, endpoint, DEFAULT_SERVER_ID, application_id)

        # Beacon Sender
        self._beacon_sender = BeaconSender(self._logger, self._http_client)

        # Session Watchdog
        # TODO: Implement Session Watchdog

        self._lock = RLock()

        self._beacon_cache_evictor.start()
        self._beacon_sender.initalize()

        self._openkit_configuration = OpenkitConfiguration(self)

    def create_session(self, ip: str, start_time: Optional[datetime] = None, device_id=None) -> Session:
        self._logger.debug(f"create_session(ip={ip}, start_time={start_time}, device_id={device_id})")

        with self._lock:
            if not self._shutdown:
                session_proxy = SessionProxy(self, self._beacon_sender, ip, device_id=device_id, start_time=start_time)
                self._children.append(session_proxy)
                return session_proxy

        return NullSession()

    def _on_child_closed(self, child):
        with self._lock:
            self._children.remove(child)

    def shutdown(self):
        self._logger.debug("Openkit shutdown requested")
        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True

        for child in self._children:
            try:
                child.end()
            except Exception as e:
                self._logger.error(f"Could not close {child}: {e}")

        self._beacon_cache_evictor.stop()
        self._beacon_sender.shutdown()
