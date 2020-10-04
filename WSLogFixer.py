import argparse
import glob
import os
from os import SEEK_SET
from os.path import join

from Common import dir_path


def peek_line(f):
    line = f.readline()
    count = len(line) + 1
    f.seek(f.tell() - count, SEEK_SET)
    return line


def fix_log(path: str):
    """
    Fixes two things in the logs:
    1. Fixes encoding by using latin-1 encoding, as explained in http://python-notes.curiousefficiency.org/en/latest/python3/text_file_processing.html#files-in-an-ascii-compatible-encoding-best-effort-is-acceptable
    2. Fixes line breaks within one log entry and merges those lines together
    :param path: Path to the log file
    """
    if "WSCmd" not in path:
        print("WSCmd should be part of the filename")
        return

    target_path = path.replace("WSCmd", "WSCmd_f")

    print("Converting ", path)
    with open(path, encoding="latin-1") as logfile:
        with open(target_path, mode="w") as targetFile:
            counter = 0

            first_line = logfile.readline()
            while first_line:
                second_line = peek_line(logfile)

                counter = counter + 1
                if counter % 10000 == 0:
                    print("Processed {} entries".format(counter))

                if first_line.startswith('[') and second_line.startswith('['):
                    targetFile.write(first_line)
                else:
                    targetFile.write("{}{}\n".format(first_line.rstrip('\n'),
                                                     second_line.strip()))
                    logfile.readline()  # consume second line

                first_line = logfile.readline()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert WS log files to common log file format.')
    parser.add_argument('--files', '-f',
                        type=str,
                        nargs='+',
                        help='the paths to the WS log files')
    parser.add_argument('--directory', '-d',
                        type=dir_path,
                        help='the directory the log files are located in')

    args = parser.parse_args()

    if args.files is None and args.directory is None:
        parser.print_help()
        exit(1)

    logfilesToConvert = args.files if args.files is not None else []

    if args.directory is not None:
        logfiles = glob.glob(join(args.directory, "WSCmd*.log"))
        logfilesToConvert.extend(logfiles)

    print("Logs to convert: " + str(logfilesToConvert))

    for path in logfilesToConvert:
        fix_log(path)
        os.remove(path)
