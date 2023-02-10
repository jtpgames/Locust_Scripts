#!/usr/bin/env python
import csv
import logging
import os
from dataclasses import dataclass

import typer

from common.Common import call_locust_with

response_time_statistics = {}


@dataclass
class RequestStatistics:
    avg: float = 0
    min: float = 0
    max: float = 0


def read_measurements_from_locust_csv_and_append_to_dictonaries(path):
    logger = logging.getLogger('readMeasurementsFromCsvAndAppendToDictonaries')

    with open(path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            type = row['Type']
            name: str = row['Name']
            request_name = name.split('/')[len(name.split('/')) - 1]
            if request_name == "" or request_name == "Aggregated":
                continue

            if len(request_name.split('?')) > 1:
                request_name = request_name.split('?')[0]

            request = f"{type} {request_name}"

            if request not in response_time_statistics:
                response_time_statistics[request] = RequestStatistics()

            r = response_time_statistics[request]

            v = float(row['Average Response Time'])
            r.avg = v if r.avg < v else r.avg

            v = float(row['Min Response Time'])
            r.min = v if r.min < v else r.min

            v = float(row['Max Response Time'])
            r.max = v if r.max < v else r.max

        for r in response_time_statistics.items():
            logger.info(f"Request: {r}")


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
        ),
        silent: bool = typer.Option(
            False,
            "--silent", "-s",
            help="Omit .csv and log files"
        )
):
    if silent is False:
        fh = logging.FileHandler('executor.log')
        fh.setLevel(logging.DEBUG)

        logging.basicConfig(format="%(asctime)s %(message)s",
                            level=os.environ.get("LOGLEVEL", "INFO"),
                            handlers=[fh])

    call_locust_with(locust_script, url, num_clients, runtime, silent)

    if silent is False:
        read_measurements_from_locust_csv_and_append_to_dictonaries(f"loadtest_{num_clients}_clients_stats.csv")


if __name__ == "__main__":
    typer.run(main)
