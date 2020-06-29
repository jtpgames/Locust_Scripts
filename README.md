---
**This project is WIP**
---

This repository contains Python scripts I use in my research to perform performance tests:

* executor.py: executes Locust with a set of parameters;
* locust-parameter-variation.py: executes Locust for as long as the SUT complies with real-time requirements
in order to find the saturation point of the SUT;
* locust_tester.py: contains specific code for Locust to perform the actual performance test.
For demonstration purposes, this script tests SUT_simulation.py.
Outputs a `response_times.log`;
* loadtest_plotter.py: reads the response_times.log and plots them. `!WIP!`
* System under Test Simulation (SUT_simulation.py): simulates real-world workload measured in the production system.

# Instructions
* Clone the repository,
* run `pip3 install -r requirements.txt`
* open two terminal shells:
  * run `python HTTPEchoServer.py`
  * run `python3 executor.py.`
* to stop the text, terminate the executor.py script
* run `python3 loadtest_plotter.py`, pass the locust_log.log and see the results :)