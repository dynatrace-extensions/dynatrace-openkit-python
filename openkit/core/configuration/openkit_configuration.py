from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ... import Openkit


class OpenkitConfiguration:
    def __init__(self, openkit: "Openkit"):
        self.endpoint_url = openkit._endpoint
        self.deviceID = openkit._device_id
        self.openkit_type = "DynatraceOpenKit"
        self.application_id = openkit._application_id
        self.application_name = openkit._application_name
        self.application_version = openkit._version
        self.operating_system = openkit._os
        self.manufacturer = openkit._manufacturer
        self.model_id = "OpenKitDevice"
        self.default_server_id = 1
