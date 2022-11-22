#!/usr/bin/env python

# This file tests the TeaStore, see https://github.com/DescartesResearch/TeaStore.
# It is inspired by
# https://github.com/DescartesResearch/teastore/blob/master/examples/httploadgenerator/teastore_browse.lua.

import logging
import random
import re
from re import search
from datetime import timedelta, datetime
from glob import glob

import requests
from locust import between, task, HttpUser, events, LoadTestShape, constant
from locust.contrib.fasthttp import FastHttpUser
from locust.env import Environment


@events.test_start.add_listener
def on_test_start(environment: Environment, **kwargs):
    logs_endpoint = environment.host.replace(":8080", ":8081/logs/reset")

    logging.info("Resetting teastore logs")
    response = requests.get(logs_endpoint)
    logging.info(response.status_code)


@events.request_success.add_listener
def my_success_handler(request_type, name, response_time, response_length, **kw):
    logging.info("Response time %s ms", response_time)


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
        for file_path in sorted(glob("GS Production Workload/All_requests_per_*.log")):
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


class TeaStore(FastHttpUser):
    # wait_time = between(1, 90)
    wait_time = constant(1)

    _global_user_count = 0

    _user = "user"
    _pw = "password"
    _productviewcount = 30

    _known_product_ids = []
    _dup = {}
    _products_in_cart = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prefix = self.host + "/tools.descartes.teastore.webui/"

        self._user += str(TeaStore._global_user_count)
        TeaStore._global_user_count += 1

        print(self._user)

    def _login(self):
        endpoint = self._prefix + f"loginAction?username={self._user}&password={self._pw}"

        self.client.post(endpoint, name="/login")
        self.browse_tea_categories()

    def _logout(self):
        endpoint = self._prefix + "loginAction?logout="

        self.client.post(endpoint, name="/logout")

    @task(5)
    def browse_tea_categories(self):
        random_category = random.randint(2, 6)
        endpoint = self._prefix + f"category?page=1&category={random_category}&number={self._productviewcount}"

        r = self.client.get(endpoint, name="/tea_category")

        p = re.compile(r"href=.*product.*?id=\d+. ><img")

        product_links = p.findall(r.text)

        for link in product_links:
            product_id = re.search(r"(?<=id=)\d+", link).group(0)
            if product_id not in self._dup:
                self._known_product_ids.append(int(product_id))
                self._dup[product_id] = len(self._known_product_ids) - 1

    @task(5)
    def open_product(self):
        if len(self._known_product_ids) == 0:
            return

        random_product_id = random.randint(
            min(self._known_product_ids),
            max(self._known_product_ids)
        )

        endpoint = self._prefix + f"product?id={random_product_id}"

        self.client.get(endpoint, name="/product")

    @task(3)
    def add_product_to_cart(self):
        if len(self._known_product_ids) == 0:
            return

        random_product_id = random.randint(
            min(self._known_product_ids),
            max(self._known_product_ids)
        )

        endpoint = self._prefix + f"cartAction?addToCart=&productid={random_product_id}"

        self.client.post(endpoint, name="/add_to_cart")
        self._products_in_cart.append(random_product_id)

    @task(3)
    def remove_product_from_cart(self):
        if len(self._products_in_cart) == 0:
            return

        random_idx = random.randrange(0, len(self._products_in_cart))
        random_product_id = self._products_in_cart.pop(random_idx)

        endpoint = self._prefix + f"cartAction?removeProduct_{random_product_id}=&productid={random_product_id}"

        self.client.post(endpoint, name="/remove_from_cart")

    @task
    def open_user_profile(self):
        endpoint = self._prefix + "profile"

        self.client.get(endpoint, name="/profile")

    @task(2)
    def open_user_cart(self):
        endpoint = self._prefix + "cart"

        self.client.get(endpoint, name="/cart")

    def on_start(self):
        self._login()

    def on_stop(self):
        self._logout()
