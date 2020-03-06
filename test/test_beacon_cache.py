from datetime import datetime, timedelta
import logging
import sys

sys.path.append("..")

from core.caching.beacon_cache import BeaconCache, BeaconCacheEvictor

logger = logging.getLogger(__name__)


def test_cache_space_eviction():

    c = BeaconCache(logger)
    minimum_cache_size = 1 * 1024 * 1024  # 1 MB
    b = BeaconCacheEvictor(logger, c, 20000, 1 * 1024 * 1024, 0)
    b.start()

    # Adds about 4.88 MB of data
    for i in range(5):
        c.add_action(i, datetime.now(), "A" * 1024 * 1000)

    b.space_eviction()

    # Should be 0.98 MB left (< 1MB)
    assert c.cache_size <= minimum_cache_size

    b.stop()


def test_cache_time_eviction():

    c = BeaconCache(logger)

    # The maximum record age is 20 seconds
    b = BeaconCacheEvictor(logger, c, 20000, 1 * 1024 * 1024, 0)
    b.start()

    # Adds 1 record with current timestamp
    c.add_action(10, datetime.now(), "A" * 1024 * 1000)

    # Adds 5 records that are 30 seconds old
    for i in range(5):
        c.add_action(i, datetime.now() - timedelta(seconds=30), "A" * 1024 * 1000)

    b.time_eviction()
    b.stop()

    # 5 records out of 6 should be removed, only 1 left
    actions = sum([len(entry.actions) for entry in c.beacons.values()])
    assert actions == 1
