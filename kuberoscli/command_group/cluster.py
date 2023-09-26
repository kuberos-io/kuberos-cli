"""
Command group Cluster
"""

import sys
import yaml
from tabulate import tabulate

from ..endpoints import Endpoints
from ..kuberos_config import KuberosConfig
from .base import CommandGroupBase, KubeROSBaseCompleter


CLUSTER_HELP = '''
KubeROS CLI [cluster] command group

Usage:
    kuberos cluster <command> [-args]
    
Commands:
    create       Register a new cluster to Kuberos 
                 -f --file: cluster registration yaml file path

    list         List all clusters
    
    info         Get cluster info by cluster name
                 -u --usage: get cluster resource utilization
                 -s --sync:  synchronize immediatelly
    
    update       Update a cluster inventory description
                 -f --file:  cluster inventory yaml file path
                 
    delete       Remove the cluster from KubeROS
'''


class ClusterCompleter(KubeROSBaseCompleter):
    """
    Get the list of cluster names from the API server or cached data
    """

    def get_data_for_completion(self):
        _, data = self.call_api()
        return [item['cluster_name'] for item in data]


class ClusterCommandGroup(CommandGroupBase):
    """
    Command group [cluster]
    """

    COMMAND_LIST = ['list', 'create', 'delete', 'info', 'update']

    RESOURCE_URL = 'api/v1/cluster/clusters_name_list'

    def __init__(self, subparsers) -> None:
        super().__init__(subparsers, 'cluster')

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
        parser.add_argument('cluster_name',
                            help="Name of the cluster").completer = ClusterCompleter(
                                resource_url=self.RESOURCE_URL)
        parser.add_argument('-s', '--sync', action='store_true',
                            help='Synchronize the cluster with Kuberos')
        parser.add_argument('-u', '--usage', action='store_true',
                            help='Get current resource usage')

    def init_subcommand_delete(self):
        """
        Initialize the subcommand <delete>
        """
        parser = self.commands['delete']
        parser.add_argument('cluster_name',
                            help="Name of the cluster").completer = ClusterCompleter(
                                resource_url=self.RESOURCE_URL)

    def create(self, *args):
        """
        Add new cluster to KubeROS
        """
        parser = self.commands['create']
        parsed_args = parser.parse_args(args)

        cluster_data = self.parse_cluster_registration_yaml(parsed_args.file)
        ca_file_path = cluster_data.pop('ca_cert')

        config = KuberosConfig.get_current_config()
        url = f"{config['server']}/{Endpoints.CLUSTER}"
        try:
            with open(ca_file_path, 'r') as f:
                files = {'ca_crt_file': f}
                success, res = self.call_api(
                    'POST',
                    url,
                    files=files,
                    data=cluster_data,
                    auth_token=config['token'],
                )
                if success:
                    print("Successfully create cluster")
                else:
                    print('ERROR')

        except FileNotFoundError:
            print(f'CA cert file: {ca_file_path} not found.')
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
        cluster_url = f"{config['server']}/{Endpoints.CLUSTER}{parsed_args.cluster_name}/"
        success, response = self.call_api('GET',
                                          cluster_url,
                                          auth_token=config['token'],
                                          json_data={
                                              'sync': str(parsed_args.sync),
                                              'get_usage': str(parsed_args.usage),
                                          })
        if success:
            if response['status'] == 'failed':
                print("Retrieve cluster status failed.")
                print("Errors: ")
                print(response['errors'])
                sys.exit(1)

            data = response['data']
            print('\n')
            print(f"Cluster Name: {data['cluster_name']}")
            print(f"API Server: {data['host_url']}")
            print(f'Alive Age: {data["alive_age"]}')
            print(f'Since Last Sync: {data["last_sync_since"]}')
            print('\n')
            # display onboard device
            onboard_devices = []
            edge_nodes = []
            control_plane_nodes = []
            unassigned_nodes = []
            resource_usage = []

            for node in data['cluster_node_set']:
                # onboard computers
                if node['kuberos_role'] == 'onboard':
                    fleet_name = node.get('assigned_fleet_name', 'Unknown')
                    if not fleet_name:
                        fleet_name = 'N/A'

                    onboard_devices.append(
                        {
                            'ROBOT_NAME': node.get('robot_name', None),
                            'HOSTNAME': node['hostname'],
                            'DEVICE_GROUP': node['device_group'],
                            'IS_ALIVE': node['is_alive'],
                            'AVAILABLE': node['is_available'],
                            'FLEET': fleet_name,
                            'PERIPHERALS': node.get('peripheral_device_name_list', None), })

                # Edge nodes (on-premise)
                elif node['kuberos_role'] == 'edge':
                    edge_nodes.append({
                        'HOSTNAME': node['hostname'],
                        'GROUP': node.get('resource_group', None),
                        'SHARED RESOURCE': node.get('is_shared', None),
                        'IS_ALIVE': node['is_alive'],
                        'AVAILABLE': node['is_available'],
                        'REACHABLE': node['is_alive']})

                # unassigned nodes
                elif node['kuberos_role'] == 'unassigned':
                    unassigned_nodes.append({
                        'HOSTNAME': node['hostname'],
                        'ROLE': node['kuberos_role'],
                        'REGISTERED': node['kuberos_registered'],
                        'IS_ALIVE': node['is_alive'],
                        'AVAILABLE': node['is_available'],
                        'REACHABLE': node['is_alive'], })

                # control plane nodes
                elif node['kuberos_role'] == 'control_plane':
                    control_plane_nodes.append({
                        'HOSTNAME': node['hostname'],
                        'ROLE': node['kuberos_role'],
                        'REGISTERED': node['kuberos_registered'],
                        'IS_ALIVE': node['is_alive'],
                        'AVAILABLE': node['is_available'],
                        'REACHABLE': node['is_alive'], })

                # resoruce usage and capacity
                use = node['get_usage']
                cap = node['get_capacity']
                display_usage_conditions = [
                    use['cpu'] > 0,
                    use['memory'] > 0,
                    use['storage'] > 0,
                ]
                if all(display_usage_conditions):
                    resource_usage.append({
                        'HOSTNAME': node['hostname'],
                        'CPU (Cores)': f"{use['cpu']:.2f}/{cap['cpu']} ({use['cpu']/cap['cpu']*100:.1f}%)",
                        'Memory (Gb)': f"{use['memory']:.2f}/{cap['memory']:.1f} ({use['memory']/cap['memory']*100:.1f}%)",
                        # 'Storage (Gb)': f"{use['storage']:.2f}/{cap['storage']:.1f} ({use['storage']/cap['storage']*100:.1f}%)"
                        'Storage (Gb)': f"N/A/{cap['storage']:.1f}"
                    })

            # display data
            num_of_single_dash = 80
            if len(onboard_devices) > 0:
                print('Robot Onboard Computers')
                print('-' * num_of_single_dash)
                table = tabulate(
                    onboard_devices, headers="keys", tablefmt='plain')
                print(table)
                print('\n')
            if len(edge_nodes) > 0:
                print('Edge Nodes')
                print('-' * num_of_single_dash)
                table = tabulate(edge_nodes, headers="keys", tablefmt='plain')
                print(table)
                print('\n')
            if len(unassigned_nodes) > 0:
                print('Unassigned Nodes')
                print('-' * num_of_single_dash)
                table = tabulate(unassigned_nodes,
                                 headers="keys", tablefmt='plain')
                print(table)
                print('\n')
            if len(control_plane_nodes) > 0:
                print('Control Plane Nodes')
                print('-' * num_of_single_dash)
                table = tabulate(control_plane_nodes,
                                 headers="keys", tablefmt='plain')
                print(table)
                print('\n')

            # print resource usages
            if all(display_usage_conditions):
                print('Resource Usages')
                print('-' * num_of_single_dash)
                table = tabulate(
                    resource_usage, headers="keys", tablefmt='plain')
                print(table)
                print('\n')
        else:
            print('error')

    def list(self):
        """
        List all clusters that the user has access to
        Example: kuberos cluster list
        """
        config = KuberosConfig.get_current_config()
        success, response = self.call_api('GET',
                                          f"{config['server']}/{Endpoints.CLUSTER}",
                                          auth_token=config['token'])
        if success:
            data = response['data']
            data_to_display = [{
                'Cluster name': item['cluster_name'],
                'Status': item['cluster_status'],
                'Alive age': item["alive_age"],
                'Last sync': item['last_sync_since'],
                'Dist.': item['distribution'],
                'Env.': item['env_type'],
                'API server': item['host_url'],
            } for item in data]

            table = tabulate(data_to_display, headers="keys", tablefmt='plain')
            print(table)
        else:
            print('[Error] Failed to list clusters')

    def delete(self, *args):
        """
        Delete the cluster by cluster name
        """
        parser = self.commands['delete']
        parsed_args = parser.parse_args(args)
        config = KuberosConfig.get_current_config()
        url = f"{config['server']}/{Endpoints.CLUSTER}{parsed_args.cluster_name}/"

        success, response = self.call_api('DELETE',
                                          url,
                                          auth_token=config['token'])
        if success:
            print(response)
            print(f"Successfully delete cluster: {parsed_args.cluster_name}")
        else:
            print('[Error] Failed to delete cluster')

    def print_help(self):
        """
        Print help text
        """
        print(CLUSTER_HELP)
