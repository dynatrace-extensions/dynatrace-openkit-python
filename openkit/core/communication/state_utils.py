from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.beacon_sender import BeaconSendingContext
    from ...vendor.mureq.mureq import Response


def is_successful(response: "Response"):
    return response.status_code < 400


def send_status_request(context: "BeaconSendingContext", num_retries: int, init_retry_delay: int):

    retries = 0
    sleep_time = init_retry_delay
    while True:
        response = context.http_client.send_status_request(context)
        if response.status_code <= 400 or response.status_code == 429 or retries >= num_retries or context.shutdown_requested:
            break

        context.sleep(sleep_time)
        sleep_time *= 2
        retries += 1

    return response
