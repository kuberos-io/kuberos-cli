#!/usr/bin/env python3

import argparse
import os
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.convert import message_to_csv
from rosidl_runtime_py.utilities import get_message
import rosbag2_py

def bag_to_df(bagfile):

    def get_rosbag_options(path, serialization_format='cdr'):
        storage_options = rosbag2_py.StorageOptions(uri=path, storage_id='sqlite3')

        converter_options = rosbag2_py.ConverterOptions(
            input_serialization_format=serialization_format,
            output_serialization_format=serialization_format)

        return storage_options, converter_options

    storage_options, converter_options = get_rosbag_options(bagfile)

    reader = rosbag2_py.SequentialReader()
    reader.open(storage_options, converter_options)

    topic_types = reader.get_all_topics_and_types()

    # Create a map for quicker lookup
    type_map = {topic_types[i].name: topic_types[i].type for i in range(len(topic_types))}

    # Set filter for topic
    storage_filter = rosbag2_py.StorageFilter(topics=['/task_status'])
    reader.set_filter(storage_filter)

    data = ''
    while reader.has_next():
        (topic, msgdata, t) = reader.read_next()
        msg_type = get_message(type_map[topic])
        msg = deserialize_message(msgdata, msg_type)
        data += message_to_csv(msg) + '\n'
    return data

def get_rosbag_dirs(parent_dir, rosbag_dirs):
    for path, dirs, _ in os.walk(parent_dir):
        for d in dirs:
            current = os.path.join(path, d)
            if any(fname.endswith('.db3') for fname in os.listdir(current)):
                rosbag_dirs.append(current)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description='create dataframes from rosbags')

    argparser.add_argument(
        'parent-dir',
        type=str,
        default='.',
        help='parent directory containing the bag files')

    args = argparser.parse_args()

    rosbag_dirs = []
    get_rosbag_dirs(args.parent_dir, rosbag_dirs)

    for bag_path in rosbag_dirs:
        print('=== Processing bagfile: ', bag_path)
        output_path = bag_path + '.csv'
        print('=== Writing output to: ', output_path)
        with open(output_path, 'w') as f:
            f.write(bag_to_df(bag_path))