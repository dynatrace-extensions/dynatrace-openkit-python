from enum import Enum


class EventType(Enum):
    ACTION = 1
    VALUE_STRING = 11
    VALUE_INT = 12
    VALUE_DOUBLE = 13
    NAMED_EVENT = 10
    SESSION_START = 18
    SESSION_END = 19
    WEB_REQUEST = 30
    ERROR = 40
    CRASH = 50
    IDENTIFY_USER = 60
