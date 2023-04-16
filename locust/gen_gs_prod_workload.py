#!/usr/bin/env python
import random
import re
from datetime import datetime
from glob import glob
from re import search

from locust import task, constant, LoadTestShape
from locust.contrib.fasthttp import FastHttpUser


def contains_timestamp_with_ms(line: str):
    return search(r"\s*\d*-\d*-\d*\s\d*:\d*:\d*\.\d*", line) is not None


def get_timestamp_from_string(line: str):
    return search(r"\s*\d*-\d*-\d*\s\d*:\d*:\d*\.?\d*", line).group().strip()


def get_timestamp_from_line(line: str) -> datetime:
    if contains_timestamp_with_ms(line):
        format_string = '%Y-%m-%d %H:%M:%S.%f'
    else:
        format_string = '%Y-%m-%d %H:%M:%S'

    return datetime.strptime(
        get_timestamp_from_string(line),
        format_string
    )


class RealWorkloadShape(LoadTestShape):
    def __init__(self):
        super().__init__()

        self._max_requests_per_hour_within_the_workload = 0
        self._max_requests_per_second_within_the_workload = 0

        self._workload_pattern = dict()

        self._number_of_days_recorded = 0
        for file_path in sorted(glob("GS Production Workload/Requests_without_alarms_*.log")):
            print(file_path)
            with open(file_path) as logfile:
                for line in logfile:
                    requests_per_second = re.search('(?<=RPS:\\s)\\d*', line)
                    if requests_per_second is not None:
                        requests_per_second = int(requests_per_second.group())
                        self._max_requests_per_second_within_the_workload = max(
                            self._max_requests_per_second_within_the_workload,
                            requests_per_second
                        )

                    requests_per_hour = re.search('(?<=RPH:\\s)\\d*', line)
                    if requests_per_hour is None:
                        continue

                    time_stamp = get_timestamp_from_line(line)

                    requests_per_hour = int(requests_per_hour.group())

                    self._workload_pattern[self._number_of_days_recorded * 24 + time_stamp.hour] = requests_per_hour
            self._number_of_days_recorded += 1

        self._max_requests_per_hour_within_the_workload = max(self._workload_pattern.values())
        print(f"Requests per hour to send: {self._max_requests_per_hour_within_the_workload}")
        print(f"Requests per sec to send: {self._max_requests_per_second_within_the_workload}")

    def tick(self):
        avg_requests_per_second = int(self._max_requests_per_second_within_the_workload)
        return avg_requests_per_second, avg_requests_per_second

        # run_time = self.get_run_time()
        #
        # run_time_in_hours = int(run_time / 3600)
        # run_time_in_days = int(run_time_in_hours / 24)
        #
        # if run_time_in_days >= self._number_of_days_recorded:
        #     return None
        #
        # avg_requests_per_second = int(self._workload_pattern[run_time_in_hours] / 3600)
        #
        # # Because every user sends one request per second, we need avg_requests_per_second users
        # return avg_requests_per_second, avg_requests_per_second


# class RepeatingHttpLocust(User):
#     abstract = True
#
#     def __init__(self, *args, **kwargs):
#         super(RepeatingHttpLocust, self).__init__(*args, **kwargs)
#         self.client = RepeatingHttpClient(self.host, self)


requests = set()

with open("GS Production Workload/All_Request_Names.log") as logfile:
    for line in logfile:
        if "ID_REQ_KC_STORE7D3BPACKET" in line:
            continue

        requests.add(line.rstrip())

requests = tuple(requests)


class LoadGenerator(FastHttpUser):
    """
    Generates the workload that occurs independently of alarm devices.
    This workload consists of requests that are executed by other components of the legacy system.
    """
    wait_time = constant(1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # initialize the random seed value to get reproducible random sequences
        random.seed(42)

    def do_request(self):
        cmd_to_use = random.choice(requests)

        self.client.post(f"/{cmd_to_use}")

    @task(1)
    def execute_request(self):
        self.do_request()
