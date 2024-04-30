#!/usr/bin/env python
import csv
import logging
import os
from dataclasses import dataclass

import typer
from pandas.core.frame import DataFrame

from common.Common import call_locust_with, read_response_times_from_locust_logfile

response_time_statistics = {}


@dataclass
class RequestStatistics:
    avg: float = 0
    min: float = 0
    max: float = 0


def read_measurements_from_locust_csv_and_append_to_dictonaries(path):
    logger = logging.getLogger('readMeasurementsFromCsvAndAppendToDictonaries')

    logger.info("Measurements from Locust .csv file")

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
            if r.min == 0:
                r.min = v
            else:
                r.min = v if r.min > v else r.min

            v = float(row['Max Response Time'])
            r.max = v if r.max < v else r.max

        for r in response_time_statistics.items():
            logger.info(f"Request: {r}")


def analyse_teastore_response_times():
    response_times = read_response_times_from_locust_logfile("locust_log.log")
    df = DataFrame.from_records(response_times)
    df_grouped_by_request_type = df.groupby(['request_type'])
    df_mean_response_times = df_grouped_by_request_type.mean()
    df_min_response_times = df_grouped_by_request_type.min()
    df_max_response_times = df_grouped_by_request_type.max()
    get_login = RequestStatistics(
        df_mean_response_times.loc['GET login', 'response_time_ms'],
        df_min_response_times.loc['GET login', 'response_time_ms'],
        df_max_response_times.loc['GET login', 'response_time_ms']
    )
    post_login_action = RequestStatistics(
        df_mean_response_times.loc['POST loginAction', 'response_time_ms'],
        df_min_response_times.loc['POST loginAction', 'response_time_ms'],
        df_max_response_times.loc['POST loginAction', 'response_time_ms']
    )
    get_category = RequestStatistics(
        df_mean_response_times.loc['GET category', 'response_time_ms'],
        df_min_response_times.loc['GET category', 'response_time_ms'],
        df_max_response_times.loc['GET category', 'response_time_ms']
    )
    get_product = RequestStatistics(
        df_mean_response_times.loc['GET product', 'response_time_ms'],
        df_min_response_times.loc['GET product', 'response_time_ms'],
        df_max_response_times.loc['GET product', 'response_time_ms']
    )
    post_cart_action = RequestStatistics(
        df_mean_response_times.loc['POST cartAction', 'response_time_ms'],
        df_min_response_times.loc['POST cartAction', 'response_time_ms'],
        df_max_response_times.loc['POST cartAction', 'response_time_ms']
    )
    get_profile = RequestStatistics(
        df_mean_response_times.loc['GET profile', 'response_time_ms'],
        df_min_response_times.loc['GET profile', 'response_time_ms'],
        df_max_response_times.loc['GET profile', 'response_time_ms']
    )
    logging.info("Measurements from Locust .log file")
    logging.info(f"GET login: {get_login}")
    logging.info(f"GET category: {get_category}")
    logging.info(f"GET product: {get_product}")
    logging.info(f"GET profile: {get_profile}")
    logging.info(f"POST loginAction: {post_login_action}")
    logging.info(f"POST cartAction: {post_cart_action}")


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

    pipe_fd = 0
    open_fifo_pipe_env = os.environ.get('OPEN_FIFO_PIPE')
    if open_fifo_pipe_env is not None and open_fifo_pipe_env:
        pipe_name = "/tmp/locust_executor_pipe"
        if not os.path.exists(pipe_name):
            os.mkfifo(pipe_name)

        logging.info("Opening locust_executor_pipe")
        pipe_fd = os.open(pipe_name, os.O_WRONLY)
        logging.info("Pipe opened")
    try:
        load_intensity_profile_env = os.environ.get('LOAD_INTENSITY_PROFILE')
        if load_intensity_profile_env is not None:
            if pipe_fd != 0:
                os.write(pipe_fd, str(load_intensity_profile_env).encode())

        call_locust_with(locust_script, url, num_clients, runtime, silent)

        if silent is False:
            read_measurements_from_locust_csv_and_append_to_dictonaries(f"loadtest_{num_clients}_clients_stats.csv")

        if "teastore" in locust_script:
            analyse_teastore_response_times()

        if pipe_fd != 0:
            os.write(pipe_fd, "FIN".encode())
    finally:
        if pipe_fd != 0:
            os.close(pipe_fd)


if __name__ == "__main__":
    typer.run(main)
