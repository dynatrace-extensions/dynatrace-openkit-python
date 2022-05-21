class OpenKitComposite:
    _DEFAULT_ACTION_ID = 0

    def __init__(self, **kwargs):
        self._children = []

    def _store_child_in_list(self, child):
        self._children.append(child)

    @property
    def _action_id(self):
        return self._DEFAULT_ACTION_ID

    def _on_child_closed(self, child: "OpenKitComposite"):
        raise NotImplementedError("_on_child_closed() not implemented")
