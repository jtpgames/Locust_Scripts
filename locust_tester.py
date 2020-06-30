#!/usr/bin/env python
import time

from locust import HttpLocust, Locust, TaskSet, task, events, between

import json
import requests
from requests import RequestException

import logging


class AlarmDeviceBehavior(TaskSet):

    def send_alarm(self):
        json_msg = {
            'id': "070010",
            'body': "alarm"
        }

        json_string = json.dumps(json_msg)

        response = self.client.post("/fake_call", json_msg)

    @task(1)
    def fake_alarm(self):
        self.send_alarm()


class RepeatingHttpClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def post(self, endpoint, json_data):
        logger = logging.getLogger('RepeatingHttpClient')

        url = self.base_url + endpoint

        logger.info("Sending to %s", url)

        # TODO Simply use StopWatch instead of manually calculating total_time
        tau_trigger = time.time()

        successfully_sent = False
        while not successfully_sent:
            try:
                logger.debug("POST")
                response = requests.post(url, json=json_data)
                logger.debug("Response: %s", response.status_code)

                successfully_sent = 200 <= response.status_code < 300
            except RequestException:
                pass

        tau_ack = time.time()
        total_time = int((tau_ack - tau_trigger) * 1000)
        events.request_success.fire(request_type="POST", name=endpoint, response_time=total_time, response_length=0)

        logger.info("Response time %s ms", total_time)

        return response


class RepeatingHttpLocust(Locust):
    def __init__(self, *args, **kwargs):
        super(RepeatingHttpLocust, self).__init__(*args, **kwargs)
        self.client = RepeatingHttpClient(self.host)


class AlarmDevice(RepeatingHttpLocust):
    task_set = AlarmDeviceBehavior
    wait_time = between(1, 1)
