#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

# Copyright 2023 Yongzhou Zhang
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sys
import argparse
import argcomplete

# KuberosCLI
from kuberoscli.command_group.cluster import ClusterCommandGroup
from kuberoscli.command_group.fleet import FleetCommandGroup
from kuberoscli.command_group.deploy import DeployCommandGroup
from kuberoscli.command_group.config import ConfigCommandGroup
from kuberoscli.command_group.batchjob import BatchJobCommandGroup
from kuberoscli.command_group.registry import RegistryCommandGroup


CLI_HELP_SUMMARY = '''
KubeROS Command Line Tool

Usage:
    kuberos <command_group> <command> [name] [-args]
    
    Call kuberos <command_group> -h for more detailed usages.
    Example: check the deployment info
             kuberos deploy info <deployment_name>
    
Command Groups:

    deploy       Deploy, check, delete the ROS2 applications
    
    job          create, check, stop, delete a BatchJob
    
    apply        General command to create resources in any supported types
    
    cluster      Manage the clusters (create, list, update, info, delete)
    
    fleet        Manage the fleets (create, list, update, info, delete)
    
    config       Manage the context of the Kuberos CLI (login, switch context, etc.)
    
    registry     Manage the container registry (token, repository)
'''


class KuberosCli:
    """
    Command line tool for KubeROS
    """

    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(
            description="KubeROS Command Line Tool")

        group_subparsers = self.parser.add_subparsers(dest='group',
                                                      help='Command group to execute')

        # Add subparsers for each command group
        self.groups = {}
        self.groups.update({
            'deploy': DeployCommandGroup(subparsers=group_subparsers),
            'job': BatchJobCommandGroup(subparsers=group_subparsers),
            'cluster': ClusterCommandGroup(subparsers=group_subparsers),
            'fleet': FleetCommandGroup(subparsers=group_subparsers),
            'registry': RegistryCommandGroup(subparsers=group_subparsers),
            'config': ConfigCommandGroup(subparsers=group_subparsers),
        })

        argcomplete.autocomplete(self.parser)
        args = self.parser.parse_args(sys.argv[1:2])

        # dispatch to the corresponding command group
        if not args.group in self.groups.keys():
            self.print_help()
            sys.exit(1)
        else:
            self.groups[args.group].run(*sys.argv[2:])

    def print_help(self):
        """
        Print the help message
        """
        print(CLI_HELP_SUMMARY)


def main():
    KuberosCli()


if __name__ == "__main__":
    main()
