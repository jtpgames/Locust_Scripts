---
**This project is WIP**
---

This repository contains Python scripts I use in my research to perform performance tests:

* executor.py: executes Locust with a set of parameters;
* locust-parameter-variation.py: executes Locust for as long as the ARS complies with real-time requirements
in order to find the saturation point of the ARS;
* locust_tester.py: contains specific code for Locust to perform the actual performance test.
For demonstration purposes, this script tests ARS_simulation.py.
Outputs a `locust_log.log`;
* loadtest_plotter.py: reads the `locust_log.log` and plots them.
* Alarm Receiving Software Simulation (ARS_simulation.py): simulates workload measured 
in the production environment of an industrial ARS.

# Quick start
* Clone the repository,
* run `pip3 install -r requirements.txt`
* open two terminal shells:
  * run `python3 ARS_simulation.py`
  * run `python3 executor.py.`
* to stop the test, terminate the executor.py script
* run `python3 loadtest_plotter.py`, pass the locust_log.log and see the results :)