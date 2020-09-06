import argparse
import glob
import re
from datetime import datetime
from os.path import join
from typing import Tuple

from Common import get_timestamp_from_string, contains_timestamp_with_ms, dir_path, get_date_from_string


class NumberOfParallelCommandsTracker:
    def __init__(self):
        self.currentParallelCommands = 0

    def process_log_line(self, line: str):
        if "CMD-START" in line:
            self.currentParallelCommands += 1
        elif "CMD-ENDE" in line:
            self.currentParallelCommands -= 1

    def reset(self):
        self.currentParallelCommands = 0


class GSLogConverter:

    def __init__(self):
        self.startedCommands = {}

        self.parallelCommandsTracker = NumberOfParallelCommandsTracker()

    def read(self, path: str):

        from pathlib import Path
        nameOfLogFile = Path(path).name
        targetPath = Path(path) \
            .with_name("Conv_{}".format(get_date_from_string(nameOfLogFile))) \
            .with_suffix(".log")

        print("Writing to ", targetPath)
        targetFile = open(targetPath, mode="w")

        print("Reading from %s" % path)
        with open(path) as logfile:
            counter = 0

            for line in logfile:
                counter = counter + 1
                if counter % 20000 == 0:
                    print("Processed {} entries".format(counter))

                if "CMD-START" in line:
                    (tid, _) = self.process_threadid_and_timestamp(line)
                    self.process_cmd(line, tid)
                elif "CMD-ENDE" in line:
                    (tid, end_time) = GSLogConverter.get_threadid_and_timestamp(line)

                    if tid not in self.startedCommands:
                        print("Command ended without corresponding start log entry")
                        print("in file: ", logfile)
                        print("on line: ", line)
                        print(self.startedCommands)
                        if not args.force:
                            input("Press ENTER to continue...")
                        continue

                    self.startedCommands[tid][
                        "parallelCommandsEnd"] = self.parallelCommandsTracker.currentParallelCommands

                    start_time = self.startedCommands[tid]["time"]

                    execution_time_ms = (end_time - start_time).total_seconds() * 1000

                    self.write_to_target_log(
                        {
                            "receivedAt": end_time,
                            "cmd": self.startedCommands[tid]["cmd"],
                            "parallelRequestsStart": self.startedCommands[tid]["parallelCommandsStart"],
                            "parallelRequestsEnd": self.startedCommands[tid]["parallelCommandsEnd"],
                            "parallelCommandsFinished": self.startedCommands[tid]["parallelCommandsFinished"],
                            "time": int(execution_time_ms)
                        },
                        targetFile
                    )

                    # thread <tid> finished his command,
                    # increment counter of other commands
                    for cmd in self.startedCommands.values():
                        cmd["parallelCommandsFinished"] = cmd["parallelCommandsFinished"] + 1

                    # ...remove from startedCommands
                    self.startedCommands.pop(tid)

                self.parallelCommandsTracker.process_log_line(line)

        if len(self.startedCommands) > 0:
            print("Commands remaining")
            print(self.startedCommands)
            if not args.force:
                input("Press ENTER to continue...")
        self.startedCommands.clear()
        self.parallelCommandsTracker.reset()
        targetFile.close()

    @staticmethod
    def get_threadid_from_line(line: str) -> int:
        tid = re.search(r"\[\d*\]", line).group()
        tid = tid.replace("[", "", 1)
        tid = tid.replace("]", "", 1)
        tid = int(tid)

        return tid

    @staticmethod
    def get_threadid_from_line_optimized(line: str) -> int:
        foundLeftBracket = False
        tidString = []

        for c in line:
            if c == '[':
                foundLeftBracket = True
                continue
            elif c == ']':
                break

            if foundLeftBracket:
                tidString.append(c)

        tidString = ''.join(tidString)
        tid = int(tidString)

        return tid

    @staticmethod
    def get_timestamp_from_line(line: str) -> datetime:
        if contains_timestamp_with_ms(line):
            format_string = '%Y-%m-%d %H:%M:%S.%f'
        else:
            format_string = '%Y-%m-%d %H:%M:%S'

        return datetime.strptime(
            get_timestamp_from_string(line),
            format_string
        )

    @staticmethod
    def write_to_target_log(data, target_file):
        receivedAt = data['receivedAt'].strftime('%Y-%m-%d %H:%M:%S,%f')

        firstPart = f"[{receivedAt:26}] " \
                    f"(PR: {data['parallelRequestsStart']:2}/" \
                    f"{data['parallelRequestsEnd']:2}/" \
                    f"{data['parallelCommandsFinished']:2})"
        secondPart = f"{data['cmd']:35}:"
        thirdPart = f"Response time {data['time']} ms"
        target_file.write(f"{firstPart} {secondPart} {thirdPart}\n")

    @staticmethod
    def write_ARS_CMDs_to_target_log(data, target_file):
        if "ID_REQ_KC_STORE7D3BPACKET" in data["cmd"]:
            GSLogConverter.write_to_target_log(data, target_file)

    @staticmethod
    def get_threadid_and_timestamp(line: str) -> Tuple[int, datetime]:
        # format: [tid] yyyy-MM-dd hh-mm-ss.f

        tid = GSLogConverter.get_threadid_from_line_optimized(line)

        timestamp = GSLogConverter.get_timestamp_from_line(line)

        return tid, timestamp

    def process_threadid_and_timestamp(self, line: str) -> Tuple[int, datetime]:

        tid, timestamp = GSLogConverter.get_threadid_and_timestamp(line)

        self.startedCommands[tid] = {
            "time": timestamp,
            "cmd": None,
            "parallelCommandsStart": self.parallelCommandsTracker.currentParallelCommands,
            "parallelCommandsEnd": 0,
            "parallelCommandsFinished": 0
        }

        return tid, timestamp

    def process_cmd(self, line: str, lastTid: int):
        if "unbekanntes CMD" not in line:
            cmd = re.search(r"ID_\w+", line).group()
        else:
            cmd = "ID_Unknown"

        self.startedCommands[lastTid]["cmd"] = cmd


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert log files '
                                                 'of the GS legacy system '
                                                 'to our custom locust log file format.')
    parser.add_argument('--files', '-f',
                        type=str,
                        nargs='+',
                        help='the paths to the ARS log files')
    parser.add_argument('--directory', '-d',
                        type=dir_path,
                        help='the directory the log files are located in')
    parser.add_argument('--force',
                        action='store_true',
                        help='ignore errors in the log files')

    args = parser.parse_args()

    if args.files is None and args.directory is None:
        parser.print_help()
        exit(1)

    logfilesToConvert = args.files if args.files is not None else []

    if args.directory is not None:
        logfiles = glob.glob(join(args.directory, "Merged_*.log"))
        logfilesToConvert.extend(logfiles)

    # remove duplicates trick
    logfilesToConvert = sorted(set(logfilesToConvert))

    print("Logs to convert: " + str(logfilesToConvert))

    for path in logfilesToConvert:
        converter = GSLogConverter()
        print("Converting ", path)
        converter.read(path)
