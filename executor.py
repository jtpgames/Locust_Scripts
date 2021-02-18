#!/usr/bin/env python
import glob
import csv

import platform
import os
import logging

from common.Common import call_locust_with

average_response_time = {}
min_response_time = {}
max_response_time = {}

plt = platform.system()

if plt != "Windows":
    import readline


def complete_python(text, state):
    # replace ~ with the user's home dir. See https://docs.python.org/2/library/os.path.html
    if '~' in text:
        text = os.path.expanduser('~')

    # autocomplete directories with having a trailing slash
    if os.path.isdir(text):
        text += '/'

    return [x for x in glob.glob(text + '*.py')][state]


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


if plt != "Windows":
    readline.set_completer_delims(' \t\n;')
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete_python)

locust_script = input('Path to the Locust script: ')

if plt != "Windows":
    readline.set_completer(None)

#url = input('URL of the software to test: ')

url = "http://localhost:1337"

fh = logging.FileHandler('executor.log')
fh.setLevel(logging.DEBUG)

logging.basicConfig(format="%(asctime)s %(message)s",
                    level=os.environ.get("LOGLEVEL", "INFO"),
                    handlers=[fh])

if __name__ == "__main__":
    call_locust_with(locust_script, url, 1)

    read_measurements_from_locust_csv_and_append_to_dictonaries("loadtest_1_clients_stats.csv", 1)
