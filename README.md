# Dynatrace OpenKit Python

| :bangbang: | Not supported by dynatrace, use at your own risk! |
|:----------:|:--------------------------------------------------|

This project provides a python implementation
of [Dynatrace OpenKit](https://www.dynatrace.com/support/help/extend-dynatrace/openkit)

## Quickstart

`pip install openkit`

```python
import time

from openkit import OpenKit


def main():
    beacon_url = "https://my.beacon.url/mbeacon"
    app_id = "my-application-id"
    ok = OpenKit(beacon_url, app_id, 1)

    # Create a session and identify the user
    session = ok.create_session("192.168.15.1")
    session.identify_user("david")

    # Trace a web request and a user action
    session.trace_web_request("https://www.google.com")
    session.enter_action("test_action")

    # End the session
    time.sleep(1)
    session.end()

    time.sleep(5)
    ok.shutdown()


if __name__ == "__main__":
    main()

```