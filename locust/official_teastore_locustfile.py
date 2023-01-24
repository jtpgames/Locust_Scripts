#!/usr/bin/env python

# This file tests the TeaStore, see https://github.com/DescartesResearch/TeaStore.
# It is a modified version of
# https://github.com/DescartesResearch/TeaStore/blob/master/examples/locust/locustfile.py.
# The modifications include:
# * A loadtest shape that, depending on a workload defined in a .csv file,
#   steadily increases the load and stops the test. This loadtest shape tries to
#   mimic the loadtest of the
#   teastore developers: https://github.com/DescartesResearch/TeaStore/tree/master/examples/httploadgenerator
# * Reset the logfiles of teastore before starting the test.
# * Additional logging for better insight and postprocessing of the measured response times.
# * Consistent randomness by working with fixed seeds.
# * Removed random user logins
# * Minor refactoring and quality of life improvements like sending a unique request-id.

import logging
from datetime import timedelta
from random import seed, Random

import csv
from uuid import uuid1

import gevent
from locust import HttpUser, task, LoadTestShape, constant, events
from locust.env import Environment
from locust.contrib.fasthttp import FastHttpUser

import requests

WITH_WARMUP_PHASE = True

# logging
logging.getLogger().setLevel(logging.INFO)

# noinspection PyTypeChecker
locust_environment: Environment = None

requests_counter = 0
buy_counter = 0

stop_executing_users = False


def reset_teastore_logs(environment: Environment):
    logs_endpoint = environment.host.replace(":8080", ":8081")

    logging.info("Resetting teastore logs")
    response = requests.get(logs_endpoint + "/logs/reset")
    logging.info(f"{response.status_code} - {response.text}")


@events.test_start.add_listener
def on_test_start(environment: Environment, **kwargs):
    reset_teastore_logs(environment)

    environment.stop_timeout = 10

    global locust_environment
    locust_environment = environment


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kwargs):
    logging.info(f"Test stopped with {requests_counter} total requests send and {buy_counter} buy requests.")


@events.request_success.add_listener
def my_success_handler(request_type, name, response_time, response_length, **kw):
    logging.info("Response time %s ms", response_time)


@events.request_failure.add_listener
def my_failure_handler(request_type, name, response_time, response_length, exception):
    logging.error(f"{request_type} {name} failed", response_time)


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

    _is_tick_disabled = False
    _is_warming_up = WITH_WARMUP_PHASE
    _is_preparing_for_regular_load = False
    _last_tick_data = None

    _stages = []

    def __init__(self):
        super().__init__()

        with open("locust/increasingLowIntensity.csv") as intensityFile:
        # with open("locust/increasingMedIntensity.csv") as intensityFile:
        # with open("locust/increasingHighIntensity.csv") as intensityFile:
            reader = csv.DictReader(intensityFile, ['time', 'rps'])
            for row in reader:
                time = float(row['time'])
                rps = round(float(row['rps']))

                if rps == 0:
                    rps = 1
                print((time, rps))
                self._stages.append({"duration": time, "users": rps, "spawn_rate": 100})

    def start_regular_load_profile(self):
        global requests_counter, buy_counter

        logging.info(f"Warm-Up finished after sending {requests_counter} requests. Regular load profile starts.")

        locust_environment.runner.stats.reset_all()
        self.reset_time()
        UserBehavior._currently_executing_users = 0
        UserBehavior._global_user_count = 0

        requests_counter = 0
        buy_counter = 0

        self._is_warming_up = False

    def tick(self):
        if self._is_tick_disabled:
            return self._last_tick_data

        run_time = self.get_run_time()

        if self._is_warming_up:
            if run_time < 5 * 60:
                return 50, 50
            else:
                if not self._is_preparing_for_regular_load:
                    gevent.spawn_later(5, lambda: reset_teastore_logs(locust_environment))
                    gevent.spawn_later(10, self.start_regular_load_profile)
                self._is_preparing_for_regular_load = True
                return 0, 50
        else:
            for stage in self._stages:
                if run_time < stage["duration"]:
                    tick_data = (stage["users"], stage["spawn_rate"])
                    self._last_tick_data = tick_data
                    return tick_data

            global stop_executing_users
            stop_executing_users = True
            logging.info("Stopping loadtest")

            self._is_tick_disabled = True
            return self._last_tick_data


# initialize the random seed value to produce consistent random sequences in every load test.
seed(42)


