from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.beacon_sender import BeaconSendingContext


def send_status_request(context: "BeaconSendingContext", num_retries: int, init_retry_delay: int):
    retries = 0
    sleep_time = init_retry_delay
    while True:
        response = context.http_client.send_status_request(context)
        if response.is_ok_response() or response.is_too_many_requests() or retries >= num_retries or context.shutdown_requested:
            break
        else:
            context.logger.warning(f"Status request failed for {response.http_response.url}, response: {response.http_response}")

        context.sleep(sleep_time)
        sleep_time *= 2
        retries += 1

    return response
