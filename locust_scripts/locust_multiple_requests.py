#!/usr/bin/env python
import json

from locust import task, between, User

from common.common_locust import RepeatingHttpClient


class RepeatingHttpLocust(User):
    abstract = True

    def __init__(self, *args, **kwargs):
        super(RepeatingHttpLocust, self).__init__(*args, **kwargs)
        self.client = RepeatingHttpClient(self.host)


class LoadGenerator(RepeatingHttpLocust):
    """
    Generates the workload that occurs independently of alarm devices.
    This workload consists of requests that are executed by other components of the legacy system.
    """
    wait_time = between(1, 1)

    def get_server_time(self):
        response = self.client.send("/CMD_GETSERVERTIMESTR")

    def get_status(self):
        response = self.client.send("/KC_GETQUITTIERTEPAKETE")

    def update_status(self):
        json_msg = {
            'id': "070010",
        }

        json_string = json.dumps(json_msg)

        response = self.client.send("/KC_DELETEQUITTIERTEPAKETE", json_string)

    @task(5)
    def server_time(self):
        self.get_server_time()

    @task(1)
    def alarms_status(self):
        self.get_status()

    @task(1)
    def update_alarms_status(self):
        self.update_status()


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

        response = self.client.send("/KC_STORE7D3BPACKET", json_msg)

    @task(10)
    def fake_alarm(self):
        self.send_alarm()
