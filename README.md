# Improved RAST Simulator and Load Tester Components (In Review: MASCOTS 2023)
**Last change from: 03.06.2023**

In our publication (currently in review at MASCOTS 2023), we explain, implement and evaluate improvements to the following components of RAST:
* Predictive Model Creator,
* Simulator,
* Load Tester.

For our evaluation, we use the [TeaStore benchmarking application](https://github.com/DescartesResearch/TeaStore). 
We created a [GitHub fork](https://github.com/jtpgames/TeaStore) and modified some parameters of their logging framework to create consistent logs especially for higher intensity workloads. 

This repository contains the improved Load Tester 
whereas the Simulator and the predictive models we created can be found in this (TODO: Add link) repository.
The Automated Estimator Pipeline (see below) is one implementation of the remaining RAST components (including the Predictive Model Creator).

Additional experimental results, including the Python scripts we use for similarity calculation, not published in our paper can be accessed in our [Datalore notebook](https://datalore.jetbrains.com/notebook/6K6VkECuLMtN5t5nSYg6WK/TVGp1egwDQlwI19astdVlM).

# Automated Estimator Pipeline
**Last change from: 03.06.2023**

The [Automated Estimator Pipline](https://github.com/jtpgames/Automated-Estimator-Pipeline) by Adrian Liermann was developed as part of his master's thesis.
In his thesis, he implements and evaluates improvements to our RAST approach, 
in particular, improvements to the training process. 
In the RAST approach, 
the following components are of particular interest to the training process:
* Log Transformer
* Predictive Model Creator

The Automated Estimator Pipeline is an implementation of these improved components wrapped in a CLI tool.

# RAST Simulator and Load Tester Components (MASCOTS 2022)

**Last change from: 31.10.2022**

In our [latest publication at MASCOTS 2022](https://www.doi.org/10.1109/MASCOTS56607.2022.00015), we explain our extension of this project.
* We provide a regression model learned from log files using our RAST approach;
* we improved the Simulator so that it uses the regression model to simulate processing times of the System-Under-Evaluation (SUE);
* we built a [mininet](http://mininet.org/) topology to ease the process of reproducibly launching experiments. 
We modelled the link parameters based on the infrastructure of the SUE;
* we implemented additional ancillary Python scripts to help analyse the log files.

# Instructions to launch an experiment
## Quick start

> Tested with
> * Python 3.8.10 on Ubuntu 20.04 LTS
> * Python 3.9.12 on macOS 12.6.1

* Clone the repository
* run `cd <the_directory_you_cloned_the_repository>`
* create a python virtual environment in a directory called `venv`, e.g., `python3 -m venv venv` 
* activate virtual environment with `source activate_venv.sh` 
* run `pip install -r requirements.txt`
* install mininet using the command `sudo apt-get install mininet` (in case you need additional help, consult the [mininet documentation](http://mininet.org/download/)
* run `cd mininet`
* execute `./start_mininet.sh`
* if mininet successfully started the experiment, you will notice a series of log files that were created:
    * ARS_simulation.log (means that the Simulator is running)
    * locust-parameter-variation.log (means that the load tester is generating the alarm device workload)
    * locust.log (means that the load tester is generating the background workload)
* in another terminal, run `cd <the_directory_you_cloned_the_repository>`
* run `tail -f locust-parameter-variation.log`
* the experiment may run for a couple of hours. 
The experiment ends, once the locust-parameter-variation.log prints the message "Finished performance test. System failed at ..."
* after that, you can analyse the log files. 
The locust-parameter-variation.log is of particular interest 
as it contains the measured average and maximum response times 
depending on the number of simulated alarm devices.

# Locust Performance Testing Infrastructure (MASCOTS 2020)

**Last change from: 06.06.2021**

In [[1]](https://www.doi.org/10.1007/978-3-030-68110-4_9), we introduced a 
generic performance testing infrastructure and used it in an industrial case study. 
Our idea is to have decoupled components, 
Python scripts in our case, that together allow to:

1. reproducible execute a load testing tool with a set of parameters for a particular experiment,
2. evaluate the performance measurements assisted by visualizations or automatic evaluators.

Generally, we have four types of components in our infrastructure:

* Executors: execute a particular Load Tester as long as the Load Tester provides a CLI or an API;
* Load Testers: execute the load test, parametrized with values given by an Executor. Have to output a logfile containing the response times;
* Evaluators: postprocess the logfile and for example plot the response times;
* Systems under Test (SUTs): Target systems we want to test. 
Usually, the target systems will be external systems, e.g., web servers. 
In our case, we build software that simulates the behavior of a real system, 
in order to provide the means for others to roughly reproduce our experiments.

More details about our generic performance testing infrastructure can be found in our paper [[1]](https://www.doi.org/10.1007/978-3-030-68110-4_9).

This repository contains the aforementioned Python scripts:

* Executors:
    * executor.py: executes Locust with a set of parameters;
    * locust-parameter-variation.py: executes Locust and keeps increasing the load.
    This is similar to Locust's [Step Load Mode](https://docs.locust.io/en/stable/running-locust-in-step-load-mode.html), 
    however, our approach increases the number of clients for as long as the ARS complies with real-time requirements
    in order to find the saturation point of the ARS. 
* Load Testers:
    * locust_tester.py: contains specific code for Locust to perform the actual performance test.
For demonstration purposes, this script tests ARS_simulation.py.
Outputs a `locust_log.log`;
    * locust_multiple_requests: an enhanced version of locust_tester that sends additional requests to generate more load.
    * locust_teastore.py: performs load testing against TeaStore, or our simulated TeaStore.
* Evaluators:
    * loadtest_plotter.py: reads the `locust_log.log`, plots response times, and additional metrics 
to better visualize, if the real-time requirements of the EN 50136 are met.
* SUTs
    * Alarm Receiving Software Simulation (ARS_simulation.py): simulates an industrial ARS 
based on data measured in the production environment of the GS company group.
    * TeaStore (teastore_simulation.py): simulates TeaStore based on a predictive model
generated in a lab environment.

# Instructions to reproduce results in our paper
## Quick start
* Clone the repository;
* run `pip3 install -r requirements.txt`;
* In the file `ARS_simulation.py` make sure that 
the constant `MASCOTS2020` is set to `True`.
* open two terminal shells:
  1. run `python3 ARS_simulation.py` in one of them;
  2. run `python3 executor.py.` in the other.
* to stop the test, terminate the executor.py script;
* run `python3 loadtest_plotter.py`, pass the locust_log.log and see the results. :)

## Details
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

So, write a performance test using Locust, following the instructions of the Locust developers
on how to write a Locust script. The only thing to keep in mind is, that your Locust script 
has to output the measured response times to a logfile in the same way our script does it. 
Use `logger.info("Response time %s ms", total_time)` to log the response times.

When you have your Locust script ready, execute it with `python3 executor.py`, 
pass the path to your script as argument, 
and when you want to finish the load test, terminate it with `Ctrl + C`.

Use `python3 executor.py --help` to get additional information.

Example call:
```
% python3 executor.py locust_scripts/locust_tester.py
```

After that, plot your results:

```
% python3 loadtest_plotter.py
Path to the logfile: locust_log.log
```
