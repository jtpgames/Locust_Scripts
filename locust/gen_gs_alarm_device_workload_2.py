#!/usr/bin/env python
import random
import os
import gevent
import logging

from locust import task, between, User, constant, events
from locust.env import Environment

from common.common_locust import RepeatingHttpxClient

import random
from datetime import datetime, timedelta, timezone

class RepeatingHttpLocust(User):
    abstract = True

    def __init__(self, *args, **kwargs):
        super(RepeatingHttpLocust, self).__init__(*args, **kwargs)
        self.client = RepeatingHttpxClient(self.host, self)


# initialize the random seed value to get reproducible random sequences
random.seed(42)

EXPERIMENT_RUNTIME = timedelta(minutes=float(os.environ.get('EXPERIMENT_RUNTIME', 10)))

locust_environment: Environment = None
experiment_starttime: datetime = datetime.now()

@events.init.add_listener
def on_test_start(environment: Environment, **kwargs):
    environment.stop_timeout = 10

    global locust_environment
    locust_environment = environment

    global experiment_starttime
    experiment_starttime = datetime.now()
    LOGGER = logging.getLogger('AlarmDevice')
    LOGGER.info(f"Experiment started @{experiment_starttime} to run for {EXPERIMENT_RUNTIME}")


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
    
    currently_executing_users = 0
    LOGGER = logging.getLogger('AlarmDevice')

    def __init__(self, *args, **kwargs):
        super(AlarmDevice, self).__init__(*args, **kwargs)
        self.random_phone = random.choice(self.available_phone_numbers_for_devices)
        AlarmDevice.currently_executing_users += 1
    
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

        now = datetime.now()
        time_since_experiment = now - experiment_starttime
        if time_since_experiment > EXPERIMENT_RUNTIME:
            AlarmDevice.LOGGER.info(f"Stopping user")
            if AlarmDevice.currently_executing_users == 1:
                AlarmDevice.LOGGER.info(f"Stopping Runner")
                gevent.spawn_later(2, locust_environment.runner.quit)
            self.stop()
            AlarmDevice.currently_executing_users -= 1


    @task(1)
    def call_with_reject(self):
        self.send_simple_alarm()
