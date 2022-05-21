class BeaconKey:
    def __init__(self, beacon_id: int, beacon_seq_num: int):
        self.beacon_id = beacon_id
        self.beacon_seq_number = beacon_seq_num

    def __eq__(self, other):
        if self.beacon_id != other.beacon_id:
            return False

        return self.beacon_seq_number == other.beacon_seq_number

    def __hash__(self):
        return 31 * self.beacon_id + self.beacon_seq_number

    def __str__(self):
        return f"[sn={self.beacon_id}, seq={self.beacon_seq_number}]"
