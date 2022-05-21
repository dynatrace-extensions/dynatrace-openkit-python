import random
from typing import Optional

MAX_VALUE = 2 ** 31 - 1


class SessionIDProvider:

    def __init__(self, initial_offset: Optional[int] = None):
        if initial_offset is None:
            initial_offset = random.randint(0, MAX_VALUE)
        self._initial_offset = initial_offset

    @property
    def next_session_id(self) -> int:
        if self._initial_offset == MAX_VALUE:
            self._initial_offset = 0

        self._initial_offset += 1
        return self._initial_offset




