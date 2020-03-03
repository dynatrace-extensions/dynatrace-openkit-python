from datetime import datetime
from enum import Enum
import logging
from threading import RLock

from api import Session
from api.beacon_cache import BeaconCache, BeaconCacheEvictor
from protocol.http_client import HttpClient, DEFAULT_SERVER_ID
from core.beacon_sender import BeaconSender


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
DEFAULT_DATA_COLLECTION_LEVEL = DataCollectionLevel.USER_BEHAVIOR
DEFAULT_CRASH_REPORTING_LEVEL = CrashReportingLevel.OPT_IN_CRASHES


class Openkit:
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
    ):
        self.endpoint = endpoint
        self.application_id = application_id
        self.device_id = device_id
        self.os = os
        self.manufacturer = manufacturer
        self.version = version

        if logger is None:
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.WARNING)
            handler = logging.StreamHandler()
            handler.setLevel(logging.WARNING)
            logger.addHandler(handler)

        self.logger = logger
        self.shutdown = False

        # Cache
        self.beacon_cache = BeaconCache(logger)
        self.beacon_cache_evictor = BeaconCacheEvictor(
            logger, self.beacon_cache, beacon_cache_max_age, beacon_cache_lower_memory, beacon_cache_upper_memory
        )

        # HTTP Client
        self.http_client = HttpClient(self.logger, endpoint, DEFAULT_SERVER_ID, application_id)

        # Beacon Sender
        self.beacon_sender = BeaconSender(self.logger, self.http_client)

        # Session Watchdog
        # TODO: Implement Session Watchdog

        self._lock = RLock()

        self.beacon_cache_evictor.start()
        self.beacon_sender.initalize()

    def create_session(self, ip: str, start_time: datetime) -> Session:
        self.logger.debug(f"create_session({ip}, {start_time})")

        with self._lock:
            if not self.shutdown:
                # TODO: create BeaconConfiguration
                # TODO: create Beacon
                # TODO: start Session
                #

                session = Session(ip)
