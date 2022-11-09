import threading


class CountDownLatch(object):
    def __init__(self, count = 1):
        self.count = count
        self.lock = threading.Condition()

    def count_down(self):
        self.lock.acquire()
        self.count -= 1
        if self.count <= 0:
            self.lock.notify_all()
        self.lock.release()

    def wait(self, timeout_ms):
        self.lock.acquire()
        self.lock.wait(timeout_ms / 1000.0)
        if self.count > 0:
            raise Exception("Timeout waiting for initialization")
        self.lock.release()
