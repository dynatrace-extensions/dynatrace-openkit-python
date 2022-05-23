from abc import abstractmethod
from typing import List

from .openkit_object import OpenKitObject


class OpenKitComposite:
    _DEFAULT_ACTION_ID = 0

    def __init__(self):
        self._children: List[OpenKitObject] = []
        self._id = self._DEFAULT_ACTION_ID

    def _store_child_in_list(self, child: OpenKitObject):
        self._children.append(child)

    def _remove_child_from_list(self, child: OpenKitObject):
        self._children.remove(child)

    def _copy_children(self) -> List[OpenKitObject]:
        return self._children.copy()

    @property
    def _child_count(self) -> int:
        return len(self._children)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @abstractmethod
    def _on_child_closed(self, child: OpenKitObject):
        raise NotImplementedError("_on_child_closed() not implemented")
