#!/usr/bin/env python
import json
import random

from locust import task, between, User

from common.common_locust import RepeatingHttpClient


class RepeatingHttpLocust(User):
    abstract = True

    def __init__(self, *args, **kwargs):
        super(RepeatingHttpLocust, self).__init__(*args, **kwargs)
        self.client = RepeatingHttpClient(self.host)


# initialize the random seed value to get reproducible random sequences
random.seed(42)


class AlarmDevice(RepeatingHttpLocust):
    """
    Simulates an alarm device, i.e., sends periodic alarm and repeats the transmission until it was successful.
    """

    wait_time = between(1, 1)

    def send_alarm(self):
        json_msg = {
            'id': "070010",
            'body': "alarm"
        }

        json_string = json.dumps(json_msg)

        response = self.client.send("/ID_REQ_KC_STORE7D3BPACKET", json_msg)

    @task(1)
    def fake_alarm(self):
        self.send_alarm()
