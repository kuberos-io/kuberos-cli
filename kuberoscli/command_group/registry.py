"""
Command group Container Registry
"""

import sys
import yaml
from tabulate import tabulate

from ..endpoints import Endpoints
from ..kuberos_config import KuberosConfig
from .base import CommandGroupBase, KubeROSBaseCompleter
from .cluster import ClusterCompleter


REGISTRY_HELP = '''
KubeROS CLI [registry] command group

Usage:
    kuberos registry <command> [token_name] [-args]
    
Commands:
    create       Add a new registry token (name must be unique)
                 -f --file: manifest file path
    
    attach       Attach a registry token to a cluster
                 token_name (Positional required): name of the token
                 cluster_name (Positional required): cluster name
                 -n --namespace (Optional): namespace of the cluster, default: ros-default
    
    list         List all container registries and token
    
    info         Get the info of a container registry
    
    delete       Remove the container registry from KubeROS
'''


class RegistryTokenCompleter(KubeROSBaseCompleter):
    """
    Get the list of cluster names from the API server or cached data
    """

    def get_data_for_completion(self):
        _, data = self.call_api()
        return [item['name'] for item in data]


class RegistryCommandGroup(CommandGroupBase):
    """
    Command group [registry]
    """

    COMMAND_LIST = ['create', 'attach', 'list', 'info', 'delete']

    RESOURCE_URL = 'api/v1/cluster/registry_token_name_list/'

    def __init__(self, subparsers) -> None:
        super().__init__(subparsers, 'registry')

        self.init_subcommand_create()
        self.init_subcommand_attach()
        self.init_subcommand_info()
        self.init_subcommand_delete()

    def init_subcommand_create(self):
        """
        Initialize the subcommand <create>
        """
        parser = self.commands['create']
        parser.add_argument(
            '-f', '--file',
            required=True,
            help='Path of the registry token yaml file')

    def init_subcommand_attach(self):
        """
        Initialize the subcommand <attach>
        """
        parser = self.commands['attach']
        parser.add_argument('token_name',
                            help="Token name").completer = RegistryTokenCompleter(
            resource_url=self.RESOURCE_URL
        )
        parser.add_argument('cluster_name',
                            help="Cluster name").completer = ClusterCompleter(
            resource_url='api/v1/cluster/clusters_name_list'
        )
        parser.add_argument(
            '-n', '--namespace', help='Namespace of the cluster, default: ros-default')

    def init_subcommand_info(self):
        """
        Initialize the subcommand <info>
        """
        parser = self.commands['info']
        parser.add_argument('token_name',
                            help="Token name").completer = RegistryTokenCompleter(
            resource_url=self.RESOURCE_URL
        )

    def init_subcommand_delete(self):
        """
        Initialize the subcommand <delete>
        """
        parser = self.commands['delete']
        parser.add_argument('token_name',
                            help="Token name").completer = RegistryTokenCompleter(
                                resource_url=self.RESOURCE_URL)

    def create(self, *args):
        """
        Add new registry token to KubeROS
        """
        parser = self.commands['create']
        parsed_args = parser.parse_args(args)

        file_path = parsed_args.file
        config = KuberosConfig.get_current_config()

        url = f"{config['server']}/{Endpoints.REGISTRY_TOKEN}"
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                registry_token = yaml.safe_load(file)
                meta_data = registry_token['metadata']
                success, res = self.call_api(
                    'POST',
                    url,
                    data={
                        'name': meta_data['name'],
                        'user_name': meta_data['userName'],
                        'registry_url': meta_data['registryUrl'],
                        'token': meta_data['token'],
                        'description': meta_data['description'],
                    },
                    auth_token=config['token'],
                )
                if success:
                    print("Successfully added new registry token")
                    print(res)
                else:
                    print('ERROR')

        except FileNotFoundError:
            print(
                f'Container registry token file: {parsed_args.file} not found.')
            sys.exit(1)

    def attach(self, *args):
        """
        Attach the registry token to a cluster
        Example: kuberos registry attach <token_name> <cluster_name> -n <namespace>
        """
        parser = self.commands['attach']
        parsed_args = parser.parse_args(args)

        config = KuberosConfig.get_current_config()
        url = f"{config['server']}/{Endpoints.REGISTER_TOKEN_TO_CLUSTER}"
        success, response = self.call_api(
            'POST',
            url,
            data={
                'token_name': parsed_args.token_name,
                'cluster_name': parsed_args.cluster_name,
                'namespace': parsed_args.namespace if parsed_args.namespace else 'ros-default',
            },
            auth_token=config['token'],
        )
        if success:
            print(response)
        else:
            print('ERROR')
            print(response)

    def info(self, *args):
        """
        Retrieve the info of a registry token
        Example: kuberos registry info <token_name>
        """
        parser = self.commands['info']
        parsed_args = parser.parse_args(args)

        config = KuberosConfig.get_current_config()
        url = f"{config['server']}/{Endpoints.REGISTRY_TOKEN}{parsed_args.token_name}/"
        success, response = self.call_api('GET',
                                          url,
                                          auth_token=config['token'],
                                          )

        if success and response['status'] == 'success':
            data = response['data']
            print(f"Name: {data['name']}")
            print(f"Registry: {data['registry_url']}")
            print(f"User name: {data['user_name']}")
            print(f"Description: {data['description']}")
        else:
            print("ERROR")

    def list(self):
        """
        List all registry tokens that managed by KubeROS
        Example: kuberos registry list
        """
        config = KuberosConfig.get_current_config()
        success, response = self.call_api('GET',
                                          f"{config['server']}/{Endpoints.REGISTRY_TOKEN}",
                                          auth_token=config['token'])
        if success:
            data = response['data']
            data_to_display = [{
                'name': item['name'],
                'uuid': item['uuid'],
                'user name': item['user_name'],
                'registry': item['registry_url'],
                # 'description': item['description'],
            } for item in data]
            table = tabulate(data_to_display, headers="keys", tablefmt='plain')
            print(table)
        else:
            print('error')
            print(response)

    def delete(self, *args):
        """
        Delete the registry token from KubeROS and all the clusters
        """
        parser = self.commands['delete']
        parsed_args = parser.parse_args(args)
        config = KuberosConfig.get_current_config()
        url = f"{config['server']}/{Endpoints.REGISTRY_TOKEN}{parsed_args.token_name}/"

        success, response = self.call_api('DELETE',
                                          url,
                                          auth_token=config['token'])
        if success:
            print(response)
            print(
                f"Successfully delete registry token: {parsed_args.token_name}")
        else:
            print('[Error] Failed to delete the registry token')

    def print_help(self):
        """
        Print help message
        """
        print(REGISTRY_HELP)
