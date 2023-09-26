"""
Command group Fleet
"""

import sys
import yaml
from tabulate import tabulate

from ..endpoints import Endpoints
from ..kuberos_config import KuberosConfig
from .base import CommandGroupBase, KubeROSBaseCompleter


FLEET_HELP = '''
KubeROS CLI [fleet] command group

Usage:
    kuberos fleet <command> [fleet_name] [-args]
    
Commands:
    create       Build a new fleet (Fleet name must be unique)
                 -f --file: manifest file path
    
    list         List all fleets
    
    info         Get a fleet by name
    
    delete       Remove a fleet from Kuberos (remove all kuberos labels)
    
    update       Update a fleet with fleet description
'''


class FleetCompleter(KubeROSBaseCompleter):
    """
    Get the list of cluster names from the API server or cached data
    """

    def get_data_for_completion(self):
        _, data = self.call_api()
        return [item['fleet_name'] for item in data]


class FleetCommandGroup(CommandGroupBase):
    """
    Command group [fleet]
    """

    COMMAND_LIST = ['list', 'create', 'delete', 'info']

    RESOURCE_URL = 'api/v1/fleet/fleets_name_list'

    def __init__(self, subparsers) -> None:
        super().__init__(subparsers, 'fleet')

        self.init_subcommand_create()
        self.init_subcommand_info()
        self.init_subcommand_delete()


    def init_subcommand_create(self):
        """
        Initialize the subcommand <create>
        """
        parser = self.commands['create']
        parser.add_argument(
            '-f', '--file', help='File path of cluster registration')

    def init_subcommand_info(self):
        """
        Initialize the subcommand <info>
        """
        parser = self.commands['info']
        parser.add_argument('fleet_name', help="Fleet name").completer = FleetCompleter(
            resource_url=self.RESOURCE_URL
        )

    def init_subcommand_delete(self):
        """
        Initialize the subcommand <delete>
        """
        parser = self.commands['delete']
        parser.add_argument('fleet_name',
                            help="Fleet name").completer = FleetCompleter(
                                resource_url=self.RESOURCE_URL)

    def create(self, *args):
        """
        Add new cluster to KubeROS
        """
        parser = self.commands['create']
        parsed_args = parser.parse_args(args)

        file_path = parsed_args.file
        config = KuberosConfig.get_current_config()

        url = f"{config['server']}/{Endpoints.FLEET}"
        try:
            with open(file_path, 'r') as f:
                files = {'fleet_manifest': f}
                success, res = self.call_api(
                    'POST',
                    url,
                    files=files,
                    data={
                        'create': True,
                    },
                    auth_token=config['token'],
                )
                if success:
                    print("Successfully create fleet")
                else:
                    print('ERROR')

        except FileNotFoundError:
            print(f'Fleet manifest file: {parsed_args.file} not found.')
            sys.exit(1)

    @staticmethod
    def parse_cluster_registration_yaml(yaml_file):
        """
        Parse the cluster registration yaml file
        Args:
            yaml_file (str): path_to_yaml_file
        Returns:
            dict: cluster registreation dict
        """
        try:
            with open(yaml_file, 'r') as f:
                manifest = yaml.safe_load(f)
                meta_data = manifest['metadata']
                cluster = {
                    'cluster_name': meta_data['name'],
                    'distribution': meta_data['distribution'],
                    'host_url': meta_data['apiServer'],
                    'ca_cert': meta_data['caCert'],
                    'service_token_admin': meta_data['serviceTokenAdmin'],
                }
                return cluster
        except FileNotFoundError:
            print(f'Cluster registration file: {yaml_file} not found.')
            sys.exit(1)

    def info(self, *args):
        """
        Retrieve the status of a cluster by cluster name
        Example: kuberos cluster info <cluster_name>
        """
        parser = self.commands['info']
        parsed_args = parser.parse_args(args)

        config = KuberosConfig.get_current_config()
        cluster_url = f"{config['server']}/{Endpoints.FLEET}{parsed_args.fleet_name}/"
        success, response = self.call_api('GET',
                                          cluster_url,
                                          auth_token=config['token'],
                                          )
        if success and response['status'] == 'success':
            data = response['data']
            print(f"Fleet Name: {data['fleet_name']}")
            print(f"Healthy: {data['is_entire_fleet_healthy']}")
            print(f"Fleet status: {data['fleet_status']}")
            print(f"Alive Age: {data['alive_age']}")
            print(f"Main Cluster: {data['k8s_main_cluster_name']}")
            print(f"Description: {data['description']}")
            print(f"Created since: {data['created_since']}")
            print('='*40)
            data_to_display = [{
                    'Robot Name': item['robot_name'],
                    'Id': item['robot_id'],
                    'Hostname': item['cluster_node_name'],
                    'Computer Group': item['onboard_comp_group'],
                    'Reachable': item['is_fleet_node_alive'],
                    'Status': item['status'],
                    'Shared Resource': item['shared_resource'],
                } for item in data['fleet_node_set']]
            table = tabulate(data_to_display, headers="keys", tablefmt='plain')
            print(table)
        else:
            print("ERROR")

    def list(self):
        """
        List all clusters that the user has access to
        Example: kuberos cluster list
        """
        config = KuberosConfig.get_current_config()
        success, response = self.call_api('GET',
                                          f"{config['server']}/{Endpoints.FLEET}",
                                          auth_token=config['token'])
        if success:
            data = response['data']
            data_to_display = [{
                'Name': item['fleet_name'],
                'Status': item['fleet_status'],
                'Alive Age': item['alive_age'],
                'Healthy': item['is_entire_fleet_healthy'],
                'Main Cluster': item['k8s_main_cluster_name'],
                'Created since': item['created_since'],
            } for item in data]
            table = tabulate(data_to_display, headers="keys", tablefmt='plain')
            print(table)
        else:
            print('error')


    def delete(self, *args):
        """
        Delete the cluster by cluster name
        """
        parser = self.commands['delete']
        parsed_args = parser.parse_args(args)
        config = KuberosConfig.get_current_config()
        url = f"{config['server']}/{Endpoints.FLEET}{parsed_args.fleet_name}/"

        success, response = self.call_api('DELETE',
                                          url,
                                          auth_token=config['token'])
        if success:
            print(response)
            print(f"Successfully delete cluster: {parsed_args.fleet_name}")
        else:
            print('[Error] Failed to delete cluster')

    def print_help(self):
        """
        Print help message
        """
        print(FLEET_HELP)