class UserBehavior(FastHttpUser):
    wait_time = constant(1)

    _global_user_count = 0
    _currently_executing_users = 0

    def _get(self, url, params=None):
        request_id = uuid1().int

        resp = self.client.get(url, params=params, headers={"Request-Id": str(request_id)})
        global requests_counter
        requests_counter += 1
        self.wait()
        return resp

    def _post(self, url, params=None, with_wait=True):
        request_id = uuid1().int

        resp = self.client.post(url, params=params, headers={"Request-Id": str(request_id)})
        global requests_counter
        requests_counter += 1
        if with_wait:
            self.wait()
        return resp

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prefix = self.host + "/tools.descartes.teastore.webui"

        self._user_id = UserBehavior._global_user_count
        self._user = "user" + str(self._user_id)
        UserBehavior._global_user_count += 1
        UserBehavior._currently_executing_users += 1

        # Produce consistent random sequences across subsequent load tests.
        self._random = Random()
        self._random.seed(self._user_id)

        self._is_logged_in = False

    def on_stop(self):
        if self._is_logged_in:
            try:
                self.logout(with_wait=False)
            except requests.exceptions.ConnectionError as e:
                logging.error(f"{e.request.url, str(e)}")

    @task
    def load(self) -> None:
        """
        Simulates user behaviour.
        :return: None
        """

        try:
            logging.debug(f"Starting user {self._user}")
            self.visit_home()
            self.login()
            self.browse()
            # 50/50 chance to buy
            choice_buy = self._random.choice([True, False])
            logging.debug(f"{self._user}: choice: {choice_buy}")
            if choice_buy:
                self.buy()
            self.visit_profile()
            self.logout()
            logging.debug(f"Completed user {self._user}.")
        except requests.exceptions.ConnectionError as e:
            logging.error(f"{e.request.url, str(e)}")

        if stop_executing_users:
            if UserBehavior._currently_executing_users == 1:
                gevent.spawn_later(2, locust_environment.runner.quit)
            self.stop()
            UserBehavior._currently_executing_users -= 1
            return

    def visit_home(self) -> None:
        """
        Visits the landing page.
        :return: None
        """
        # load landing page
        res = self._get(self._prefix + '/')
        if res.status_code == 200 or res.ok:
            logging.info("Loaded landing page.")
        else:
            logging.error(f"Could not load landing page: {res.status_code}")

    def login(self) -> None:
        """
        User login with a distinct userid chosen in the constructor.
        :return: categories
        """
        # load login page
        res = self._get(self._prefix + '/login')
        if res.status_code == 200 or res.ok:
            logging.info("Loaded login page.")
        else:
            logging.error(f"Could not load login page: {res.status_code}")

        # login user
        user = self._user
        url = f"/loginAction?username={user}&password=password"
        login_request = self._post(self._prefix + url)
        if login_request.status_code == 200 or login_request.ok:
            logging.info(f"Login with username: {user}")
            self._is_logged_in = True
        else:
            logging.error(
                f"Could not login with username: {user} - status: {login_request.status_code}")

    def browse(self) -> None:
        """
        Simulates random browsing behaviour.
        :return: None
        """
        # execute browsing action randomly up to 5 times
        for i in range(1, self._random.randint(2, 5)):
            logging.debug(f"{self._user}: {i}")
            # browses random category and page
            category_id = self._random.randint(2, 6)
            logging.debug(f"{self._user}: {category_id}")
            page = self._random.randint(1, 5)
            logging.debug(f"{self._user}: {page}")
            url = f"/category?page={page}&category={category_id}"
            category_request = self._get(self._prefix + url)
            # category_request = self._get(self._prefix + "/category", params={"page": page, "category": category_id})
            if category_request.status_code == 200 or category_request.ok:
                logging.info(f"Visited category {category_id} on page 1")
                # browses random product
                product_id = self._random.randint(7, 506)
                url = f"/product?id={product_id}"
                product_request = self._get(self._prefix + url)
                # product_request = self._get(self._prefix + "/product", params={"id": product_id})
                if product_request.status_code == 200 or product_request.ok:
                    logging.info(f"Visited product with id {product_id}.")
                    url = f"/cartAction?addToCart=&productid={product_id}"
                    cart_request = self._post(self._prefix + url)
                    # cart_request = self._post(self._prefix + "/cartAction", params={"addToCart": "", "productid": product_id})
                    if cart_request.status_code == 200 or cart_request.ok:
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
        url = f"/cartAction" \
              f"?firstname=User&lastname=User" \
              f"&adress1=Road&adress2=City" \
              f"&cardtype=volvo&cardnumber&314159265359&expirydate=12/2050" \
              f"&confirm=Confirm"
        buy_request = self._post(self._prefix + url)
        # buy_request = self._post(self._prefix + "/cartAction", params=user_data)
        if buy_request.status_code == 200 or buy_request.ok:
            logging.info(f"Bought products.")
        else:
            logging.error("Could not buy products.")
        global buy_counter
        buy_counter += 1

    def visit_profile(self) -> None:
        """
        Visits user profile.
        :return: None
        """
        profile_request = self._get(self._prefix + "/profile")
        if profile_request.status_code == 200 or profile_request.ok:
            logging.info("Visited profile page.")
        else:
            logging.error("Could not visit profile page.")

    def logout(self, with_wait=True) -> None:
        """
        User logout.
        :return: None
        """
        url = f"/loginAction?logout="
        logout_request = self._post(self._prefix + url, with_wait=with_wait)
        # logout_request = self._post(self._prefix + "/loginAction", params={"logout": ""})
        if logout_request.status_code == 200 or logout_request.ok:
            logging.info("Successful logout.")
            self._is_logged_in = False
        else:
            logging.error(f"Could not log out - status: {logout_request.status_code}")
