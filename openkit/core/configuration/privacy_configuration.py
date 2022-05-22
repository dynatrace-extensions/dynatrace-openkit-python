from enum import Enum


class DataCollectionLevel(Enum):
    OFF = 0
    PERFORMANCE = 1
    USER_BEHAVIOR = 2

    def as_beacon_value(self):
        return f"{self.value}"

    @staticmethod
    def default_value(self) -> "DataCollectionLevel":
        return DataCollectionLevel.USER_BEHAVIOR


class CrashReportingLevel(Enum):
    OFF = 0
    OPT_OUT_CRASHES = 1
    OPT_IN_CRASHES = 2

    def as_beacon_value(self):
        return f"{self.value}"

    @staticmethod
    def default_value(self) -> "CrashReportingLevel":
        return CrashReportingLevel.OPT_IN_CRASHES


class PrivacyConfiguration:

    def __init__(self, data_collection_level: DataCollectionLevel, crash_reporting_level: CrashReportingLevel):
        self.data_collection_level = data_collection_level
        self.crash_reporting_level = crash_reporting_level

    @property
    def device_id_sending_allowed(self) -> bool:
        return self.data_collection_level == DataCollectionLevel.USER_BEHAVIOR

    @property
    def session_number_reporting_allowed(self) -> bool:
        return self.data_collection_level == DataCollectionLevel.USER_BEHAVIOR

    @property
    def web_request_tracing_allowed(self) -> bool:
        return self.data_collection_level != DataCollectionLevel.OFF

    @property
    def session_reporting_allowed(self) -> bool:
        return self.data_collection_level != DataCollectionLevel.OFF

    @property
    def action_reporting_allowed(self) -> bool:
        return self.data_collection_level != DataCollectionLevel.OFF

    @property
    def value_reporting_allowed(self) -> bool:
        return self.data_collection_level == DataCollectionLevel.USER_BEHAVIOR

    @property
    def event_reporting_allowed(self) -> bool:
        return self.data_collection_level == DataCollectionLevel.USER_BEHAVIOR

    @property
    def error_reporting_allowed(self) -> bool:
        return self.data_collection_level != DataCollectionLevel.OFF

    @property
    def crash_reporting_allowed(self) -> bool:
        return self.crash_reporting_level == CrashReportingLevel.OPT_IN_CRASHES

    @property
    def user_identification_allowed(self) -> bool:
        return self.data_collection_level == DataCollectionLevel.USER_BEHAVIOR
