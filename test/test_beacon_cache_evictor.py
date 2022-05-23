import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from openkit.core.caching.beacon_cache import BeaconCache, BeaconCacheEvictor
from openkit.core.caching.beacon_key import BeaconKey


class TestBeaconCacheEvictor(unittest.TestCase):

    def test_space_eviction(self):
        logger = MagicMock()
        cache = BeaconCache(logger)
        max_age = 20 * 1000  # 20 seconds
        max_size = 1 * 1024 * 1024  # 1 MB
        evictor = BeaconCacheEvictor(logger, cache, max_age, max_size, 0)

        # Add around 5MB of data to the cache
        for i in range(5):
            big_data = "A" * 1024 * 1000  # About 1 MB
            cache.add_action(BeaconKey(i, i), datetime.now(), big_data)

        # Check that data was added to the cache
        assert cache.cache_size >= 5 * 1024 * 1000
        evictor.space_eviction()

        # Check that data was removed from the cache until it's below the max size
        assert cache.cache_size <= max_size

    def test_time_eviction(self):
        logger = MagicMock()
        cache = BeaconCache(logger)
        max_age = 20 * 1000  # 20 seconds
        max_size = 1 * 1024 * 1024  # 1 MB
        evictor = BeaconCacheEvictor(logger, cache, max_age, max_size, 0)

        # Add 1 record with current timestamp
        cache.add_action(BeaconKey(10, 10), datetime.now(), "A" * 1024 * 1000)

        # Add 5 records that are 30 seconds old
        for i in range(5):
            cache.add_action(BeaconKey(i, i), datetime.now() - timedelta(seconds=30), "test data")

        # Check that 6 actions have been added to the cache
        actions = sum([len(entry.actions) for entry in cache.beacons.values()])
        assert actions == 6

        evictor.time_eviction()
        # Check that the old actions have been removed from the cache
        actions = sum([len(entry.actions) for entry in cache.beacons.values()])
        assert actions == 1
