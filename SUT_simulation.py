#!/usr/bin/env python
# Simulates the System under Test you want to test.
# Based on https://gist.github.com/huyng/814831 Written by Nathan Hamiel (2010)

from http.server import HTTPServer, BaseHTTPRequestHandler
from optparse import OptionParser
from random import random, seed
from time import sleep

from datetime import datetime

begin_of_fault = datetime(1970, 1, 1)
chosen_fault_time = 0


def between(min, max):
    return min + random() * (max - min)


def simulate_fault():
    """
    simulate a fault:

    * this method causes the function `is_faulted` to return true for `chosen_fault_time` seconds.
    * `chosen_fault_time` is set using the ideal time the real-world fault management mechanism requires.
    """
    global begin_of_fault
    begin_of_fault = datetime.now()

    # this is the ideal time,
    # the fault management needs to perform a recovery operation
    # when a fault occurs
    # these are the expected min and max times based on the real-world fault detection mechanism.
    expected_fault_time_min = 26
    expected_fault_time_max = 34

    global chosen_fault_time
    chosen_fault_time = between(expected_fault_time_min, expected_fault_time_max)


def is_faulted():
    now = datetime.now()

    return (now - begin_of_fault).seconds <= chosen_fault_time


def simulate_workload_under_faults():
    """
    Simulate a minimal workload based on real processing times measured
    in the production environment and randomly inject faults.
    """

    # min time measured from 16541 requests
    min_processing_time = 6

    # inject a fault every minute
    if (datetime.now() - begin_of_fault).seconds > 60:
        simulate_fault()

    if is_faulted():
        print("System faulted for {} s".format(chosen_fault_time))
        return False

    wait_time = min_processing_time

    print("Waiting for {}".format(wait_time))

    sleep(wait_time)

    return True


def simulate_minimal_workload_of_staging_system():
    # min time measured with Locust in the staging system
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

        #is_successful = simulate_workload_under_faults()
        is_successful = simulate_minimal_workload_of_staging_system()

        print("<----- Request End -----\n")

        self.send_response(200 if is_successful else 500)
        self.end_headers()

    do_PUT = do_POST
    do_DELETE = do_GET


def main():
    port = 13565
    print('Listening on localhost:%s' % port)
    server = HTTPServer(('', port), RequestHandler)
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
