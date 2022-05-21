import logging
from threading import RLock
from typing import List, Optional

from .constants import DEFAULT_APPLICATION_VERSION, \
    DEFAULT_CRASH_REPORTING_LEVEL, \
    DEFAULT_DATA_COLLECTION_LEVEL, \
    DEFAULT_LOWER_MEMORY_BOUNDARY_IN_BYTES, \
    DEFAULT_MANUFACTURER, \
    DEFAULT_MAX_RECORD_AGE_IN_MILLIS, \
    DEFAULT_OPERATING_SYSTEM, \
    DEFAULT_UPPER_MEMORY_BOUNDARY_IN_BYTES
from .openkit_object import OpenKitObject
from .session import Session
from ..core.beacon_sender import BeaconSender
from ..core.caching import BeaconCache, BeaconCacheEvictor
from ..core.configuration import OpenkitConfiguration
from ..core.objects.composite import OpenKitComposite
from ..protocol.http_client import DEFAULT_SERVER_ID, HttpClient


class OpenKit(OpenKitObject, OpenKitComposite):

    def __init__(self,
                 endpoint: str,
                 application_id: str,
                 device_id: int,
                 logger: Optional[logging.Logger] = None,
                 os: Optional[str] = DEFAULT_OPERATING_SYSTEM,
                 manufacturer: Optional[str] = DEFAULT_MANUFACTURER,
                 version: Optional[str] = DEFAULT_APPLICATION_VERSION,
                 beacon_cache_max_age: Optional[int] = DEFAULT_MAX_RECORD_AGE_IN_MILLIS,
                 beacon_cache_lower_memory: Optional[int] = DEFAULT_LOWER_MEMORY_BOUNDARY_IN_BYTES,
                 beacon_cache_upper_memory: Optional[int] = DEFAULT_UPPER_MEMORY_BOUNDARY_IN_BYTES,
                 application_name: Optional[str] = "",
                 data_collection_level: Optional[int] = DEFAULT_DATA_COLLECTION_LEVEL,
                 crash_reporting_level: Optional[int] = DEFAULT_CRASH_REPORTING_LEVEL):
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
        self._beacon_cache_evictor = BeaconCacheEvictor(logger,
                                                        self._beacon_cache,
                                                        beacon_cache_max_age,
                                                        beacon_cache_lower_memory,
                                                        beacon_cache_upper_memory)

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

    def wait_for_init_completion(self, timeout_ms: Optional[int] = None) -> bool:
        raise NotImplementedError("Wait for init completion is not implemented")

    def initialized(self) -> bool:
        raise NotImplementedError("Initialized is not implemented")

    def create_session(self, ip_address: Optional[str] = None, timestamp: Optional[int] = None) -> Session:
        self._logger.debug(f"create_session({ip_address}, {timestamp})")
        with self._lock:
            if not self._shutdown:
                session_proxy = SessionProxy(self, self._beacon_sender, ip, device_id=device_id, start_time=start_time)
                self._store_child_in_list(session_proxy)
                return session_proxy

    def shutdown(self) -> None:
        self._logger.debug("Openkit shutdown requested")
        with self._lock:
            if self._shutdown:
                return
            self._shutdown = True

        children = self._copy_children()
        for child in children:
            child.close()

        # TODO - stop watchdog
        self._beacon_cache_evictor.stop()
        self._beacon_sender.shutdown()

    def close(self):
        self.shutdown()

    def _on_child_closed(self, child: OpenKitObject):
        with self._lock:
            self._remove_child_from_list(child)
