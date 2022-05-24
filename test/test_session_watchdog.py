import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from openkit.core.objects.session_proxy import SessionProxy
from openkit.core.session_watchdog import SessionWatchdogContext


class TestSessionWatchdog(unittest.TestCase):

    def test_split_timed_out_sessions(self):
        watchdog = SessionWatchdogContext()

        # Create session proxies
        session_1 = SessionProxy(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())
        session_2 = SessionProxy(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())
        session_1.split_and_create_initial_session = MagicMock()
        session_2.split_and_create_initial_session = MagicMock()

        # Setup server config
        session_1.server_config = MagicMock()
        session_1.server_config.session_timeout_in_milliseconds = 1000  # 1 second timeout
        session_1.server_config.max_session_duration_in_milliseconds = 3000
        session_1.server_config.session_split_by_idle_timeout_enabled = True
        session_1.server_config.session_split_by_session_duration_enabled = True

        session_2.server_config = MagicMock()
        session_2.server_config.session_timeout_in_milliseconds = 2000  # 2 seconds timeout
        session_2.server_config.max_session_duration_in_milliseconds = 3000
        session_2.server_config.session_split_by_idle_timeout_enabled = True
        session_2.server_config.session_split_by_session_duration_enabled = True

        # Setup beacon timings
        session_1.last_interaction_time = datetime.now() - timedelta(milliseconds=1500)  # Last interaction was 1.5 seconds ago
        session_2.last_interaction_time = datetime.now() - timedelta(milliseconds=1500)  # Last interaction was 1.5 seconds ago
        session_1.current_session.beacon.session_start_time = datetime.now() - timedelta(milliseconds=2000)  # Session started 2 seconds ago
        session_2.current_session.beacon.session_start_time = datetime.now() - timedelta(milliseconds=2000)  # Session started 2 seconds ago

        # Add the sessions to be split by timeout
        watchdog.sessions_to_split_by_timeout.extend([session_1, session_2])

        watchdog.split_timed_out_sessions()

        # Check that split_and_create_initial_session was called (it is over the timeout time)
        self.assertTrue(session_1.split_and_create_initial_session.called)

        # Check that split_and_create_initial_session was NOT called (it is still under the timeout time)
        self.assertFalse(session_2.split_and_create_initial_session.called)
