import argparse
import glob
import os
from os.path import join

from Common import dir_path


def merge_first_and_second_line(path: str):
    if "koppelcmd" not in path:
        print("koppelcmd should be part of the filename")
        return

    target_path = path.replace("koppelcmd", "ARS")

    print("Converting ", path)
    with open(path) as logfile:
        with open(target_path, mode="w") as targetFile:
            counter = 0

            for firstLine in logfile:
                second_line = logfile.readline()

                counter = counter + 2
                if counter % 10000 == 0:
                    print("Processed {} entries".format(counter))

                targetFile.write("{}\t{}\n".format(firstLine.strip(), second_line.strip()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert ARS log files to common log file format.')
    parser.add_argument('--files', '-f',
                        type=str,
                        nargs='+',
                        help='the paths to the ARS log files')
    parser.add_argument('--directory', '-d',
                        type=dir_path,
                        help='the directory the log files are located in')

    args = parser.parse_args()

    if args.files is None and args.directory is None:
        parser.print_help()
        exit(1)

    logfilesToConvert = args.files if args.files is not None else []

    if args.directory is not None:
        logfiles = glob.glob(join(args.directory, "koppelcmd*.log"))
        logfilesToConvert.extend(logfiles)

    print("Logs to convert: " + str(logfilesToConvert))

    for path in logfilesToConvert:
        merge_first_and_second_line(path)
        os.remove(path)
