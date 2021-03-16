#!/usr/bin/env python

# This file tests the TeaStore, see https://github.com/DescartesResearch/TeaStore.
# It is inspired by
# https://github.com/DescartesResearch/teastore/blob/master/examples/httploadgenerator/teastore_browse.lua.

import logging
import random
import re

import requests
from locust import between, task, HttpUser, events
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


class TeaStore(HttpUser):
    wait_time = between(1, 1)

    _user = "user"
    _pw = "password"
    _productviewcount = 30

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prefix = self.host + "/tools.descartes.teastore.webui/"

    def _login(self):
        endpoint = self._prefix + f"loginAction?username={self._user}&password={self._pw}"

        response = self.client.post(endpoint, name="/login")

    def _logout(self):
        endpoint = self._prefix + "loginAction?logout="

        response = self.client.post(endpoint, name="/logout")

    @task(3)
    def browse_tea_categories(self):
        random_category = random.randint(2, 6)
        endpoint = self._prefix + f"category?page=1&category={random_category}&number={self._productviewcount}"

        r = self.client.get(endpoint, name="/tea_category")

        p = re.compile('href=.*product.*?id=\\d+. ><img')

        product_links = p.findall(r.text)

        for link in product_links:
            product_id = re.search('id=\\d+', link).group(0)
            print(product_id)

    @task
    def open_user_profile(self):
        endpoint = self._prefix + "profile"

        self.client.get(endpoint, name="/profile")

    @task
    def open_user_cart(self):
        endpoint = self._prefix + "cart"

        self.client.get(endpoint, name="/cart")

    def on_start(self):
        self._login()

    def on_stop(self):
        self._logout()
