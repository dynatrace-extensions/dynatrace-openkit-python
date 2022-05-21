from threading import RLock
import typing

from .server_configuration import ServerConfiguration


if typing.TYPE_CHECKING:
    from .openkit_configuration import OpenkitConfiguration


class BeaconConfiguration:
    def __init__(
        self,
        openkit_configuration: "OpenkitConfiguration",
        server_id: int,
        data_collection_level,
        crash_reporting_level,
    ):
        self.openkit_configuration = openkit_configuration
        self.data_collection_level = data_collection_level
        self.crash_reporting_level = crash_reporting_level
        self.server_configured = False
        self._server_configuration = None
        self._lock = RLock()

    @property
    def server_configuration(self):
        with self._lock:
            if self._server_configuration is None:
                self._server_configuration = ServerConfiguration()
            return self._server_configuration

    @server_configuration.setter
    def server_configuration(self, server_configuration):
        with self._lock:
            self._server_configuration = server_configuration
