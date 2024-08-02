#!/usr/bin/env python
import json
import random

from locust import task, between, User, constant

from common.common_locust import RepeatingHttpClient, RepeatingHttpxClient


class RepeatingHttpLocust(User):
    abstract = True

    def __init__(self, *args, **kwargs):
        super(RepeatingHttpLocust, self).__init__(*args, **kwargs)
        self.client = RepeatingHttpxClient(self.host, self)


# initialize the random seed value to get reproducible random sequences
random.seed(42)


class AlarmDevice(RepeatingHttpLocust):
    """
    Simulates an alarm device, i.e., sends periodic alarm and repeats the transmission until it was successful.
    """

    # Wait time between 20 sec (SP6 devices) and 90 sec (DP4 devices) according to EN 50136-1
    # wait_time = between(20, 90)
    # Use most demanding frequency of the EN 50136-1 standard
    wait_time = constant(20)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_first_alarm = True

    def send_alarm(self):
        if self.is_first_alarm:
            # wait before sending first alarm
            self.wait()
            self.is_first_alarm = False

        json_msg = {
            'id': "070010",
            'body': "0123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789"
        }

        json_string = json.dumps(json_msg)

        response = self.client.send("/ID_REQ_KC_STORE7D3BPACKET", json_msg)

    @task(1)
    def fake_alarm(self):
        self.send_alarm()
