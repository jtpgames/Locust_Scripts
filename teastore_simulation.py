#!/usr/bin/env python

# ###################### DEPRECATED ######################
# ## Replaced by the Rast-Simulator Project ##############
# ## Reason: Performance problems starting with ##########
# ## the medium intensity load profile. ##################
# Simulates the TeaStore software system using a model obtained by the RAST approach.

import asyncio
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from uuid import uuid4

import numpy
import pandas

from fastapi import FastAPI, Request, HTTPException, Response
from joblib import load
from uvicorn import run
import gunicorn.app.base

from stopwatch import Stopwatch

app = FastAPI(
    root_path="",
    title="TeaStore Simulation"
)

predictive_model = None
known_request_types = []


@app.on_event("startup")
async def startup_event():
    # workload_to_use = "gs"
    # predictive_model = load(f"Models/teastore_model_{workload_to_use}_workload.joblib")
    # known_request_types = load(f"Models/teastore_requests_{workload_to_use}_workload.joblib")
    global predictive_model
    global known_request_types

    predictive_model = load("Models/teastore_model_LR_02-12-2022.joblib")
    known_request_types = load("Models/teastore_requests_mapping_02-12-2022.joblib")

    logger.info(known_request_types)

number_of_parallel_requests_pending = 0
startedCommands = {}


# Because not everyone is using Python 3.9+ we use this one.
# Source: https://stackoverflow.com/a/16891418
def remove_prefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def namer(name):
    return name.replace(".log.", "") + ".log"


fh = TimedRotatingFileHandler(f"teastore-cmd_simulation.log", when='midnight')
fh.setLevel(logging.DEBUG)
fh.suffix = "_%Y-%m-%d"
fh.namer = namer

logging.basicConfig(format="[%(thread)d] %(asctime)s [%(levelname)s] %(message)s",
                    level=os.environ.get("LOGLEVEL", "DEBUG"),
                    handlers=[fh])

logger = logging.getLogger('Audit')


def log_info(tid, msg):
    if logger.isEnabledFor(logging.INFO):
        logging.info(f"UID: {str(tid):13},"
                     f" {msg}")


def log_command(tid, cmd, startOrEndOfCmd):
    log_info(
        tid,
        f" {startOrEndOfCmd:9}"
        f" {cmd}"
    )


def log_start_command(tid, cmd):
    log_command(tid, cmd, "CMD-START")


def log_end_command(tid, cmd):
    log_command(tid, cmd, "CMD-ENDE")


def predict_sleep_time(model, tid, command):
    request_type_as_int = known_request_types[command]

    X = numpy.reshape(
        [startedCommands[tid]["parallelCommandsStart"],
         startedCommands[tid]["parallelCommandsFinished"],
         request_type_as_int],
        (1, -1)
    )

    Xframe = pandas.DataFrame(X, columns=['PR 1', 'PR 3', 'Request Type'])

    logger.debug(f"-> UID: {tid}, X: {X} -")
    y = model.predict(Xframe)
    logger.debug(f"<- UID: {tid}, y: {y} -")

    y_value = y[0]
    y_value = max(0, y_value)

    return y_value


@app.middleware("http")
async def simulate_processing_time(request: Request, call_next):
    found_command = request.scope["X-CMD"]

    tid = request.scope['X-UID']

    stopwatch: Stopwatch = request.scope["X-SW"]

    total_sleep_time = 0

    sleep_time_to_use = predict_sleep_time(predictive_model, tid, found_command)
    logger.debug(f"--> UID: {tid}, {found_command}: Elapsed time: {stopwatch.duration}s")
    sleep_time_to_use -= stopwatch.duration
    sleep_time_to_use = max(0, sleep_time_to_use)

    if sleep_time_to_use > 0:
        logger.debug(f"--> UID: {tid}, {found_command}: Waiting for {sleep_time_to_use}")
        await asyncio.sleep(sleep_time_to_use)
        total_sleep_time += sleep_time_to_use

        for i in range(1):
            sleep_time_test = predict_sleep_time(predictive_model, tid, found_command)
            logger.debug(f"--> UID: {tid}, {found_command}: Elapsed time: {stopwatch.duration}s")
            sleep_time_test -= stopwatch.duration
            sleep_time_test = max(0, sleep_time_test)

            if sleep_time_test <= total_sleep_time:
                break
            else:
                sleep_time_to_use = sleep_time_test - total_sleep_time

            logger.debug(f"---> UID: {tid}, {found_command}: Waiting for {sleep_time_to_use}")
            await asyncio.sleep(sleep_time_to_use)
            total_sleep_time += sleep_time_to_use
    else:
        logger.debug(f"--> UID: {tid}, {found_command}: Skip waiting")

    response = await call_next(request)
    return response


