#!/usr/bin/env python
import random

from locust import task, between, User, constant

from common.common_locust import RepeatingHttpxClient

from locust import User, task, between

import random
from datetime import datetime, timezone

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
    wait_time = between(20, 90)
    # wait_time = constant(1)
    
    available_phone_numbers_for_devices = ["015142611148", "01754937448", "016590943333"]
    available_branch_numbers_for_devices = list(range(2001, 2011)) + list(range(2012, 2017))
    
    def __init__(self, *args, **kwargs):
        super(AlarmDevice, self).__init__(*args, **kwargs)
        self.random_phone = random.choice(self.available_phone_numbers_for_devices)
    
    def construct_call_with_reject_request_object(self):
        random_branch = random.choice(self.available_branch_numbers_for_devices)
    
        now = datetime.now(timezone.utc).isoformat()
    
        json_obj = {
            'phone': self.random_phone,
            'branch': str(random_branch),
            'headnumber': "8023",
            'triggertime': now
        }
        
        return json_obj
    

    def send_simple_alarm(self):
        json_obj = self.construct_call_with_reject_request_object()

        response = self.client.send("/api/v1/simple", json_obj)

    @task(1)
    def call_with_reject(self):
        self.send_simple_alarm()
