#!/bin/sh

./start_sysstat.sh teastore

#uvicorn teastore_simulation:app --port 1337 --reload --backlog 2048
python teastore_simulation.py

pkill -f "sar"