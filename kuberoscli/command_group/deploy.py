"""
Command group Deploy
"""

import sys
import yaml
from tabulate import tabulate

from ..endpoints import Endpoints
from ..kuberos_config import KuberosConfig
from .base import CommandGroupBase, KubeROSBaseCompleter


DEPLOY_HELP = '''
KubeROS CLI [deploy] command group

Usage:
    kuberos deploy <command> [deployment_name] [-args]
    
Commands:
    create       Deploy an ROS2 application from manifest file
                 -f --file: manifest file path
    
    list         List all deployments
    
    info         Display the status of the deployment request
    
    delete       Delete deployed application via deployment name
    
    upgrade      Upgrade an existing deployment -> TODO
    
    check        Check the deployment request -> TODO
'''


class DeployCompleter(KubeROSBaseCompleter):
    """
    Get the list of deployment names from the API server or cached data
    """

    def get_data_for_completion(self):
        _, data = self.call_api()
        return [item['name'] for item in data]


class DeployCommandGroup(CommandGroupBase):
    """
    Command group [deploy]
    """

    COMMAND_LIST = ['list', 'create', 'delete', 'info']

    RESOURCE_URL = 'api/v1/deployment/deployments_name_list'

    def __init__(self, subparsers) -> None:
        super().__init__(subparsers, 'deploy')

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
        parser.add_argument('deployment_name',
                            help="Name of the cluster").completer = DeployCompleter(
                                resource_url=self.RESOURCE_URL)

    def init_subcommand_delete(self):
        """
        Initialize the subcommand <delete>
        """
        parser = self.commands['delete']
        parser.add_argument('deployment_name',
                            help="Name of the cluster").completer = DeployCompleter(
                                resource_url=self.RESOURCE_URL)

    def create(self, *args):
        """
        Add new cluster to KubeROS
        """
        parser = self.commands['create']
        parsed_args = parser.parse_args(args)

        config = KuberosConfig.get_current_config()

        try:
            with open(parsed_args.file, "r") as yaml_file:

                deploy_content = yaml.safe_load(yaml_file)
                rosparam_yamls = self.load_yaml_files_from_parammap(
                    deploy_content)

                # call api server
                _, response = self.call_api(
                    'POST',
                    f"{config['server']}/{Endpoints.DEPLOYING}",
                    json_data={
                        'deployment_manifest': deploy_content,
                        'rosparam_yamls': rosparam_yamls
                    },
                    auth_token=config['token']
                )
                print(response)

        except FileNotFoundError:
            print(
                f'Deployment description file: {parsed_args.file} not found.')
            sys.exit(1)

    @staticmethod
    def load_yaml_files_from_parammap(deploy_content: dict):
        """
        Load the yaml files from the rosParamMap

        Args:
            deploy_content (dict): Deployment manifest
        Returns:
            list of dict: 
                {
                    'name': paramete map name,
                    'type': 'yaml',
                    'content': {
                        'ros parameter file name': 'file content'
                    }
                }
        """
        parammap = deploy_content.get('rosParamMap', None)
        if not parammap:
            return []

        param_files = []
        for item in parammap:
            if item['type'] == 'yaml':
                try:
                    with open(item['path'], 'r') as yaml_file:
                        # read the file content, don't parse it to dict
                        param_files.append({
                            'name': item['name'],
                            'type': 'yaml',
                            'content': {
                                item['name']: yaml_file.read()
                            },
                        })
                except FileNotFoundError:
                    print(f"Parameter file: {item['path']} not found.")
                    sys.exit(1)
                except KeyError:
                    print(
                        f"Parameter file path in {item['name']} is not specified.")
                    sys.exit(1)

        return param_files

    def info(self, *args):
        """
        Retrieve the status of a cluster by cluster name
        Example: kuberos cluster info <cluster_name>
        """
        parser = self.commands['info']
        parsed_args = parser.parse_args(args)

        config = KuberosConfig.get_current_config()
        resource_url = f"{config['server']}/{Endpoints.DEPLOYMENT}{parsed_args.deployment_name}/"
        success, res = self.call_api('GET',
                                     resource_url,
                                     auth_token=config['token'])
        if res['status'] == 'success':

            data = res['data']

            # meta info
            print(f"Deployment Name: {data['name']}")
            print(f"Status: {data['status']}")
            print(f"Fleet: {data['fleet_name']}")
            print(f"Running Since: {data['running_since']}")

            # dep jobs summary
            num_of_single_dash = 60
            print('Deployment Jobs Summary')
            print('-' * num_of_single_dash)
            dep_job_set = data['deployment_job_set']
            data_to_display = [{
                'Robot Name': job['robot_name'],
                'Job Phase': job['job_phase'],
                'Pods': len(job['all_pods_status']),
                'Services': len(job['all_svcs_status']),
            } for job in dep_job_set]
            table = tabulate(data_to_display, headers="keys", tablefmt='plain')
            print(table)

            # detailed job status
            print('\n')
            i = 0
            for job in dep_job_set:
                i += 1
                print(f"Deployment Job Nr. {i}")
                print(f"Robot Name: {job['robot_name']}")
                print(f"Job Phase: {job['job_phase']}")
                print('-' * num_of_single_dash)

                data_to_display = [{
                    'Resource Name': pod['name'],
                    'Type': 'Pod',
                    'Status': pod.get('status', 'N/A'),
                } for pod in job['all_pods_status']]
                data_to_display += [{
                    'Resource Name': svc['name'],
                    'Type': 'Service',
                    'Status': svc.get('status', 'N/A'),
                } for svc in job['all_svcs_status']]

                table = tabulate(
                    data_to_display, headers="keys", tablefmt='plain')
                print(table)

        else:
            print(res)

    def list(self):
        """
        List all deployments
        Example: kuberos cluster list
        """
        config = KuberosConfig.get_current_config()
        _, response = self.call_api('GET',
                                    f"{config['server']}/{Endpoints.DEPLOYMENT}",
                                    auth_token=config['token'])
        if response['status'] == 'success':
            data = response['data']
            data_to_display = [{
                'name': item['name'],
                'status': item['status'],
                'fleet': item['fleet_name'],
                'running_since': item['running_since'],
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
        url = f"{config['server']}/{Endpoints.DEPLOYING}{parsed_args.deployment_name}/"

        success, response = self.call_api('DELETE',
                                          url,
                                          auth_token=config['token'])
        if success:
            print(response)
            # print(f"Successfully delete cluster: {parsed_args.deployment_name}")
        else:
            print('[Error] Failed to delete cluster')

    def print_help(self):
        """
        Print help message
        """
        print(DEPLOY_HELP)
