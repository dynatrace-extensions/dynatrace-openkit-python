from datetime import datetime, timedelta
import functools
import logging
import sys
from threading import RLock, Thread, Condition, Event
from typing import Dict, List

from .key import BeaconKey


@functools.total_ordering
class BeaconCacheRecord:
    def __init__(self, timestamp: datetime, data: str):
        self.timestamp = timestamp
        self.data = data
        self.marked_for_sending = False

    def size(self):
        return sys.getsizeof(self.data)

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __eq__(self, other):
        return self.timestamp == other.timestamp

    def __repr__(self):
        return f"BeaconCacheRecord({self.timestamp}, '{self.data}', {self.size()})"


class BeaconCacheEntry:
    def __init__(self):
        self.events: List[BeaconCacheRecord] = []
        self.actions: List[BeaconCacheRecord] = []
        self.events_being_sent: List[BeaconCacheRecord] = []
        self.actions_being_sent: List[BeaconCacheRecord] = []
        self.total_bytes = 0
        self.lock = RLock()

    def needs_data_copied_before_chunking(self):
        return not self.actions_being_sent and not self.events_being_sent

    def has_data_to_send(self):
        return self.events_being_sent or self.actions_being_sent

    def copy_data_for_chunking(self):
        self.actions_being_sent = self.actions
        self.events_being_sent = self.events
        self.actions = []
        self.events = []
        self.total_bytes = 0

    def get_chunk(self, chunk_prefix, max_size, delimiter):
        if not self.has_data_to_send():
            return ""

        beacon_builder = "".join([str(max_size), chunk_prefix])
        beacon_builder += self.chunkify_data_list(beacon_builder, self.events_being_sent, max_size, delimiter)
        beacon_builder += self.chunkify_data_list(beacon_builder, self.actions_being_sent, max_size, delimiter)

        return beacon_builder

    @staticmethod
    def chunkify_data_list(chunk_builder: str, data_being_sent: List[BeaconCacheRecord], max_size, delimiter):

        for record in data_being_sent:
            if len(chunk_builder) < max_size:
                record.marked_for_sending = True
                chunk_builder += f"{delimiter}{record.data}"
        return chunk_builder

    def reset_data_marked_for_sending(self):
        if not self.has_data_to_send():
            return

        num_bytes = 0
        for record in self.events_being_sent:
            record.marked_for_sending = False
            num_bytes += len(record.data)

        for record in self.actions_being_sent:
            record.marked_for_sending = False
            num_bytes += len(record.data)

        self.events_being_sent.extend(self.events)
        self.actions_being_sent.extend(self.actions)
        self.events = self.events_being_sent
        self.actions = self.actions_being_sent
        self.events_being_sent = []
        self.actions_being_sent = []

        self.total_bytes += num_bytes

    def remove_data_marked_for_sending(self):

        if not self.has_data_to_send():
            return

        marked_events = [record for record in self.events_being_sent if record.marked_for_sending]
        for event in marked_events:
            self.events_being_sent.remove(event)

        marked_actions = [record for record in self.actions_being_sent if record.marked_for_sending]
        for action in marked_actions:
            self.actions_being_sent.remove(action)


class BeaconCache:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._lock = RLock()
        self.beacons: Dict[int, BeaconCacheEntry] = dict()
        self.cache_size = 0

        # For threading, might change later
        self.observers: List[BeaconCacheEvictor] = []
        self.changed = False

    def add_observer(self, observer):
        self.observers.append(observer)

    def on_date_added(self):
        self.changed = True
        for observer in self.observers:
            observer.update()

    def update_size(self):
        with self._lock:
            self.cache_size = 0
            for key, entry in self.beacons.items():
                self.cache_size += entry.total_bytes

    def add_action(self, beacon_key: BeaconKey, timestamp: datetime, data: str):
        self.logger.debug(f"add_action(sn={beacon_key.beacon_id}, seq={beacon_key.beacon_seq_number}, timestamp={datetime}, data={data})")
        with self._lock:
            key = hash(beacon_key)
            entry = self.beacons.get(key, BeaconCacheEntry())

            record = BeaconCacheRecord(timestamp, data)

            with entry.lock:
                entry.actions.append(record)
                entry.total_bytes += record.size()

            self.beacons[key] = entry
            self.cache_size += record.size()

        self.on_date_added()

    def add_event(self, beacon_key: BeaconKey, timestamp: datetime, data: str):
        self.logger.debug(f"add_event(sn={beacon_key.beacon_id}, seq={beacon_key.beacon_seq_number}, timestamp={datetime}, data={data})")
        with self._lock:
            key = hash(beacon_key)
            entry = self.beacons.get(key, BeaconCacheEntry())

            record = BeaconCacheRecord(timestamp, data)

            with entry.lock:
                entry.events.append(record)
                entry.total_bytes += record.size()

            self.beacons[key] = entry
            self.cache_size += record.size()

        self.on_date_added()

    def get_next_beacon_chunk(self, key, chunk_prefix, max_size, delimiter):
        key = hash(key)
        with self._lock:
            entry = self.beacons.get(key)

        if entry is None:
            return

        if entry.needs_data_copied_before_chunking:
            with entry.lock:
                num_bytes = entry.total_bytes
                entry.copy_data_for_chunking()
            self.cache_size += -1 * num_bytes

        return entry.get_chunk(chunk_prefix, max_size, delimiter)

    def remove_chunked_data(self, key):
        key = hash(key)
        with self._lock:
            entry = self.beacons.get(key)

        if entry is None:
            return

        entry.remove_data_marked_for_sending()

    def reset_chunked_data(self, key):

        key = hash(key)
        with self._lock:
            entry = self.beacons.get(key)

        num_bytes = 0
        if entry is not None:
            with entry.lock:
                old_size = entry.total_bytes
                entry.reset_data_marked_for_sending()
                num_bytes = entry.total_bytes - old_size

        self.cache_size += num_bytes
        self.on_date_added()

    def delete_cache_entry(self, key):
        key = hash(key)
        self.logger.debug(f"Deleting cache entry {key}")
        with self._lock:
            entry = self.beacons.get(key)
            del self.beacons[key]

        if entry is not None:
            self.cache_size += -1 * entry.total_bytes
