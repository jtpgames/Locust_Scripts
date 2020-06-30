#!/usr/bin/env python
import glob
import csv

import platform
import os
import logging

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
        logger.info("Avg: {}, Min: {}, Max: {}".format(row['Average response time'], row['Min response time'],
                                                       row['Max response time']))
        average_response_time[num_clients] = float(row['Average response time'])
        min_response_time[num_clients] = float(row['Min response time'])
        max_response_time[num_clients] = float(row['Max response time'])


def call_locust_with(clients, runtimeInMin):
    logger = logging.getLogger('call_locust_with')

    logger.info("Starting locust with (%s, %s)", clients, runtimeInMin)

    if runtimeInMin > 0:
        os.system(
            f"locust -f {locust_script} \
            --host={url} \
            --no-web \
            --csv=loadtest_{clients}_clients \
            --clients={clients} --hatch-rate=1 \
            --run-time={runtimeInMin}m \
            --logfile locust_log.log"
        )
    else:
        os.system(
            f"locust -f {locust_script} \
            --host={url} \
            --no-web \
            --csv=loadtest_{clients}_clients \
            --clients={clients} --hatch-rate={clients} \
            --logfile locust_log.log"
        )


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
    call_locust_with(1, -1)

    read_measurements_from_locust_csv_and_append_to_dictonaries(f"loadtest_{1}_clients_stats.csv", 1)
