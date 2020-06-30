#!/usr/bin/env python
# Simulates an ARS with workloads measured in a productive environment.
# Based on https://gist.github.com/huyng/814831 Written by Nathan Hamiel (2010)
import os
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from optparse import OptionParser
from random import random, seed
from time import sleep
from apscheduler.schedulers.background import BackgroundScheduler

from datetime import datetime, timedelta
from stopwatch import Stopwatch

import logging

fh = logging.FileHandler('ARS_simulation.log')
fh.setLevel(logging.DEBUG)

logging.basicConfig(format="%(asctime)s %(message)s",
                    level=os.environ.get("LOGLEVEL", "INFO"),
                    handlers=[fh])

logger = logging.getLogger('Audit')

scheduler = BackgroundScheduler()
time_of_last_fault = datetime.now()
time_of_recovery = datetime.now()
chosen_fault_time = 0
_is_faulted = False


def between(min, max):
    return min + random() * (max - min)


def recover():

    # TODO Implement "operator reaction" time

    # TODO Implement "restart" time

    global _is_faulted
    _is_faulted = False

    global time_of_recovery
    time_of_recovery = datetime.now()

    logger.info("ARS recovered @%s", time_of_recovery)


def is_faulted():
    return _is_faulted


def inject_a_fault_every_s_seconds(s):
    scheduler.add_job(simulate_fault, 'interval', seconds=s)


def inject_three_faults_in_a_row():
    due_date1 = datetime.now() + timedelta(0, minutes=5)
    due_date2 = due_date1 + timedelta(0, 60)
    due_date3 = due_date2 + timedelta(0, 60)

    scheduler.add_job(simulate_fault, 'date', run_date=due_date1)
    scheduler.add_job(simulate_fault, 'date', run_date=due_date2)
    scheduler.add_job(simulate_fault, 'date', run_date=due_date3)
    scheduler.add_job(inject_three_faults_in_a_row, 'date', run_date=due_date3)


def simulate_fault():
    """
    simulate a fault:

    * this method causes the function `is_faulted` to return true for `chosen_fault_time` seconds.
    * `chosen_fault_time` is set using the ideal time the real-world fault management mechanism requires.
    """

    # this is the ideal time,
    # the fault management needs to perform a recovery operation
    # when a fault occurs.
    # These are the expected min and max times based on the real-world fault detection mechanism.
    # For every ARS running in the system, we have additional 2 seconds.
    this_ARS_number_in_the_server_list = 2
    expected_fault_time_min = 26
    expected_fault_time_max = 34

    global chosen_fault_time
    chosen_fault_time = between(expected_fault_time_min, expected_fault_time_max)

    logger.debug("1. chosen_fault_time: %i", chosen_fault_time)

    chosen_fault_time += 2*(this_ARS_number_in_the_server_list-1)

    logger.debug("2. chosen_fault_time: %i", chosen_fault_time)

    global time_of_last_fault
    time_of_last_fault = datetime.now()

    logger.info("ARS faulted @%s", time_of_last_fault)

    global _is_faulted
    _is_faulted = True

    due_date = datetime.now() + timedelta(0, chosen_fault_time)
    scheduler.add_job(recover, 'date', run_date=due_date)


def simulate_minimal_workload_of_staging_environment():
    # min time measured with Locust in the staging environment
    min_processing_time = 2

    wait_time = min_processing_time

    print("Waiting for {}".format(wait_time))

    sleep(wait_time)

    return True


def simulate_workload_of_production_system():
    """
    Simulate workload based on real processing times measured
    in the production environment.
    """

    print("Simulating workload")

    # -- min and max times measured from 16561 requests --
    min_processing_time = 6

    # this very high time actually happens at night, when other processes,
    # like the database backups database are executed
    #max_processing_time = 2799
    max_processing_time = 10  # for demonstration purposes
    # --

    # for simplicity we just take a random distribution
    # that is not representative for the production system behavior
    random_processing_time = between(min_processing_time, max_processing_time)

    print("Waiting for {}".format(random_processing_time))

    sleep(random_processing_time)

    return True


class RequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        request_path = self.path

        print("\n----- Request Start ----->\n")
        print("Request path:", request_path)
        print("Request headers:", self.headers)
        print("<----- Request End -----\n")

        self.send_response(200)
        self.send_header("Set-Cookie", "foo=bar")
        self.end_headers()

    def do_POST(self):

        request_path = self.path

        print("\n----- Request Start ----->\n")
        print("Request path:", request_path)

        request_headers = self.headers
        content_length = request_headers.get('Content-Length')
        length = int(content_length) if content_length else 0

        print("Content Length:", length)
        print("Request headers:", request_headers)
        print("Request payload:", self.rfile.read(length))

        if is_faulted():
            print("System faulted for {} s".format(chosen_fault_time))
            is_successful = False
        else:
            stopwatch = Stopwatch()
            is_successful = simulate_minimal_workload_of_staging_environment()
            #is_successful = simulate_minimal_workload_of_staging_system()
            stopwatch.stop()
            logger.info("Processing time: %s", stopwatch)

        print("<----- Request End -----\n")

        self.send_response(200 if is_successful else 500)
        self.end_headers()

    do_PUT = do_POST
    do_DELETE = do_GET


def main():
    scheduler.start()

    #inject_a_fault_every_s_seconds(60)
    inject_three_faults_in_a_row()

    port = 1337
    print('Listening on localhost:%s' % port)
    server = HTTPServer(('', port), RequestHandler)
    #server = ThreadingHTTPServer(('', port), RequestHandler)
    server.serve_forever()


if __name__ == "__main__":
    parser = OptionParser()
    parser.usage = ("Creates an http-server that will echo out any GET or POST parameters\n"
                    "Run:\n\n"
                    "   reflect")
    (options, args) = parser.parse_args()

    # initialize the random seed value to get reproducible random sequences
    seed(42)

    main()
