import argparse
import logging
import os
from re import search
from datetime import datetime
from typing import Dict


def get_date_from_string(line):
    return search(r"\d*-\d*-\d*", line).group().strip()


def contains_timestamp_with_ms(line: str):
    return search(r"(?<=\])\s*\d*-\d*-\d*\s\d*:\d*:\d*\.\d*", line) is not None


def get_timestamp_from_string(line: str):
    return search(r"(?<=\])\s*\d*-\d*-\d*\s\d*:\d*:\d*\.?\d*", line).group().strip()


def dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")


def readResponseTimesFromLogFile(path: str) -> Dict[datetime, float]:
    response_times = {}

    # if 'locust_log' not in path:
    #     return response_times

    with open(path) as logfile:
        for line in logfile:
            if 'Response time' not in line:
                continue

            time_stamp = datetime.strptime(search('\\[.*\\]', line).group(), '[%Y-%m-%d %H:%M:%S,%f]')
            response_time = search('(?<=Response time\\s)\\d*', line).group()

            response_times[time_stamp] = float(response_time) / 1000

    return response_times


def call_locust_with(locust_script, url, clients, runtime_in_min=-1, omit_csv_files=False):
    logger = logging.getLogger('call_locust_with')

    logger.info("Starting locust with (%s, %s)", clients, runtime_in_min)

    params = f"-f {locust_script} "
    params += f"--host={url} "
    params += "--headless "
    if omit_csv_files is False:
        params += f"--csv=loadtest_{clients}_clients "

    if runtime_in_min > 0:
        os.system(
            f"locust {params} \
            --users={clients} --spawn-rate=50 \
            --run-time={runtime_in_min}m \
            --logfile locust_log_{clients}.log"
        )
    else:
        os.system(
            f"locust {params} \
            --users={clients} --spawn-rate={clients} \
            --logfile locust_log.log"
        )
