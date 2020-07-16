import time
import requests
import logging
from api.openkit import Openkit


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.StreamHandler()])


def execute_and_trace_request(action, endpoint):
    tracer = action.trace_web_request(endpoint)
    tracer.start()

    rsp = requests.get(tracer.url)
    tracer.bytes_received = len(rsp.content)
    tracer.bytes_sent = 0

    tracer.stop(rsp.status_code)


app_name = "SimpleSampleApp"
beacon_url = "YOUR_BEACON_URI"
app_id = "YOUR_APP_ID"
device_id = 42

kit = Openkit(endpoint=beacon_url, application_id=app_id,
              device_id=device_id, version=0.1, application_name=app_name)

client_ip = "127.0.0.1"
session = kit.create_session(client_ip)
session.identify_user("openKitExampleUser")

root_action = session.enter_action("talk to postman")

execute_and_trace_request(root_action, "https://postman-echo.com/get?query=users")

root_action.report_value("sleepTime", 2000)

time.sleep(0.1)

root_action.report_event("Finished sleeping")

root_action.leave_action()

input("Press ENTER to continue")

session.end()
kit.shutdown()
