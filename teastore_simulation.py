import logging
import os
import threading
from datetime import datetime
from threading import current_thread
from time import sleep

import psutil
from fastapi import FastAPI, Request
from joblib import load

from stopwatch import Stopwatch

app = FastAPI(
    root_path="",
    title="TeaStore Simulation"
)

predictive_model = load("teastore_model.joblib")
known_request_types = load("teastore_requests.joblib")

print(known_request_types)

number_of_parallel_requests_pending = 0
startedCommands = {}


# Because not everyone is using Python 3.9+ we use this one.
# Source: https://stackoverflow.com/a/16891418
def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


date_today = datetime.now().strftime('%Y-%m-%d')

fh = logging.FileHandler(f"teastore-cmd_simulation_{date_today}.log", mode='w')
fh.setLevel(logging.DEBUG)

logging.basicConfig(format="%(message)s",
                    level=os.environ.get("LOGLEVEL", "INFO"),
                    handlers=[fh])


def log_command(cmd, startOrEndOfCmd):
    tid = threading.get_ident()

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

    logging.info(f"[{str(tid):13}]"
                 f" {timestamp}"
                 f" {startOrEndOfCmd:9}"
                 f" {cmd}")


def log_start_command(cmd):
    log_command(cmd, "CMD-START")


def log_end_command(cmd):
    log_command(cmd, "CMD-ENDE")


def predict_sleep_time(model, tid, command):
    from numpy import array

    request_type_as_int = known_request_types[command]

    X = array([startedCommands[tid]["parallelCommandsStart"],
               startedCommands[tid]["parallelCommandsFinished"],
               request_type_as_int,
               psutil.cpu_percent()]) \
        .reshape(1, -1)

    # print(f"X: {X}")

    y = model.predict(X)

    print(f"y: {y}")

    # y_value = y[0, 0]
    y_value = y[0]
    y_value = max(0, y_value)

    return y_value


@app.middleware("http")
async def simulate_processing_time(request: Request, call_next):
    # command = request.url.path.removeprefix(prefix)
    command = remove_prefix(request.url.path, prefix)

    print(f"Cmd: {command}")

    sleep_time_to_use = 0.1

    found_command = None

    for known_command in known_request_types:
        if command.lower() in known_command.lower():
            found_command = known_command
            break

    if found_command is not None:
        print(f"-> {found_command}")

        tid = threading.get_ident()
        sleep_time_to_use = predict_sleep_time(predictive_model, tid, found_command)

        print("Waiting for {}".format(sleep_time_to_use))
        sleep(sleep_time_to_use)

        sleep_time_last_time = sleep_time_to_use
        while True:
            sleep_time_test = predict_sleep_time(predictive_model, tid, found_command)
            if sleep_time_test <= sleep_time_last_time:
                break
            else:
                sleep_time_to_use = sleep_time_test - sleep_time_last_time

            sleep_time_last_time = sleep_time_test
            print("Waiting for {}".format(sleep_time_to_use))
            sleep(sleep_time_to_use)

    response = await call_next(request)
    return response


@app.middleware("http")
async def track_parallel_requests(request: Request, call_next):
    global number_of_parallel_requests_pending

    number_of_parallel_requests_at_beginning = number_of_parallel_requests_pending
    number_of_parallel_requests_pending = number_of_parallel_requests_pending + 1

    tid = threading.get_ident()

    # command = request.url.path.removeprefix(prefix)
    command = remove_prefix(request.url.path, prefix)

    found_command = None

    for known_command in known_request_types:
        if command.lower() in known_command.lower():
            found_command = known_command
            break

    if found_command is not None:
        log_start_command(found_command)

        startedCommands[tid] = {
            "cmd": found_command,
            "parallelCommandsStart": number_of_parallel_requests_at_beginning,
            "parallelCommandsFinished": 0
        }

    response = await call_next(request)

    if found_command is not None:
        number_of_parallel_requests_pending = number_of_parallel_requests_pending - 1

        startedCommands.pop(tid)

        for cmd in startedCommands.values():
            cmd["parallelCommandsFinished"] = cmd["parallelCommandsFinished"] + 1

        log_end_command(found_command)

    return response


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    stopwatch = Stopwatch()
    response = await call_next(request)
    stopwatch.stop()
    process_time = stopwatch.duration
    print("Processing Time: ", stopwatch)
    response.headers["X-Process-Time"] = str(process_time)
    return response


prefix = "/tools.descartes.teastore.webui/"


@app.post(f"{prefix}loginAction")
def login(username: str = "", password: str = "", logout: str = ""):
    print(f"[{current_thread()}] POST login {username} {password} {logout}")
    return {"message": "Success"}


@app.get(f"{prefix}profile")
def get_profile():
    print(f"[{current_thread()}] GET profile")
    return {"message": "SimProfile"}


@app.get(f"{prefix}cart")
def get_cart():
    print(f"[{current_thread()}] GET cart")
    return {"message": "Empty cart"}


@app.post(f"{prefix}cartAction")
def post_cart(action: str):
    print(f"[{current_thread()}] POST cartAction with {action}")
    return {"message": "Ok"}


@app.get(f"{prefix}category")
def get_category(page: int, category: int, number: int):
    print(
        f"[{current_thread()}] GET category: page:{page}, "
        f"category:{category}, "
        f"number: {number}"
    )

    random_products = range(1, 50)

    result_string = ""
    for product in random_products:
        result_string += """<a href="/tools.descartes.teastore.webui/product?id={0}" ><img 
            src=""
            alt="Assam (loose)"></a>""".format(product)

    return result_string


@app.get(f"{prefix}product")
def get_product(id: int):
    print(
        f"[{current_thread()}] GET product: id:{id}"
    )
    return {"name": "my product"}
