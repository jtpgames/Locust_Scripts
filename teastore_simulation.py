from threading import current_thread
from time import sleep

from fastapi import FastAPI, Request

from stopwatch import Stopwatch

app = FastAPI(
    root_path="",
    title="TeaStore Simulation"
)

sleep_time_to_use = 0.1

commands = [
    "ID_LoginActionServlet_handlePOSTRequest",
    "ID_ProfileServlet_handleGETRequest",
    "ID_CartServlet_handleGETRequest",
    "ID_CategoryServlet_handleGETRequest",
]


@app.middleware("http")
async def simulate_processing_time(request: Request, call_next):
    command = request.url.path.removeprefix(prefix)

    for known_command in commands:
        if command.lower() in known_command.lower():
            print("Valid command")

    sleep(sleep_time_to_use)
    response = await call_next(request)
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


@app.get(f"{prefix}category")
def get_category(page: int, category: int, number: int):
    print(
        f"[{current_thread()}] GET category: page:{page}, "
        f"category:{category}, "
        f"number: {number}"
    )
    return {"message": "Empty cart"}
