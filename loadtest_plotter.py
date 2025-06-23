import csv
from datetime import datetime
from pathlib import Path
import re
from typing import Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import typer
from typing_extensions import Annotated

from rast_common.main.FileUtils import readResponseTimesFromLogFile

num_clients = []
avg_time_allowed = []
max_time_allowed = []
average_response_time = []
min_response_time = []
max_response_time = []


def readMeasurementsFromCsvAndAppendToList(path):
    with open(path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        row = next(reader)
        print(row['Average response time'], row['Min response time'], row['Max response time'])
        average_response_time.append(float(row['Average response time']) / 1000)
        min_response_time.append(float(row['Min response time']) / 1000)
        max_response_time.append(float(row['Max response time']) / 1000)


def readMeasurementsFromLogFileAndAppendToList(path):
    with open(path) as logfile:
        for line in logfile:
            if 'Clients' not in line:
                continue

            lineAfterClients = line.split('Clients')[1]

            cleanedLine = lineAfterClients.replace('s', '')
            cleanedLine = cleanedLine.replace(',', '')
            cleanedLine = cleanedLine.replace('avg', '')
            cleanedLine = cleanedLine.replace('max', '')

            splittedLine = cleanedLine.split(':')

            clients = float(splittedLine[1])
            avg = float(splittedLine[3])
            max = float(splittedLine[4])

            num_clients.append(clients)
            average_response_time.append(avg)
            max_response_time.append(max)

            avg_time_allowed.append(10)
            max_time_allowed.append(30)

            print(clients, avg, max)


def plot_response_times(response_times, fault_injector_logfiles: list[Path] = []):
    dates = list(response_times.keys())
    times = list(response_times.values())

    plt.plot(dates, times, 'o', color='black', label='Response time')

    def read_lines_with_ARS_faults(file_path: Path) -> list[str]:
        lines = []
        print("read_lines_with_ARS_faults")
        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                if "ARS faulted" in line or "ARS recovered" in line:
                    lines.append(line.rstrip('\n'))
        return lines

    def extract_datetimes(lines: list[str]) -> tuple[list[datetime], list[datetime]]:
        print("extract_datetimes")
        stop_pattern = re.compile(r"(?<=ARS faulted @)[^;]*")
        start_pattern = re.compile(r"(?<=ARS recovered @).*")

        stops = []
        starts = []

        def get_timestamp_from(string):
            format_string = '%Y-%m-%d %H:%M:%S.%f'

            return datetime.strptime(
                string,
                format_string
            )


        for line in lines:
            stop_match = stop_pattern.search(line)
            if stop_match:
                print(f"stop: {stop_match.group()}")
                dt = get_timestamp_from(stop_match.group())
                stops.append(dt)
                continue  # avoid matching both in one line

            start_match = start_pattern.search(line)
            if start_match:
                print(f"start: {start_match.group()}")
                dt = get_timestamp_from(start_match.group())
                starts.append(dt)

        return stops, starts

    if len(fault_injector_logfiles) > 0:
        for fault_injector_logfile in fault_injector_logfiles:
            relevant_lines = read_lines_with_ARS_faults(fault_injector_logfile)
            stops, starts = extract_datetimes(relevant_lines)
    
            print("-- Stop-Start --")
            for i in range(len(stops)):
                if i >= len(starts):
                    continue

                diff = abs(stops[i] - starts[i])
                print("{} - {} = {}".format(stops[i].time(), starts[i].time(), diff.total_seconds()))
            print("--")

            if "proxy" in fault_injector_logfile.name:
                linestyle = '-'
            else:
                linestyle = '--'

            for d in stops:
                plt.axvline(d, color='orange', linestyle=linestyle)
            for d in starts:
                plt.axvline(d, color='green', linestyle=linestyle)

    print("-- Response times as measured by Locust sorted by value and then time --")
    max_response_times = sorted(response_times, key=response_times.get, reverse=True)[:8]
    for i in sorted(max_response_times):
        print("{} {}".format(i.strftime("%H:%M:%S"), response_times[i]))
    print("--")

    en50136_max_response_time = 30

    print("-- Response times statistics --")
    print("Number of responses: {}".format(len(times)))
    times_above_ten_seconds = list(filter(lambda t: t > 10, times))
    print("Number of faults: {}".format(len(times_above_ten_seconds)))
    times_above_max_response_time = list(filter(lambda t: t > en50136_max_response_time, times))
    print("Response times above requirements: {}".format(len(times_above_max_response_time)))

    print("Min response time: {}".format(min(times)))
    print("---")

    # min_times = min(times)

    # corrected_times = [t - min_times for t in times]
    # plt.plot(dates, corrected_times, 'x', color='gray', label='Response time - Minimum response time')

    # plt.axhline(min_times, color='blue', label='Minimum response time measured')
    #plt.axhline(max(times), color='r', label='Maximum response time measured')

    plt.axhline(en50136_max_response_time, color='r', label='Max. response time allowed')

    # plt.axhline(28, color='orange', label='Expected min fault time')
    # plt.axhline(36, color='orange', label='Expected max fault time')

    # beautify the x-labels
    myFmt = mdates.DateFormatter('%H:%M:%S')
    plt.gca().xaxis.set_major_formatter(myFmt)
    #plt.gca().xaxis.set_major_locator(mdates.SecondLocator(interval=30))
    #plt.gca().xaxis.set_minor_locator(mdates.SecondLocator(interval=10))
    #plt.gca().xaxis.set_minor_formatter(mdates.DateFormatter('%Ss'))
    plt.gcf().autofmt_xdate()

    plt.xlabel('Time')
    plt.ylabel('Response time in s')
    plt.legend(loc='upper left')


def main(
    logfile: Annotated[
        Path,
        typer.Argument(..., help="Path to the log file to analyze", exists=True, readable=True)
    ],
    fault_injector_logfiles: Annotated[
        list[Path],
        typer.Argument(
            help="Zero or more fault injector log files (optional, can pass multiple)",
            exists=True,
            readable=True
        )
    ],
    target_filename_figure: Annotated[
        Optional[Path],
        typer.Option(
            "--output",
            "-o",
            file_okay=True,
            dir_okay=False,
            writable=True,
            resolve_path=True,
            help="Optional path to output file (will be created or overwritten)"
        )
    ] = None
) -> None:
    """Load test plotter - analyze and plot response times from log files."""

    try:
        response_times = readResponseTimesFromLogFile(str(logfile))
        
        if len(response_times) > 0:
            plot_response_times(response_times, fault_injector_logfiles)
        else:
            readMeasurementsFromLogFileAndAppendToList(logfile)
            plt.plot(num_clients, avg_time_allowed, 'y--', label='Average time allowed')
            plt.plot(num_clients, max_time_allowed, 'r--', label='Maximum time allowed')
            # plt.plot(num_clients, min_response_time, label='min')
            plt.plot(num_clients, average_response_time, label='avg')
            plt.plot(num_clients, max_response_time, label='max')

            plt.xlabel('Number of alarm devices')
            plt.ylabel('Response time in s')
            plt.legend(loc='upper left')
            plt.yscale('log')
            plt.ylim(0.001, 1000)
            plt.savefig('Response_times.pdf')
            # plt.grid()
      
        if target_filename_figure is not None:
            plt.savefig(target_filename_figure)
        else:
            plt.show()

    except Exception as e:
        typer.echo(f"Error processing log file: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    typer.run(main)
