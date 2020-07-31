import argparse
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
