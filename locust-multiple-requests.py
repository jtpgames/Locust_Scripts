#!/usr/bin/env python
import time

from locust import Locust, TaskSet, task, events, between

import json
import requests

import logging

from abc import ABC, abstractmethod


class AlarmDeviceBehavior(TaskSet):

    def send_alarm(self):
        json_msg = {
            'id': "070010",
            'body': "alarm"
        }

        json_string = json.dumps(json_msg)

        response = self.client.send("/fake_call", json_msg)

    def get_status(self):
        json_msg = {
            'id': "070010",
        }

        json_string = json.dumps(json_msg)

        response = self.client.send("/get_status", json_msg)

    @task(1)
    def fake_alarm(self):
        self.send_alarm()

    @task(2)
    def alarm_status(self):
        self.get_status()


class RepeatingClient(ABC):
    """
    Base class that implements the repetition, but not the actual data transfer.
    This way, we can create a client for different protocols, e.g., RepeatingHttpClient, RepeatingTCPClient, ...
    """
    def __init__(self, base_url):
        self.base_url = base_url

    @abstractmethod
    def send_impl(self, endpoint, data) -> (object, bool):
        pass

    def send(self, endpoint, data):
        logger = logging.getLogger('RepeatingClient')

        url = self.base_url + endpoint

        logger.info("Sending to %s", url)

        # TODO Simply use StopWatch instead of manually calculating total_time
        # this might also be more precise, as Stopwatch uses perf_counter.
        tau_trigger = time.time()

        response = None
        successfully_sent = False
        while not successfully_sent:
            # noinspection PyBroadException
            try:
                response, successfully_sent = self.send_impl(url, data)
                logger.info("{} {}".format(response, successfully_sent))
            except Exception:
                pass

        tau_ack = time.time()
        total_time = int((tau_ack - tau_trigger) * 1000)
        events.request_success.fire(request_type="POST", name=endpoint, response_time=total_time, response_length=0)

        logger.info("Response time %s ms", total_time)

        return response


class RepeatingHttpClient(RepeatingClient):
    def send_impl(self, url, data) -> (object, bool):
        logger = logging.getLogger('RepeatingHttpClient')

        logger.info("POST")
        response = requests.post(url, json=data)
        logger.info("Response: %s", response.status_code)

        successfully_sent = 200 <= response.status_code < 300

        return response, successfully_sent


class RepeatingHttpLocust(Locust):
    def __init__(self, *args, **kwargs):
        super(RepeatingHttpLocust, self).__init__(*args, **kwargs)
        self.client = RepeatingHttpClient(self.host)


class AlarmDevice(RepeatingHttpLocust):
    task_set = AlarmDeviceBehavior
    wait_time = between(1, 1)
