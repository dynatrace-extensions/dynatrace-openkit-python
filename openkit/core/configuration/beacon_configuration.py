from threading import RLock
import typing

from core.configuration.server_configuration import ServerConfiguration


if typing.TYPE_CHECKING:
    from core.configuration.openkit_configuration import OpenkitConfiguration


class BeaconConfiguration:
    def __init__(
        self, openkit_configuration: "OpenkitConfiguration", server_id: int, data_collection_level, crash_reporting_level,
    ):
        self.openkit_configuration = openkit_configuration
        self.data_collection_level = data_collection_level
        self.crash_reporting_level = crash_reporting_level
        self._server_configuration = None
        self._lock = RLock()

    @property
    def server_configuration(self):
        if self._server_configuration is None:
            with self._lock:
                if self._server_configuration is None:
                    return ServerConfiguration()
                return self._server_configuration

    @server_configuration.setter
    def server_configuration(self, server_configuration):
        with self._lock:
            self._server_configuration = server_configuration
