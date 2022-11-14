import logging
from abc import ABC, abstractmethod
from uuid import uuid1

import requests
from locust import events, User

from stopwatch import Stopwatch


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

        url = self.base_url + endpoint

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
                number_of_tries += 1
                logger.info("[%i] (%i) Sending to %s", self.ID, request_id, url)
                response, successfully_sent = self.send_impl(url, data, request_id=request_id)
                logger.info("{} {} {}".format(self.ID, response, successfully_sent))
            except Exception as e:
                logger.error("[%i] (%i) %i. try: Exception occurred: %s", self.ID,  request_id, number_of_tries, str(e))

            if not successfully_sent:
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
    def send_impl(self, url, data=None, request_id=uuid1().int) -> (object, bool):
        logger = logging.getLogger('RepeatingHttpClient')

        logger.info("POST")
        if data is not None:
            response = requests.post(url, json=data, headers={"Request-Id": str(request_id)}, timeout=30)
        else:
            response = requests.post(url, headers={"Request-Id": str(request_id)}, timeout=30)
        logger.info("Response: %s", response.status_code)

        successfully_sent = 200 <= response.status_code < 300

        return response, successfully_sent
