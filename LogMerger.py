import argparse
import glob
from os.path import join
from pathlib import Path

from itertools import groupby

from Common import dir_path, get_timestamp_from_string, get_date_from_string


class LogMerger:
    @staticmethod
    def aggregate(group: str, similar_logfile_paths: list):
        def read_files(*filenames):
            counter = 0
            for filename in filenames:
                print("Reading ", filename)
                with open(filename, 'r') as file_obj:
                    for line in file_obj:
                        counter = counter + 1
                        if counter % 20000 == 0:
                            print("Processed {} entries".format(counter))

                        yield line

        def merge(*seqs):
            return sorted(read_files(*seqs), key=get_timestamp_from_string)

        logfiles_directory = Path(similar_logfile_paths[0]).parent
        targetPath = join(logfiles_directory, "Merged_%s.log" % group)

        print("Merging %s" % similar_logfile_paths)

        result_file = merge(*similar_logfile_paths)

        print("Merged %i log entries" % len(result_file))

        print("Writing to ", targetPath)
        with open(targetPath, mode="w") as targetFile:
            counter = 0
            for line in result_file:
                if counter % 20000 == 0:
                    print("Written {} entries".format(counter))
                targetFile.write(line)
                counter += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Aggregate log files from different sources to a single log file per day.')
    parser.add_argument('--directory', '-d',
                        type=dir_path,
                        help='the directory the log files are located in')

    args = parser.parse_args()

    if args.directory is None:
        parser.print_help()
        exit(1)

    logfiles = glob.glob(join(args.directory, "*.log"))

    # group the files by the date in the file name
    data = sorted(logfiles, key=get_date_from_string)
    for group, logfile in groupby(data, key=get_date_from_string):
        # omit the merged logs created by this script
        logfilesToAggregate = filter(lambda f: "Merged_" not in f, list(logfile))
        LogMerger.aggregate(group, list(logfilesToAggregate))
