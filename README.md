# This repository is WIP
---

This repository contains Python scripts I use in my research to perform performance tests:

* executor.py: to execute Locust with a set of parameters;
* locust_tester.py: contains specific code for Locust to perform the actual performance test. Outputs a `response_times.log`;
* loadtest_plotter.py: reads the response_times.log and plots them.