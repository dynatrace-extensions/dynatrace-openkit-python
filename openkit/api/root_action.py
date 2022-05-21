from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from .action import Action


class RootAction(ABC):

    @abstractmethod
    def enter_action(self, name: str, timestamp: Optional[datetime] = None) -> Action:
        pass
