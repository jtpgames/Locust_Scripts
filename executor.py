#!/usr/bin/env python
import csv
import logging
import os

import typer

from common.Common import call_locust_with

average_response_time = {}
min_response_time = {}
max_response_time = {}


def read_measurements_from_locust_csv_and_append_to_dictonaries(path, num_clients):
    logger = logging.getLogger('readMeasurementsFromCsvAndAppendToDictonaries')

    with open(path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        row = next(reader)
        logger.info("Avg: {}, Min: {}, Max: {}".format(row['Average Response Time'], row['Min Response Time'],
                                                       row['Max Response Time']))
        average_response_time[num_clients] = float(row['Average Response Time'])
        min_response_time[num_clients] = float(row['Min Response Time'])
        max_response_time[num_clients] = float(row['Max Response Time'])


# url = "http://localhost:1337"
# url = "http://192.168.64.6:8080"

fh = logging.FileHandler('executor.log')
fh.setLevel(logging.DEBUG)

logging.basicConfig(format="%(asctime)s %(message)s",
                    level=os.environ.get("LOGLEVEL", "INFO"),
                    handlers=[fh])


def main(
        locust_script: str = typer.Argument(
            ...,
            help="Path to the locust script to execute"
        ),
        url: str = typer.Option(
            "http://localhost:1337",
            "--url", "-u",
            help="URL of the System under Test"
        ),
        num_clients: int = typer.Option(
            1,
            "--num_clients", "-n",
            help="How many users should be simulated"
        ),
        runtime: int = typer.Option(
            -1,
            "--runtime", "-t",
            help="How many minutes the test should run."
        )
):
    call_locust_with(locust_script, url, num_clients, runtime)

    read_measurements_from_locust_csv_and_append_to_dictonaries("loadtest_1_clients_stats.csv", 1)


if __name__ == "__main__":
    typer.run(main)
