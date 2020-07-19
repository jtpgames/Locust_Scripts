import argparse
import re
from datetime import datetime


class ARSLogConverter:
    commandDict = {}

    responseTimes = []

    def read(self, path: str):

        if "koppelcmd" not in path:
            print("koppelcmd should be part of the filename")
            return

        targetPath = path.replace("koppelcmd", "ARS")

        print("Reading source")
        with open(path) as logfile:
            counter = 0

            for firstLine in logfile:
                secondLine = logfile.readline()

                counter = counter + 1
                if counter % 10000 == 0:
                    print("Processed {} entries".format(counter))

                if "CMD-START" in secondLine:
                    tid = self.processFirstLine(firstLine)
                    self.processSecondLine(secondLine, tid)
                elif "CMD-ENDE" in secondLine:
                    tid = self.getThreadIDFromLine(firstLine)
                    end_time = self.getTimeStampFromLine(firstLine)

                    start_time = self.commandDict[tid]["time"]

                    execution_time_ms = (end_time - start_time).total_seconds() * 1000

                    self.responseTimes.append(
                        {
                            "receivedAt": end_time,
                            "cmd": self.commandDict[tid]["cmd"],
                            "time": int(execution_time_ms)
                        })

                    self.commandDict.pop(tid)

        print("Writing to ", targetPath)
        with open(targetPath, mode="w") as targetFile:
            for responseTime in self.responseTimes:
                if "ID_REQ_KC_STORE7D3BPACKET" in responseTime["cmd"]:
                    targetFile.write(
                        "{}\t{}:\t\tResponse time {} ms\n".format(
                            responseTime["receivedAt"].strftime('[%Y-%m-%d %H:%M:%S,%f]'),
                            responseTime["cmd"],
                            responseTime["time"]
                        )
                    )

        self.commandDict.clear()
        self.responseTimes.clear()

    @staticmethod
    def getThreadIDFromLine(line: str) -> int:
        tid = re.search(r"\[\d*\]", line).group()
        tid = tid.replace("[", "")
        tid = tid.replace("]", "")
        tid = int(tid)

        return tid

    @staticmethod
    def getTimeStampFromLine(line: str) -> datetime:
        return datetime.strptime(
            re.search(
                r"(?<=\])\s\d*-\d*-\d*\s\d*:\d*:\d*\.\d*",
                line
            ).group().strip(),
            '%Y-%m-%d %H:%M:%S.%f'
        )

    def processFirstLine(self, line: str) -> int:

        # firstline: format: [tid] yyyy-MM-dd hh-mm-ss.f

        tid = self.getThreadIDFromLine(line)

        time_stamp = self.getTimeStampFromLine(line)

        self.commandDict[tid] = {"time": time_stamp, "cmd": None}

        return tid

    def processSecondLine(self, line: str, lastTid: int):
        cmd = re.search(r"ID_(_|\w)+", line).group()

        self.commandDict[lastTid]["cmd"] = cmd


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert ARS log files to locust log file format.')
    parser.add_argument('files',
                        type=str,
                        nargs='+',
                        help='the paths to the ARS log files')

    args = parser.parse_args()

    for path in args.files:
        converter = ARSLogConverter()
        print("Converting ", path)
        converter.read(path)
