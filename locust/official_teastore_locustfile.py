#!/usr/bin/env python

# This file tests the TeaStore, see https://github.com/DescartesResearch/TeaStore.
# It is a modified version of
# https://github.com/DescartesResearch/TeaStore/blob/master/examples/locust/locustfile.py.

import logging
from datetime import timedelta
from random import randint, choice

import csv
from locust import HttpUser, task, LoadTestShape, constant, events
from locust.env import Environment

import requests

# logging
logging.getLogger().setLevel(logging.INFO)

locust_environment: Environment = None


@events.test_start.add_listener
def on_test_start(environment: Environment, **kwargs):
    logs_endpoint = environment.host.replace(":8080", ":8081/logs/reset")

    logging.info("Resetting teastore logs")
    response = requests.get(logs_endpoint)
    logging.info(response.status_code)

    global locust_environment
    locust_environment = environment


@events.request_success.add_listener
def my_success_handler(request_type, name, response_time, response_length, **kw):
    logging.info("Response time %s ms", response_time)


@events.request_failure.add_listener
def my_failure_handler(request_type, name, response_time, response_length, exception):
    logging.warning(f"{request_type} {name} failed", response_time)


class StagesShape(LoadTestShape):
    """
    A simple load test shape class that has different user and spawn_rate at
    different stages.
    Keyword arguments:
        stages -- A list of dicts, each representing a stage with the following keys:
            duration -- When this many seconds pass the test is advanced to the next stage
            users -- Total user count
            spawn_rate -- Number of users to start/stop per second
    """

    stages = []

    def __init__(self):
        super().__init__()

        #with open("locust/increasingLowIntensity.csv") as intensityFile:
        #with open("locust/increasingMedIntensity.csv") as intensityFile:
        with open("locust/increasingHighIntensity.csv") as intensityFile:
            reader = csv.DictReader(intensityFile, ['time', 'rps'])
            for row in reader:
                time = float(row['time'])
                rps = round(float(row['rps']))

                if rps == 0:
                    rps = 1
                print((time, rps))
                self.stages.append({"duration": time, "users": rps, "spawn_rate": rps})

    def tick(self):
        run_time = self.get_run_time()
        run_time *= 2

        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data

        locust_environment.runner.quit()
        return None


class UserBehavior(HttpUser):
    wait_time = constant(1)

    _global_user_count = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prefix = self.host + "/tools.descartes.teastore.webui"

        self._user = "user" + str(UserBehavior._global_user_count)
        UserBehavior._global_user_count += 1

        # print(self._user)

    @task
    def load(self) -> None:
        """
        Simulates user behaviour.
        :return: None
        """

        try:
            logging.info(f"Starting user {self._user}")
            self.visit_home()
            self.wait()
            self.login()
            self.wait()
            self.browse()
            self.wait()
            # 50/50 chance to buy
            choice_buy = choice([True, False])
            if choice_buy:
                self.buy()
                self.wait()
            self.visit_profile()
            self.wait()
            self.logout()
            logging.info("Completed user.")
        except requests.exceptions.ConnectionError as e:
            logging.error(f"{e.request.url, str(e)}")

    def visit_home(self) -> None:
        """
        Visits the landing page.
        :return: None
        """
        # load landing page
        res = self.client.get(self._prefix + '/')
        if res.ok:
            logging.info("Loaded landing page.")
        else:
            logging.error(f"Could not load landing page: {res.status_code}")

    def login(self) -> None:
        """
        User login with a distinct userid chosen in the constructor.
        :return: categories
        """
        # load login page
        res = self.client.get(self._prefix + '/login')
        if res.ok:
            logging.info("Loaded login page.")
        else:
            logging.error(f"Could not load login page: {res.status_code}")

        # login user
        user = self._user
        login_request = self.client.post(self._prefix + "/loginAction", params={"username": user, "password": "password"})
        if login_request.ok:
            logging.info(f"Login with username: {user}")
        else:
            logging.error(
                f"Could not login with username: {user} - status: {login_request.status_code}")

    def browse(self) -> None:
        """
        Simulates random browsing behaviour.
        :return: None
        """
        # execute browsing action randomly up to 5 times
        for i in range(1, randint(2, 5)):
            # browses random category and page
            category_id = randint(2, 6)
            page = randint(1, 5)
            category_request = self.client.get(self._prefix + "/category", params={"page": page, "category": category_id})
            if category_request.ok:
                logging.info(f"Visited category {category_id} on page 1")
                # browses random product
                product_id = randint(7, 506)
                product_request = self.client.get(self._prefix + "/product", params={"id": product_id})
                if product_request.ok:
                    logging.info(f"Visited product with id {product_id}.")
                    cart_request = self.client.post(self._prefix + "/cartAction", params={"addToCart": "", "productid": product_id})
                    if cart_request.ok:
                        logging.info(f"Added product {product_id} to cart.")
                    else:
                        logging.error(
                            f"Could not put product {product_id} in cart - status {cart_request.status_code}")
                else:
                    logging.error(
                        f"Could not visit product {product_id} - status {product_request.status_code}")
            else:
                logging.error(
                    f"Could not visit category {category_id} on page 1 - status {category_request.status_code}")

    def buy(self) -> None:
        """
        Simulates to buy products in the cart with sample user data.
        :return: None
        """
        # sample user data
        user_data = {
            "firstname": "User",
            "lastname": "User",
            "adress1": "Road",
            "adress2": "City",
            "cardtype": "volvo",
            "cardnumber": "314159265359",
            "expirydate": "12/2050",
            "confirm": "Confirm"
        }
        buy_request = self.client.post(self._prefix + "/cartAction", params=user_data)
        if buy_request.ok:
            logging.info(f"Bought products.")
        else:
            logging.error("Could not buy products.")

    def visit_profile(self) -> None:
        """
        Visits user profile.
        :return: None
        """
        profile_request = self.client.get(self._prefix + "/profile")
        if profile_request.ok:
            logging.info("Visited profile page.")
        else:
            logging.error("Could not visit profile page.")

    def logout(self) -> None:
        """
        User logout.
        :return: None
        """
        logout_request = self.client.post(self._prefix + "/loginAction", params={"logout": ""})
        if logout_request.ok:
            logging.info("Successful logout.")
        else:
            logging.error(f"Could not log out - status: {logout_request.status_code}")