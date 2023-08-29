#!/usr/bin/env python3

import os
import argparse

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description='create dataframes from rosbags')
    argparser.add_argument('data-dir',type=str,default='.',help='directory containing the csv files')

    args = argparser.parse_args()

    csv_files = []
    for f in os.listdir(args.data_dir):
        if f.endswith(".csv"):
            csv_files.append(f)
    
    for csv in csv_files:
        start_time = None
        end_time = None
        with open(os.path.join(args.data_dir, csv), 'r') as f:
            for line in f.readlines():
                if "Start navigating" in line:
                    start_time = line.split(";")[0]
                elif "Navigation finished: Success" in line:
                    end_time = line.split(";")[0]
        if start_time and end_time:
            diff_ns = int(end_time) - int(start_time)
            diff_s = diff_ns / 10**9
            print(f"{csv}: {diff_s}")
        else:
            print(f"{csv}: N/A")