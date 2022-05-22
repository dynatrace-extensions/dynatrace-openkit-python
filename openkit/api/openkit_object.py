from abc import abstractmethod


class OpenKitObject:

    @abstractmethod
    def _close(self):
        pass


class CancelableOpenKitObject(OpenKitObject):

    @abstractmethod
    def _cancel(self):
        pass
