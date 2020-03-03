from .beacon import Beacon

import logging


class Session:
    def __init__(self, ip):

        self.is_finishing = False
        self.is_finished = False
        self.was_tried_for_ending = False

        beacon_configuration = ok
        beacon = Beacon()
        beacon.start_session()

    def __enter__(self):
        pass
