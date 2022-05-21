from datetime import datetime
from typing import Optional

from .base_action import BaseAction


class LeafAction(BaseAction):

    def __init__(self, logger, parent, name, beacon, timestamp: Optional[datetime] = None):
        super().__init__(logger, parent, name, beacon, timestamp)
