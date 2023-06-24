#!/bin/sh

# ###################### DEPRECATED ######################
echo -e "\e[91mWARNING: This feature is deprecated.
See teastore_simulation.py for details.
If you want to use it, you need to set the port number in the start_teastore_loadtest.sh to 1337.\e[0m"

./start_sysstat.sh teastore

#uvicorn teastore_simulation:app --port 1337 --reload --backlog 2048
python teastore_simulation.py

pkill -f "sar"