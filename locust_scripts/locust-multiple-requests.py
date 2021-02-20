#!/usr/bin/env python
import json

from locust import task, between, User

from common.common_locust import RepeatingHttpClient


class RepeatingHttpLocust(User):
    abstract = True

    def __init__(self, *args, **kwargs):
        super(RepeatingHttpLocust, self).__init__(*args, **kwargs)
        self.client = RepeatingHttpClient(self.host)


class AlarmDevice(RepeatingHttpLocust):
    wait_time = between(1, 1)

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
