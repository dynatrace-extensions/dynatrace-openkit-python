from threading import RLock
from typing import Optional

from .http_client_configuration import HttpClientConfiguration
from .openkit_configuration import OpenkitConfiguration
from .privacy_configuration import PrivacyConfiguration
from .server_configuration import ServerConfiguration


class BeaconConfiguration:
    def __init__(
            self,
            openkit_config: OpenkitConfiguration,
            privacy_config: PrivacyConfiguration,
            server_id: int
    ):
        self.openkit_config = openkit_config
        self.privacy_config = privacy_config
        self.http_client_config = HttpClientConfiguration(openkit_config.endpoint_url,
                                                          openkit_config.default_server_id,
                                                          openkit_config.application_id)

        self.server_configured = False

        self._server_configuration: Optional[ServerConfiguration] = None
        self.server_config_update_callback = None
        self._lock = RLock()

    @property
    def server_configuration(self) -> ServerConfiguration:
        with self._lock:
            if self._server_configuration is None:
                self._server_configuration = ServerConfiguration()
            return self._server_configuration

    @server_configuration.setter
    def server_configuration(self, server_configuration):
        with self._lock:
            self._server_configuration = server_configuration

    @staticmethod
    def create_from(openkit_conf: OpenkitConfiguration, privacy_config: PrivacyConfiguration, server_id: int) -> \
            Optional["BeaconConfiguration"]:
        if not openkit_conf or not privacy_config:
            return None
        return BeaconConfiguration(openkit_conf,
                                   privacy_config,
                                   server_id)

    def enable_capture(self):
        self.server_configuration.capture_enabled = True

    def disable_capture(self):
        self.server_configuration.capture_enabled = False

    def update_capture(self, capture_enabled):
        self.server_configuration.capture_enabled = capture_enabled
        self.server_configured = True

    # TODO initializeServerConfiguration
    # TODO updateServerConfiguration
    # TODO notifyServerConfigurationUpdate
    # TODO setServerConfigurationUpdateCallback
