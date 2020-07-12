import re
from datetime import datetime
from typing import Dict


def readResponseTimesFromLogFile(path: str) -> Dict[datetime, float]:
    response_times = {}

    # if 'locust_log' not in path:
    #     return response_times

    with open(path) as logfile:
        for line in logfile:
            if 'Response time' not in line:
                continue

            time_stamp = datetime.strptime(re.search('\\[.*\\]', line).group(), '[%Y-%m-%d %H:%M:%S,%f]')
            response_time = re.search('(?<=Response time\\s)\\d*', line).group()

            response_times[time_stamp] = float(response_time) / 1000

    return response_times
