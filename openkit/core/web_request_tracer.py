from datetime import datetime
from protocol.beacon import Beacon
from core.session import OpenKitComposite


class WebRequestTracer:

    def __init__(self, parent: OpenKitComposite, url: str, beacon: Beacon):
        self.url = url
        self.parent_action_id = parent.id
        self.start_time = datetime.now()
        self.beacon = beacon
        self.start_sequence_no = self.beacon.next_sequence_number
        self.tag = self.beacon.create_tag(self.parent_action_id, self.start_sequence_no)
    
    def start(self):
        with self.beacon._lock:
            self.start_time = datetime.now()

    def stop(self, response_code):
        with self.beacon._lock:
            self.response_code = response_code
            self.end_time = datetime.now()
            self.end_sequence_no = self.beacon.next_sequence_number
            self.beacon.add_web_request(self.parent_action_id, self)
    
    def close(self):
        self.stop(self.response_code)
