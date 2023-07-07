import logging
import os
from os import path
from re import search
from datetime import datetime, timedelta
from typing import Dict


def read_response_times_from_locust_logfile(path: str):
    response_times = []
    time_stamps = []

    if 'locust_log' not in path:
        return response_times

    with open(path) as logfile:
        for line in logfile:
            if 'Response time' not in line:
                continue

            time_stamp = datetime.strptime(search('\\[.*\\]', line).group(), '[%Y-%m-%d %H:%M:%S,%f]')
            request_type = search('\\(.*\\)', line)
            if request_type is not None:
                request_type = request_type.group()
                request_type = request_type.strip('()')
            response_time = search('(?<=Response time\\s)\\d*', line).group()

            while True:
                if time_stamp in time_stamps:
                    time_stamp += timedelta(microseconds=100)
                else:
                    break

            time_stamps.append(time_stamp)
            response_times.append({
                "time_stamp": time_stamp,
                "request_type": request_type,
                "response_time_ms": float(response_time)
            })

    return response_times


def call_locust_and_distribute_work(locust_script, url, clients, runtime_in_min, use_load_test_shape=True):
    logger = logging.getLogger('call_locust_and_distribute_work')

    params = f"-f {locust_script} "
    params += f"--host={url} "
    params += "--headless "
    params += "--stop-timeout 10 "
    params += "--only-summary "

    locust_path = "locust"
    if path.exists("venv/bin/locust"):
        locust_path = "venv/bin/locust"

    num_workers = 5
    for i in range(0, num_workers):
        logger.info(f"Starting {i+1}. worker")

        os.system(
            f"env use_load_test_shape={use_load_test_shape} \
            {locust_path} {params} \
                --logfile worker_log_{clients}.{i+1}.log \
                --worker &"
        )

    logger.info("Starting master to run for %s min", runtime_in_min)
    logger.info(f"--expect-workers={num_workers}")

    os.system(
        f"env use_load_test_shape={use_load_test_shape} \
        {locust_path} {params} \
            --run-time={runtime_in_min}m \
            --users={clients} --spawn-rate={num_workers * 100} \
            --logfile locust_log_{clients}.log \
            --csv=loadtest_{clients}_clients \
            --master \
            --expect-workers={num_workers}"
    )


def call_locust_with(locust_script, url, clients, runtime_in_min=-1, omit_csv_files=False, use_load_test_shape=True):
    logger = logging.getLogger('call_locust_with')

    logger.info("Starting locust with (%s, %s)", clients, runtime_in_min)

    params = f"-f {locust_script} "
    params += f"--host={url} "
    params += "--headless "
    params += "--stop-timeout 10 "
    params += "--only-summary "
    if omit_csv_files is False:
        params += f"--csv=loadtest_{clients}_clients "
    
    locust_path = "locust"
    if path.exists("venv/bin/locust"):
        locust_path = "venv/bin/locust"

    if runtime_in_min > 0:
        os.system(
            f"env use_load_test_shape={use_load_test_shape} \
            {locust_path} {params} \
            --users={clients} --spawn-rate=100 \
            --run-time={runtime_in_min}m \
            --logfile locust_log_{clients}.log"
        )
    else:
        os.system(
            f"env use_load_test_shape={use_load_test_shape} \
            {locust_path} {params} \
            --users={clients} --spawn-rate={clients} \
            --logfile locust_log.log"
        )
