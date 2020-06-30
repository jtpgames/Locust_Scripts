---

**This project is WIP**
---
---

TODOs
--
- [ ] Reference to published paper or online version of it
- [ ] Reference to GS company group
- [ ] loadtest_plotter.py: Cleanup and reading data from files
- [ ] ARS_simulation.py: Cleanup, documentation and control workloads 
and parameters of the simulation model through CLI
- [ ] locust-parameter-variation.py: Cleanup and Documentation

Locust Performance Testing Infrastructure
---

Basically, the idea behind our performance testing infrastructure is to have three decoupled components, 
Python scripts in our case, that together allow to:

1. reproducible execute a load testing tool with a set of parameters for a particular experiment,
2. evaluate the performance measurements assisted by visualizations.

Generally, we have three types of components:
* Executors: execute a particular Load Tester as long as the Load Tester provides a CLI or an API;
* Load Testers: execute the load test, parametrized with values given by an Executor. 
Have to output a logfile containing the response times;
* Evaluators: read the logfile, plot at least the response times, 
and the performance requirements the target system has to comply with.

More details about our generic performance testing infrastructure can be found in our paper.

This repository contains the aforementioned Python scripts:

* executor.py: executes Locust with a set of parameters;
* locust-parameter-variation.py: executes Locust for as long as the ARS complies with real-time requirements
in order to find the saturation point of the ARS;
* locust_tester.py: contains specific code for Locust to perform the actual performance test.
For demonstration purposes, this script tests ARS_simulation.py.
Outputs a `locust_log.log`;
* loadtest_plotter.py: reads the `locust_log.log`, plots response times, and additional metrics 
to better visualize, if the real-time requirements of the EN 50136 are met.
* Alarm Receiving Software Simulation (ARS_simulation.py): simulates workload measured 
in the production environment of an industrial ARS.

# Quick start
* Clone the repository;
* run `pip3 install -r requirements.txt`;
* open two terminal shells: 
  1) run `python3 ARS_simulation.py` in one of them;
  2) run `python3 executor.py.` in the other.
* to stop the test, terminate the executor.py script;
* run `python3 loadtest_plotter.py`, pass the locust_log.log and see the results. :)

# Instructions to reproduce results in our paper
Using the performance testing infrastructure available in this repository, 
we conducted performance tests in a real-world alarm system provided by the GS company.
To provide a way to reproduce our results without the particular alarm system,
we build a software simulating the Alarm Receiving Software.
The simulation model uses variables, we identified as relevant and also performed some measurements
in the production environment, to initialize the variables correctly.

To reproduce our results, follow the steps in the Section "Quick start". The scripts are already preconfigured,
to simulate a realistic workload, inject faults, and automatically recover from them.
The recovery is performed after the time, the real fault management mechanism requires.

If you follow the steps and, for example, let the test run for about an hour, 
you will get similar results to the ones you can find in the Folder "Tests under Fault".

Results after running our scripts for about an hour:

![Results](Tests_under_Fault/30.06.20.svg)

---

Keep in mind that we use a simulated ARS here; in our paper we present measurements performed with a real system, 
thus the results reproduced with the code here are slightly different.

Nonetheless, the overall observations we made in our paper, are in fact reproducible.

---

# Instructions on how to adapt our performance testing infrastructure to other uses
After cloning the repository, take a look at the `locust_tester.py`. This is, basically, 
an ordinary [Locust script](https://docs.locust.io/en/stable/writing-a-locustfile.html) 
that sends request to the target system and measures the response time, 
when the response arrives. Our locust_tester.py is special, because:
* we implemented a [custom client](https://docs.locust.io/en/stable/testing-other-systems.html) 
instead of using the default;
* we additionally log the response times to a logfile 
instead of using the [.csv files](https://docs.locust.io/en/stable/retrieving-stats.html) Locust provides.

So, write a performance test using Locust, follow the instructions of the developers
on how to write a Locust script. The only thing to keep in mind is, that your Locust script 
has to output the measured response times to a logfile in the same way our script does it. 
Use `logger.info("Response time %s ms", total_time)` to log the response times.