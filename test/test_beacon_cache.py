import unittest
from datetime import datetime

from openkit.core.caching.beacon_cache import BeaconCacheRecord
from openkit.core.caching.beacon_key import BeaconKey


class TestBeaconCache(unittest.TestCase):

    def test_beacon_cache_record(self):
        record_a = BeaconCacheRecord(datetime(2022, 1, 1), "test")
        record_b = BeaconCacheRecord(datetime(2022, 1, 1), "test")

        assert record_a == record_b
        assert not record_a.marked_for_sending
        assert record_a.size() == 53
        assert record_a.data == "test"

    def test_beacon_key(self):
        key_a = BeaconKey(1, 2)
        key_b = BeaconKey(1, 2)
        key_c = BeaconKey(1, 3)

        assert key_a == key_b
        assert key_a != key_c
        assert key_a.beacon_id == 1
        assert key_a.beacon_seq_number == 2
