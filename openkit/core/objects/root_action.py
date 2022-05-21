import logging
from datetime import datetime
from typing import Optional

from .base_action import BaseAction
from .leaf_action import LeafAction
from .null_action import NullAction
from ...api.action import Action
from ...api.root_action import RootAction
from ...api.session import Session
from ...protocol.beacon import Beacon


class RootActionImpl(BaseAction, RootAction):

    def __init__(self,
                 logger: logging.Logger,
                 parent: Session,
                 name: str,
                 beacon: Beacon,
                 timestamp: Optional[datetime] = None):
        super().__init__(logger, parent, name, beacon, timestamp)

    def enter_action(self, name: str, timestamp: Optional[datetime] = None) -> Action:
        if not name:
            self.logger.warning("action name must not be empty")
            return NullAction(self)

        self.logger.debug(f"enter_action({name}, {timestamp})")

        with self.lock:
            if not self.was_left:
                child = LeafAction(self.logger, self, name, self.beacon, timestamp)
                self._store_child_in_list(child)
                return child

        return NullAction(self)

    def __repr__(self):
        return f"RootActionImpl [sn={self.beacon.session_number}, id={self.id}, name={self.name}]"
