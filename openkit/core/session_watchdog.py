import logging
import time
from datetime import datetime, timedelta
from threading import Event, RLock, Thread
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .objects.session_proxy import SessionProxy, SessionImpl


class SessionWatchdogContext:
    DEFAULT_SLEEP_TIME = timedelta(seconds=5)

    def __init__(self):
        self._shutdown = False
        self.sessions_to_close: List["SessionImpl"] = []
        self.sessions_to_split_by_timeout: List["SessionProxy"] = []

        self.lock = RLock()

    def execute(self):
        duration_to_next_close = self.close_expired_sessions()
        duration_to_next_split = self.split_timed_out_sessions()

        try:
            sleep_time = min(duration_to_next_close, duration_to_next_split)
            time.sleep(sleep_time.total_seconds())
        except KeyboardInterrupt:
            self.request_shutdown()

    def split_timed_out_sessions(self) -> timedelta:
        sleep_time: timedelta = self.DEFAULT_SLEEP_TIME
        sessions_to_split = self.sessions_to_split_by_timeout.copy()

        for session_proxy in sessions_to_split:
            next_session_split_time = session_proxy.split_session_by_time()
            if next_session_split_time == datetime(1970, 1, 1):
                self.sessions_to_split_by_timeout.remove(session_proxy)
                continue

            now = datetime.now()
            duration_to_next_split = next_session_split_time - now
            if duration_to_next_split < timedelta(seconds=0):
                continue

            sleep_time = min(sleep_time, duration_to_next_split)

        return sleep_time

    def close_expired_sessions(self) -> timedelta:
        sleep_time: timedelta = self.DEFAULT_SLEEP_TIME
        sessions_to_end: List["SessionImpl"] = []

        sessions_to_close = self.sessions_to_close.copy()
        for session in sessions_to_close:
            now = datetime.now()
            grace_period_end = session.split_by_events_grace_period_end_time
            grace_period_expired = now >= grace_period_end
            if grace_period_expired:
                sessions_to_end.append(session)
                self.sessions_to_close.remove(session)
                continue

            sleep_time_to_grace_period_end = grace_period_end - now
            sleep_time = min(sleep_time, sleep_time_to_grace_period_end)

        for session in sessions_to_end:
            session.end(send_end_event=False)

        return sleep_time

    def request_shutdown(self):
        with self.lock:
            self._shutdown = True

    def shutdown_requested(self):
        with self.lock:
            return self._shutdown

    def close_or_enqueue_for_closing(self, session: "SessionImpl", close_period: timedelta):
        if session.try_end():
            return

        close_time = datetime.now() + close_period
        session._split_by_events_grace_period_end_time = close_time
        with self.lock:
            self.sessions_to_close.append(session)

    def dequeue_from_closing(self, session: "SessionImpl"):
        with self.lock:
            if session in self.sessions_to_close:
                self.sessions_to_close.remove(session)

    def add_to_split_by_timeout(self, session: "SessionProxy"):
        if session.finished:
            return
        with self.lock:
            self.sessions_to_split_by_timeout.append(session)

    def remove_from_split_by_timeout(self, session: "SessionProxy"):
        with self.lock:
            if session in self.sessions_to_split_by_timeout:
                self.sessions_to_split_by_timeout.remove(session)


class SessionWatchdogThread(Thread):
    def __init__(self, logger: logging.Logger, context: SessionWatchdogContext):
        Thread.__init__(self, name="SessionWatchdogThread", daemon=True)
        self.logger = logger
        self.shutdown_flag = Event()
        self.context = context

    def run(self):
        self.logger.debug("SessionWatchdogThread - Running")
        while not self.context.shutdown_requested():
            self.context.execute()

        self.logger.info("SessionWatchdogThread - Exiting")

    def interrupt(self):
        self.shutdown_flag.set()


class SessionWatchdog:
    SHUTDOWN_TIMEOUT = timedelta(seconds=2)

    def __init__(self, logger: logging.Logger, context: SessionWatchdogContext):
        self.logger = logger
        self.context = context
        self.thread: Optional[SessionWatchdogThread] = None

    def initialize(self):
        self.thread = SessionWatchdogThread(self.logger, self.context)
        self.thread.start()

    def shutdown(self):
        self.logger.debug("SessionWatchdog - Shutting down")
        self.context.request_shutdown()

        if self.thread is None:
            return

        self.thread.interrupt()
        self.thread = None

    def close_or_enqueue_for_closing(self, session: "SessionImpl", close_period: timedelta):
        self.context.close_or_enqueue_for_closing(session, close_period)

    def dequeue_from_closing(self, session: "SessionImpl"):
        self.context.dequeue_from_closing(session)

    def add_to_split_by_timeout(self, session: "SessionProxy"):
        self.context.add_to_split_by_timeout(session)

    def remove_from_split_by_timeout(self, session: "SessionProxy"):
        self.context.remove_from_split_by_timeout(session)
