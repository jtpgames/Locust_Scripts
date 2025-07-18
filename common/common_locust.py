import logging
from abc import ABC, abstractmethod
from uuid import uuid1

import requests
from locust import events, User

from stopwatch import Stopwatch
from httpx import Client, Limits

class RepeatingClient(ABC):
    """
    Base class that implements the repetition, but not the actual data transfer.
    This way, we can create a client for different protocols, e.g., RepeatingHttpClient, RepeatingTCPClient, ...
    """
    def __init__(self, base_url: str, parent_user: User):
        self.base_url = base_url
        self.parent_user = parent_user
        self.ID = uuid1().int

    @abstractmethod
    def send_impl(self, endpoint, data=None, request_id=uuid1().int) -> (object, bool):
        pass

    def send(self, endpoint, data=None):
        logger = logging.getLogger('RepeatingClient')

        index_base_url_to_use = 0
        base_urls = [url.strip() for url in self.base_url.split(",")] if "," in self.base_url else [self.base_url]

        request_id = uuid1().int

        stopwatch = Stopwatch()

        original_wait_time = self.parent_user.wait_time
        self.parent_user.wait_time = lambda: 1
        number_of_tries = 0
        response = None
        successfully_sent = False
        while not successfully_sent:
            # noinspection PyBroadException
            try:
                url = base_urls[index_base_url_to_use] + endpoint
                number_of_tries += 1
                logger.info("[%i] (%i) Sending to %s", self.ID, request_id, url)
                response, successfully_sent = self.send_impl(url, data, request_id=request_id)
                logger.info("{} {} {}".format(self.ID, response, successfully_sent))
            except Exception as e:
                logger.error("[%i] (%i) %i. try: Exception occurred: %r", self.ID,  request_id, number_of_tries, e)
                # logger.exception("[%i] (%i) Exception details:", self.ID, request_id)

            if not successfully_sent:
                index_base_url_to_use += 1
                if len(base_urls) > index_base_url_to_use:
                    logger.warning(
                        "[%i] (%i) %i. try: Send failed. Sending to the next url in %i s",
                        self.ID,
                        request_id,
                        number_of_tries,
                        self.parent_user.wait_time()
                    )
                    self.parent_user.wait()
                else:
                    index_base_url_to_use = 0
                    logger.warning(
                        "[%i] (%i) %i. try: Send failed. Repeating in %i s",
                        self.ID,
                        request_id,
                        number_of_tries,
                        self.parent_user.wait_time()
                    )
                    self.parent_user.wait()

        stopwatch.stop()
        self.parent_user.wait_time = original_wait_time
        total_time_ms = int(stopwatch.duration * 1000)
        events.request_success.fire(request_type="POST", name=endpoint, response_time=total_time_ms, response_length=0)

        logger.info("[%i] (%i) Response time %s ms", self.ID, request_id, total_time_ms)

        return response


class RepeatingHttpClient(RepeatingClient):
    REQUEST_TIMEOUT = 60
    LOGGER = logging.getLogger('RepeatingHttpClient')

    def send_impl(self, url, data=None, request_id=uuid1().int) -> (object, bool):
        RepeatingHttpClient.LOGGER.info("POST")
        response = requests.post(url, json=data, headers={"Request-Id": str(request_id)}, timeout=RepeatingHttpClient.REQUEST_TIMEOUT)
        RepeatingHttpClient.LOGGER.info("Response: %s", response.status_code)

        successfully_sent = 200 <= response.status_code < 300

        return response, successfully_sent


class RepeatingHttpxClient(RepeatingClient):
    REQUEST_TIMEOUT = 60
    LOGGER = logging.getLogger('RepeatingHttpxClient')
    HTTP_POOL_LIMITS = Limits(max_connections=50000, max_keepalive_connections=1000, keepalive_expiry=30)
    CLIENT = Client(http2=True, limits=HTTP_POOL_LIMITS)

    def __init__(self, base_url: str, parent_user: User):
        super().__init__(base_url, parent_user)
        # logging.getLogger("httpx").setLevel(logging.DEBUG)
        # logging.getLogger("httpcore").setLevel(logging.DEBUG)

    def send_impl(self, url, data=None, request_id=uuid1().int) -> (object, bool):
        RepeatingHttpxClient.LOGGER.info("POST")
        headers = {"Request-Id": f"{request_id}"}
        response = RepeatingHttpxClient.CLIENT.post(url, json=data, headers=headers, timeout=RepeatingHttpxClient.REQUEST_TIMEOUT)
        RepeatingHttpxClient.LOGGER.info("[%i] (%i) Response: %s", self.ID, request_id, response.status_code)
        RepeatingHttpxClient.LOGGER.info("[%i] (%i) HTTP version: %s", self.ID, request_id, response.http_version)

        successfully_sent = 200 <= response.status_code < 300

        return response, successfully_sent