@app.middleware("http")
async def track_parallel_requests(request: Request, call_next):
    global number_of_parallel_requests_pending

    number_of_parallel_requests_at_beginning = number_of_parallel_requests_pending
    number_of_parallel_requests_pending = number_of_parallel_requests_pending + 1

    found_command = request.scope["X-CMD"]

    tid = request.scope['X-UID']

    log_start_command(tid, found_command)

    startedCommands[tid] = {
        "cmd": found_command,
        "parallelCommandsStart": number_of_parallel_requests_at_beginning,
        "parallelCommandsFinished": 0
    }

    response = await call_next(request)

    number_of_parallel_requests_pending = number_of_parallel_requests_pending - 1

    startedCommands.pop(tid)

    for cmd in startedCommands.values():
        cmd["parallelCommandsFinished"] = cmd["parallelCommandsFinished"] + 1

    log_end_command(tid, found_command)

    return response


@app.middleware("http")
async def extract_command(request: Request, call_next):
    logger.debug(request.url.path)

    if request.url.path == "/" or request.url.path == "/logs/reset":
        return Response(content="Empty response", media_type="text/plain")

    # command = request.url.path.removeprefix(prefix)
    if request.url.path != prefix:
        command = remove_prefix(request.url.path, prefix)
    else:
        command = "index"

    tid = request.scope['X-UID']
    log_info(tid, f"Cmd: {command}")

    found_command = None

    for known_command in known_request_types:
        if command.lower() in known_command.lower():
            found_command = known_command
            break

    if found_command is None:
        raise HTTPException(status_code=404, detail="Command not found")

    logger.info(f"-> {found_command}")

    request.scope["X-CMD"] = found_command
    response = await call_next(request)

    return response


@app.middleware("http")
async def add_unique_id(request: Request, call_next):
    unique_command_id = hash(uuid4())

    # logger.debug(request.headers)
    # logger.debug(request.cookies)

    request.scope["X-UID"] = str(unique_command_id)
    response = await call_next(request)

    return response


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    stopwatch = Stopwatch()
    request.scope["X-SW"] = stopwatch
    response = await call_next(request)
    stopwatch.stop()

    if 'X-CMD' not in request.scope:
        return response

    tid = request.scope['X-UID']
    command = request.scope['X-CMD']
    # log_info(tid, f"CMD: {command}, Processing Time: {stopwatch}")
    logger.warning(f"UID: {tid}, CMD: {command}, Processing Time: {stopwatch}")
    response.headers["X-Process-Time"] = str(stopwatch)
    return response


prefix = "/tools.descartes.teastore.webui/"


@app.get(prefix)
async def index():
    logger.info(f"GET index")
    return {"message": "Success"}


@app.get(f"{prefix}login")
async def login():
    logger.info("GET login")
    return {"message": "Success"}


@app.post(f"{prefix}loginAction")
async def login_action(username: str = "", password: str = "", logout: str = ""):
    logger.info(f"POST login {username} {password} {logout}")
    return {"message": "Success"}


@app.get(f"{prefix}profile")
async def get_profile():
    logger.info(f"GET profile")
    return {"message": "SimProfile"}


@app.get(f"{prefix}cart")
async def get_cart():
    logger.info(f"GET cart")
    return {"message": "Empty cart"}


@app.post(f"{prefix}cartAction")
async def post_cart(action: str = "", productid: int = 0, confirm: str = ""):
    logger.info(f"POST cartAction with {action}, {productid}, {confirm}")
    return {"message": "Ok"}


@app.get(f"{prefix}category")
async def get_category(page: int, category: int, number: int = 0):
    logger.info(
        f"GET category: page:{page}, "
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
async def get_product(id: int):
    logger.info(
        f"GET product: id:{id}"
    )
    return {"name": "my product"}


class StandaloneApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def init(self, parser, opts, args):
        pass

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


if __name__ == "__main__":
    run(
        "teastore_simulation:app",
        host="0.0.0.0",
        port=1337,
        log_level="info",
        access_log=False,
        backlog=2048,
        workers=1,
        # reload=True,
    )

    # options = {
    #     'bind': '%s:%s' % ('0.0.0.0', '1337'),
    #     'workers': 1,
    #     'worker_class': 'uvicorn.workers.UvicornWorker',
    #     'worker_connections': 2048,
    #     'backlog': 2048,
    #     'reload': True,
    #     'loglevel': "debug",
    #     'accesslog': "-"
    # }
    # StandaloneApplication(app, options).run()
