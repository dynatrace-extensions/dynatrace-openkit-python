from datetime import datetime, timedelta
from threading import Thread, Condition, Event
import logging

from .cache import BeaconCache


class BeaconCacheEvictor(Thread):
    def __init__(
        self,
        logger: logging.Logger,
        beacon_cache: BeaconCache,
        beacon_cache_max_age: int,
        beacon_cache_lower_memory: int,
        beacon_cache_upper_memory: int,
    ):
        self.logger = logger
        self.beacon_cache = beacon_cache
        self.beacon_cache_max_age = beacon_cache_max_age
        self.beacon_cache_lower_memory = beacon_cache_lower_memory
        self.beacon_cache_upper_memory = beacon_cache_upper_memory

        self.record_added = False
        self._lock = Condition()
        self.shutdown_flag = Event()
        super().__init__(name="BeaconCacheEvictor")

    def run(self) -> None:
        self.beacon_cache.add_observer(self)

        while not self.shutdown_flag.is_set():
            with self._lock:
                while not self.record_added:
                    self._lock.wait()

                self.record_added = False

            self.logger.debug("Running Beacon Cache Evictor")
            self.time_eviction()
            self.space_eviction()

        self.logger.debug("Exiting Beacon Cache Evictor Thread")

    def update(self):
        with self._lock:
            self.record_added = True
            self._lock.notify_all()

    def stop(self):
        with self._lock:
            self.record_added = True
            self.shutdown_flag.set()
            self._lock.notify_all()

    def time_eviction(self):
        with self._lock:
            min_allowed_time = datetime.now() - timedelta(milliseconds=self.beacon_cache_max_age)
            self.logger.debug(f"Deleting all beacon records with a timestamp older than {min_allowed_time}")

            actions_deleted = 0
            events_deleted = 0
            for key, entry in self.beacon_cache.beacons.items():
                with entry.lock:
                    old_len_actions = len(entry.actions)
                    old_len_events = len(entry.events)
                    entry.actions = [action for action in entry.actions if action.timestamp > min_allowed_time]
                    entry.events = [event for event in entry.events if event.timestamp > min_allowed_time]
                    entry.total_bytes = sum(action.size() for action in entry.actions) + sum(event.size() for event in entry.events)
                    actions_deleted += old_len_actions - len(entry.actions)
                    events_deleted += old_len_events - len(entry.events)

            self.logger.debug(f"Deleted {actions_deleted} actions and {events_deleted} events from the cache")
            self.beacon_cache.update_size()

    def space_eviction(self):
        with self._lock:
            self.logger.debug(
                f"Deleting old beacon records until the cache is smaller than {self.beacon_cache_lower_memory / 1024 / 1024} MB. The cache is {self.beacon_cache.cache_size / 1024 / 1024:.2f} MB at the moment"
            )

            while self.beacon_cache.cache_size > self.beacon_cache_lower_memory and self.beacon_cache.beacons:

                for key, entry in self.beacon_cache.beacons.items():
                    with entry.lock:
                        # If there are no actions, remove the oldest event
                        if entry.events and not entry.actions:
                            oldest_event = min(entry.events)
                            entry.events.remove(oldest_event)
                            entry.total_bytes -= oldest_event.size()
                            break

                        # If there are no events, remove the oldest action
                        elif entry.actions and not entry.events:
                            oldest_action = min(entry.actions)
                            entry.actions.remove(oldest_action)
                            entry.total_bytes -= oldest_action.size()
                            break

                        # If there are events and actions, remove the oldest of the two
                        if entry.events and entry.actions:
                            oldest_event = min(entry.events)
                            oldest_action = min(entry.actions)
                            if oldest_event < oldest_action:
                                entry.events.remove(oldest_event)
                                entry.total_bytes -= oldest_event.size()
                                break
                            else:
                                entry.actions.remove(oldest_action)
                                entry.total_bytes -= oldest_action.size()
                                break
                self.beacon_cache.update_size()

            self.logger.debug(f"The cache is {self.beacon_cache.cache_size / 1024 / 1024:.2f} MB after the cleanup")
