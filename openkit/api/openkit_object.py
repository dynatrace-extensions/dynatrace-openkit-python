from abc import abstractmethod


class OpenKitObject:

    @abstractmethod
    def close(self):
        pass


class CancelableOpenKitObject(OpenKitObject):

    @abstractmethod
    def cancel(self):
        pass
