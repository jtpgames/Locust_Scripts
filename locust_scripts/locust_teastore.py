#!/usr/bin/env python

# This file tests the TeaStore, see https://github.com/DescartesResearch/TeaStore.
# It is inspired by
# https://github.com/DescartesResearch/teastore/blob/master/examples/httploadgenerator/teastore_browse.lua.

import logging
import random
import re
from datetime import timedelta

import requests
from locust import between, task, HttpUser, events, LoadTestShape
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


class StagesShape(LoadTestShape):
    """
    A simply load test shape class that has different user and spawn_rate at
    different stages.
    Keyword arguments:
        stages -- A list of dicts, each representing a stage with the following keys:
            duration -- When this many seconds pass the test is advanced to the next stage
            users -- Total user count
            spawn_rate -- Number of users to start/stop per second
            stop -- A boolean that can stop that test at a specific stage
    """

    stages = [
        {"duration": timedelta(seconds=6).total_seconds(), "users": 1, "spawn_rate": 1},
        {"duration": timedelta(seconds=8).total_seconds(), "users": 10, "spawn_rate": 10},
        {"duration": timedelta(seconds=16).total_seconds(), "users": 50, "spawn_rate": 10},
        {"duration": timedelta(seconds=24).total_seconds(), "users": 20, "spawn_rate": 10},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data

        self.reset_time()
        last_stage = self.stages[len(self.stages) - 1]
        return last_stage["users"], last_stage["spawn_rate"]


# class TeaStore(HttpUser):
class TeaStore(FastHttpUser):
    wait_time = between(1, 1)

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

        endpoint = self._prefix + f"cartAction?removeProduct_{random_product_id}"

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
