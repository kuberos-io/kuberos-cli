"""
Command group BatchJob
"""

import sys
import yaml
from tabulate import tabulate

from ..endpoints import Endpoints
from ..kuberos_config import KuberosConfig
from .base import CommandGroupBase, KubeROSBaseCompleter


BATCHJOB_HELP = '''
KubeROS CLI [job] command group

Usage:
    kuberos job <command> [job_name] [-args]
    
Commands:
    create       Create a new BatchJob deployment
                 -f --file: cluster registration yaml file path

    list         List all active BatchJobs
    
    info         Get batchjob by name
    
    stop         Stop the batchjob execution
    resume       Resume the batchjob execution
                 
    delete       Delete a BatchJob (soft stop and archive)
                 -force: delete BatchJob from DB (BE CAREFUL!!!)
'''


class BatchJobCompleter(KubeROSBaseCompleter):
    """
    Get the list of cluster names from the API server or cached data
    """

    def get_data_for_completion(self):
        _, data = self.call_api()
        return [item['name'] for item in data]


class BatchJobCommandGroup(CommandGroupBase):
    """
    Command group [job]
    """

    COMMAND_LIST = ['list', 'create', 'delete', 'info', 'stop', 'resume']

    RESOURCE_URL = 'api/v1/batch_jobs/batchjobs_name_list'

    def __init__(self, subparsers) -> None:
        super().__init__(subparsers, 'job')

        self.init_subcommand_create()
        self.init_subcommand_info()
        self.init_subcommand_delete()
        self.init_subcommand_stop()
        self.init_subcommand_resume()

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
        parser.add_argument('batchjob_name', help="Batch job name").completer = BatchJobCompleter(
            resource_url=self.RESOURCE_URL
        )

    def init_subcommand_stop(self):
        """
        Initialize the subcommand <stop>
        """
        parser = self.commands['stop']
        parser.add_argument('batchjob_name', help="Batch job name").completer = BatchJobCompleter(
            resource_url=self.RESOURCE_URL
        )

    def init_subcommand_resume(self):
        """
        Initialize the subcommand <resume>
        """
        parser = self.commands['resume']
        parser.add_argument('batchjob_name', help="Batch job name").completer = BatchJobCompleter(
            resource_url=self.RESOURCE_URL
        )

    def init_subcommand_delete(self):
        """
        Initialize the subcommand <delete>
        """
        parser = self.commands['delete']
        parser.add_argument('batchjob_name',
                            help="Batch job name").completer = BatchJobCompleter(
                                resource_url=self.RESOURCE_URL)

        parser.add_argument('-force', '--force',
                            action='store_true',
                            default=False,
                            help="Delete Batch job from database. [BE CAREFUL!]")

    def create(self, *args):
        """
        Create new BatchJob
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
                    f"{config['server']}/{Endpoints.BATCH_JOB}",
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
        success, response = self.call_api('GET',
                                          f"{config['server']}/{Endpoints.BATCH_JOB}",
                                          auth_token=config['token'])
        if success:
            data = response['data']
            data_to_display = [{
                'Name': item['name'],
                'Status': item['status'],
                'Exec. Clusters': item["exec_clusters"],
                'Started Since': item['started_since'],
                'Duration': item['execution_time']
            } for item in data]

            table = tabulate(data_to_display, headers="keys", tablefmt='plain')
            print(table)
        else:
            print("[FATAL] Unknown error.")

    def stop(self, *args):
        """
        Stop a running batchjob
        """
        parser = self.commands['stop']
        parsed_args = parser.parse_args(args)
        config = KuberosConfig.get_current_config()
        url = f"{config['server']}/{Endpoints.BATCH_JOB}{parsed_args.batchjob_name}/"
        success, response = self.call_api('PATCH',
                                          url,
                                          data={
                                              'cmd': 'stop'
                                          },
                                          auth_token=config['token'])
        if success:
            print(response)
        else:
            print('[Error] Failed to stop a batchjob')

    def resume(self, *args):
        """
        Stop a running batchjob
        """
        parser = self.commands['resume']
        parsed_args = parser.parse_args(args)
        config = KuberosConfig.get_current_config()
        url = f"{config['server']}/{Endpoints.BATCH_JOB}{parsed_args.batchjob_name}/"
        success, response = self.call_api('PATCH',
                                          url,
                                          data={
                                              'cmd': 'resume'
                                          },
                                          auth_token=config['token'])
        if success:
            print(response)
        else:
            print('[Error] Failed to stop a batchjob')

    def delete(self, *args):
        """
        Delete the cluster by cluster name
        """
        parser = self.commands['delete']
        parsed_args = parser.parse_args(args)
        config = KuberosConfig.get_current_config()
        url = f"{config['server']}/{Endpoints.BATCH_JOB}{parsed_args.batchjob_name}/"
        success, response = self.call_api('DELETE',
                                          url,
                                          data={
                                              'hard_delete': str(parsed_args.force)
                                          },
                                          auth_token=config['token'])
        if success:
            print(response)
            # print(f"Successfully delete cluster: {parsed_args.deployment_name}")
        else:
            print('[Error] Failed to delete batchjob')

    def print_help(self):
        """
        Print the help message
        """
        print(BATCHJOB_HELP)
