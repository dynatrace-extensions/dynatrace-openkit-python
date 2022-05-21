import logging
from datetime import datetime
from typing import Optional

from .session import SessionImpl
from ..caching.beacon_cache import BeaconCache
from ..configuration import OpenkitConfiguration
from ..configuration.beacon_configuration import BeaconConfiguration
from ..configuration.privacy_configuration import PrivacyConfiguration
from ...api.composite import OpenKitComposite
from ...protocol.beacon import Beacon
from ...providers.session_id import SessionIDProvider


class SessionCreator:

    def __init__(self,
                 logger: logging.Logger,
                 openkit_config: OpenkitConfiguration,
                 privacy_config: PrivacyConfiguration,
                 beacon_cache: BeaconCache,
                 ip_address: str,
                 server_id: int,
                 session_id_provider: SessionIDProvider):
        self.logger = logger
        self.openkit_config = openkit_config
        self.privacy_config = privacy_config
        self.beacon_cache = beacon_cache
        self.ip_address = ip_address
        self.server_id = server_id
        self.session_id_provider = session_id_provider
        self.session_sequence_number = 0

    def create_session(self,
                       parent: OpenKitComposite,
                       device_id: Optional[int] = None,
                       timestamp: Optional[datetime] = None) -> SessionImpl:
        beacon_config = BeaconConfiguration.create_from(self.openkit_config, self.privacy_config, self.server_id)
        beacon = Beacon(self, beacon_config, device_id, timestamp)
        session = SessionImpl(self.logger, parent, beacon)

        self.session_sequence_number += 1

        return session

    def reset(self):
        self.session_sequence_number = 0
