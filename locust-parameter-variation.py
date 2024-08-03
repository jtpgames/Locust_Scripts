#!/usr/bin/env python
import argparse
import csv
import glob

import os
import logging
import time

from common.Common import call_locust_with, call_locust_and_distribute_work

input_args = argparse.Namespace()


url = "http://localhost:1337"

fh = logging.FileHandler('locust-parameter-variation.log')
fh.setLevel(logging.DEBUG)

logging.basicConfig(format="%(asctime)s %(message)s",
                    level=os.environ.get("LOGLEVEL", "INFO"),
                    handlers=[fh])

avg_time_allowed_in_s = 10
max_time_allowed_in_s = 30
average_response_time = {}
min_response_time = {}
max_response_time = {}


def read_measurements_from_locust_csv_and_append_to_dictonaries(path, num_clients):
    logger = logging.getLogger('readMeasurementsFromCsvAndAppendToDictonaries')

    with open(path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        avg = 0
        min = 0
        max = 0
        for row in reader:
            v = float(row['Average Response Time'])
            avg = v if avg < v else avg

            v = float(row['Min Response Time'])
            min = v if min < v else min

            v = float(row['Max Response Time'])
            max = v if max < v else max

        logger.info("Avg: {}, Min: {}, Max: {}".format(avg, min, max))
        average_response_time[num_clients] = float(avg)
        min_response_time[num_clients] = float(min)
        max_response_time[num_clients] = float(max)


def config_complies_with_real_time_requirements(num_clients):
    logger = logging.getLogger('config_complies_with_real_time_requirements')

    # return True, because we have no measurements yet
    if len(average_response_time) == 0 or len(max_response_time) == 0:
        return True

    if average_response_time[num_clients] == 0 or max_response_time[num_clients] == 0:
        logger.error("Something went wrong: average or max response time was 0")
        return False

    average_response_time_s = average_response_time[num_clients] / 1000
    max_response_time_s = max_response_time[num_clients] / 1000

    logger.info(f"Clients: {num_clients}: avg: {average_response_time_s}s, max: {max_response_time_s}s")

    exceeds_average_response_time = average_response_time_s > avg_time_allowed_in_s
    exceeds_max_response_time = max_response_time_s > max_time_allowed_in_s

    is_compliant = not (exceeds_average_response_time or exceeds_max_response_time)

    logger.info(f"--> {is_compliant}")

    return is_compliant


def get_next_number_of_clients_for_load_test(previous_number_of_clients: int, multiplier: int, num_failures: int) -> int:
    adjusted_multiplier = multiplier / max(num_failures * 10, 1)

    if adjusted_multiplier <= 10:
        return 0

    num_clients = previous_number_of_clients + adjusted_multiplier

    return int(num_clients)


def parameter_variation_loop(multiplier: int = 5000):
    logger = logging.getLogger('parameter_variation_loop')

    last_succeeded_num_clients = 0
    last_failed_num_clients = 0
    num_failures = 0

    logger.info(f"Starting performance test.")

    is_first_run = True
    while True:
        if not is_first_run:
            logger.info("Sleeping for 1 min ...")
            time.sleep(60)
        is_first_run = False

        # start with multiplier clients, then increase linearly (2*multiplier, ... x*multiplier)
        # until the number of clients exceeds the threshold.
        # After that, start from the last working number of clients and keep increasing with one tenth of the multiplier (x*multiplier + y*multiplier/10)
        num_clients = get_next_number_of_clients_for_load_test(last_succeeded_num_clients, multiplier, num_failures)
        if num_clients == 0:
            break

        call_locust_and_distribute_work(locust_script, url, num_clients, runtime_in_min=1, use_load_test_shape=False)

        read_measurements_from_locust_csv_and_append_to_dictonaries(f"loadtest_{num_clients}_clients_stats.csv", num_clients)

        if config_complies_with_real_time_requirements(num_clients):
            last_succeeded_num_clients = num_clients
        else:
            num_failures += 1
            last_failed_num_clients = num_clients

    logger.info(f"Finished performance test. System failed at {last_failed_num_clients}")


def parameter_variation_loop_old(multiplier: int = 5000):
    logger = logging.getLogger('parameter_variation_loop')

    num_clients = 1
    x = 1
    y = 0
    z = 0

    logger.info(f"Starting performance test.")

    is_first_run = True
    while config_complies_with_real_time_requirements(num_clients):
        if not is_first_run:
            logger.info("Sleeping for 1 min ...")
            time.sleep(60)
        is_first_run = False

        # start with multiplier clients, then increase linearly (2*multiplier, ... x*multiplier)
        # until the number of clients exceeds the threshold. 
        # After that, keep increasing with one tenth of the multiplier (x*multiplier + y*multiplier/10)
        num_clients = max(x * multiplier + y * int(multiplier / 10) + z * 10, 1)
        if num_clients >= 1500:
            z += 1
        elif num_clients >= 1200:
            y += 1
        else:
            x += 1

        call_locust_and_distribute_work(locust_script, url, num_clients, runtime_in_min=10, use_load_test_shape=False)
        # call_locust_with(locust_script, url, num_clients, runtime_in_min=10, omit_csv_files=True)

        read_measurements_from_locust_csv_and_append_to_dictonaries(f"loadtest_{num_clients}_clients_stats.csv", num_clients)

    logger.info(f"Finished performance test. System failed at {num_clients}")


def read_cli_args():
    parser = argparse.ArgumentParser(description='Locust Wrapper.')
    parser.add_argument('locust_script', help='Path to the locust script to execute')
    parser.add_argument('-p', '--parametervariation', action='store_true', help='run the test and variate parameters')
    parser.add_argument('-m', '--multiplier',
                        type=int,
                        help='start and linearly increase number of clients by the given multiplier',
                        default=200)
    parser.add_argument('-u', '--url', help='URL of the System under Test')

    global input_args

    input_args = parser.parse_args()
    print("Args: " + str(input_args))


if __name__ == "__main__":
    read_cli_args()

    locust_script = input_args.locust_script
    if input_args.url:
        url = input_args.url

    if input_args.parametervariation:
        parameter_variation_loop(input_args.multiplier)
    else:
        call_locust_with(locust_script, url, clients=1)

        read_measurements_from_locust_csv_and_append_to_dictonaries("loadtest_1_clients_stats.csv", 1)
