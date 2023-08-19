#!/usr/bin/env python3

# python
import os
import argparse
import argcomplete
import requests
import getpass
import json
import yaml
import sys
from tabulate import tabulate

# KuberosCLI
import endpoints
import help_texts


def print_helper(help_text):
    """
    Wrapper to print help text
    """
    def inner(func):
        def wrapper(instance, *args, **kwargs):
            if len(args) == 0:
                print(help_text)
            func(instance, *args, **kwargs)
        return wrapper
    return inner


class KuberosCli():
    """
    KuberROS Comand Line Interface
    """
    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(
            description='ROS Kubernetes Package Manager',
            usage=help_texts.help_text_summary
        )
        self.parser.add_argument('command',
                            # choices=["list", "create", "delete"],
                            help='Subcommand to run')

        # config parameters
        self.parser.add_argument('--output', help='Output format (default is table. "yaml"/"dict")')
        self.parser.add_argument('--kube-config-file', help='Path to k8s config file')
        self.parser.add_argument('--kube-api-server', help='K8s Api server IP and Port')
        self.parser.add_argument('--kube-api-key', help='api-key for authorization')
        self.parser.add_argument('--kube-ssl-ca', help='ca certificate')

        argcomplete.autocomplete(self.parser)

        # print helper if the supplied subcommand not found.
        if len(sys.argv) == 1:
            self.print_helper()
            sys.exit(1)

        args = self.parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print(f'Unrecognized command: {args.command}')
            self.print_helper()
            sys.exit(1)

        if args.command == 'login':
            self.login()
        else:
            self.load_config()

        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)(*sys.argv[2:])


    ### BASIC COMMANDS ###
    def deploy(self, *args):
        """
        Deploy an ROS2 application through a deployment desciption file 
        or select software module from software manager.
        args: 
            - file: deployment description file
        """
        parser = argparse.ArgumentParser(
            description='Deploy an application'
        )
        parser.add_argument('-f', required=True, help='YAML file')
        args = parser.parse_args(args)

        try:
            with open(args.f, "r") as yaml_file:

                deploy_content = yaml.safe_load(yaml_file)
                rosparam_yamls = self.load_yaml_files_from_parammap(deploy_content)

                # call api server
                _, response = self.__api_call(
                    'POST',
                    f'{self.api_server}/{endpoints.DEPLOYING}',
                    json_data={
                        'deployment_manifest': deploy_content,
                        'rosparam_yamls': rosparam_yamls
                    },
                    auth_token=self.auth_token
                )
                print (response)

        except FileNotFoundError:
            print(f'Deployment description file: {args.f} not found.')
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
                    print(f"Parameter file path in {item['name']} is not specified.")
                    sys.exit(1)

        return param_files


    def delete(self, *args):
        """
        Delete an deployed application by the deployment name
        args: 
            -- deployment_name
        """
        parser = argparse.ArgumentParser(
            description='Delete an application'
        )
        parser.add_argument('deployment_name', help='Name of the deployment')
        args = parser.parse_args(args)

        url = f'{endpoints.DEPLOYING}{args.deployment_name}/'
        _, response = self.__api_call('DELETE',
                                      f'{self.api_server}/{url}',
                                      auth_token=self.auth_token)
        print(response)


    def info(self, *args):
        """
        Command to get the details of a deployment
        """
        parser = argparse.ArgumentParser(
            description='Get the details of a deployment'
        )
        parser.add_argument('deployment_name', help='Name of the deployment')
        args = parser.parse_args(args)
        # call api server
        url = f'{endpoints.DEPLOYMENT}{args.deployment_name}/'
        _, res = self.__api_call('GET',
                                 f'{self.api_server}/{url}',
                                 auth_token=self.auth_token)
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

                table = tabulate(data_to_display, headers="keys", tablefmt='plain')
                print(table)

        else:
            print(res)

    def list(self, *args):
        """
        Command to get the list of deployments
        """
        parser = argparse.ArgumentParser(
            description='List the fleets in kuberos'
        )
        # parser.add_argument('--verbose', help='Verbose output')
        args = parser.parse_args(args)
        # call api server
        _, response = self.__api_call('GET',
                                      f'{self.api_server}/{endpoints.DEPLOYMENT}',
                                      auth_token=self.auth_token)
        
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
            print('[Error]')
            print(response)


    ### BATCH JOBS ###
    def job(self, *args):
        """
        Batch jobs command
        """
        parser = argparse.ArgumentParser(
            description='Submit batch jobs',
            usage=help_texts.BATCH_JOB,
        )
        parser.add_argument('subcommand', help='Subcommand to run')
        args = parser.parse_args(args[:1])
        # call subcommand
        if not hasattr(self, f'job_{args.subcommand}'):
            print(f'[Error] -- Unrecognized command: {args.subcommand}')
            sys.exit(1)
        getattr(self, f'job_{args.subcommand}')(*sys.argv[3:])


    def job_list(self, *args):
        """
        List all batchjob deployment
        """
        parser = argparse.ArgumentParser(
            description='List the registered clusters in kuberos'
        )
        args = parser.parse_args(args)
        # call api server
        success, response = self.__api_call('GET', f'{self.api_server}/{endpoints.BATCH_JOB}',
                                        auth_token=self.auth_token)

        if success:
            data = response['data']
            data_to_display = [{
                'Batch jobs name': item['name'],
                'Is Active': item['is_active'],
                'Status': item["status"],
                'Execution in cluster': item['exec_cluster'],
            } for item in data]

            table = tabulate(data_to_display, headers="keys", tablefmt='plain')
            print(table)
        else:
            print('error')

    def job_create(self, *args):
        """
        Deploy an ROS2 application through a deployment desciption file 
        or select software module from software manager.
        args: 
            - file: deployment description file

        """
        parser = argparse.ArgumentParser(
            description='Create a batch jobs'
        )
        parser.add_argument('-f', required=True, help='YAML file')
        args = parser.parse_args(args)

        try:
            with open(args.f, "r") as yaml_file:

                deploy_content = yaml.safe_load(yaml_file)
                rosparam_yamls = self.load_yaml_files_from_parammap(deploy_content)

                # call api server
                _, response = self.__api_call(
                    'POST',
                    f'{self.api_server}/{endpoints.BATCH_JOB}',
                    json_data={
                        'deployment_manifest': deploy_content,
                        'rosparam_yamls': rosparam_yamls
                    },
                    auth_token=self.auth_token
                )
                print (response)

        except FileNotFoundError:
            print(f'Deployment description file: {args.f} not found.')
            sys.exit(1)

    def job_delete(self, *args):
        """
        Terminate and delete a batch job deployment
        """
        parser = argparse.ArgumentParser(
            description='Delete a batch job deployment'
        )
        parser.add_argument('deployment_name', help='Name of the deployment')
        args = parser.parse_args(args)

        url = f'{endpoints.BATCH_JOB}{args.deployment_name}/'
        _, response = self.__api_call('DELETE',
                                      f'{self.api_server}/{url}',
                                      auth_token=self.auth_token)
        print(response)


    ### CLUSTER MANAGEMENT ###
    def cluster(self, *args):
        """
        Cluster management command
        """
        parser = argparse.ArgumentParser(
            description='Manage clusters',
            usage=help_texts.cluster,
        )
        parser.add_argument('subcommand', help='Subcommand to run')
        args = parser.parse_args(args[:1])
        # call subcommand
        if not hasattr(self, f'cluster_{args.subcommand}'):
            print(f'[Error] -- Unrecognized command: {args.subcommand}')
            sys.exit(1)
        getattr(self, f'cluster_{args.subcommand}')(*sys.argv[3:])

    def cluster_list(self, *args):
        """
        List all clusters that the user has access to
        """
        parser = argparse.ArgumentParser(
            description='List the registered clusters in kuberos'
        )
        parser.add_argument('--verbose', help='Verbose output')
        args = parser.parse_args(args)
        # call api server
        success, response = self.__api_call('GET', f'{self.api_server}/{endpoints.CLUSTER}',
                                        auth_token=self.auth_token)
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
            print('error')

    def cluster_info(self, *args):
        """
        Retrieve the status of a cluster by cluster name
        """
        parser = argparse.ArgumentParser(
            description='Get cluster details'
        )
        parser.add_argument('cluster_name', help='Name of the cluster')
        parser.add_argument('-sync', action='store_true', help='Sync the cluster with Kuberos')
        parser.add_argument('-output', help='Output format: table / json / yaml')
        args = parser.parse_args(args)

        # call API server
        url = f'{endpoints.CLUSTER}{args.cluster_name}/'
        success, response = self.__api_call('GET',
                                        f'{self.api_server}/{url}',
                                        auth_token=self.auth_token,
                                        data={
                                            'sync': args.sync
                                        })
        if success:
            if response['status'] == 'failed':
                print("Retrieve cluster status failed.")
                print("Errors: ")
                print(response['errors'])
                sys.exit(1)
            if args.output == 'json':
                json_str = json.dumps(response['data'], indent=4)
                print(json_str)
            elif args.output == 'yaml':
                data_to_display = yaml.dump(response['data'],
                                            default_flow_style=False,
                                            indent=2,
                                            sort_keys=False)
                print(data_to_display)
            else:
                data = response['data']
                print('\n')
                print(f"Cluster Name: {data['cluster_name']}")
                print(f"API Server: {data['host_url']}")
                print(f'Alive Age: {data["alive_age"]}')
                print(f'Since Last Sync: {data["last_sync_since"]}')
                print('\n')
                # print(data)
                # display onboard device
                onboard_devices = []
                edge_nodes = []
                control_plane_nodes = []
                unassigned_nodes = []

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
                                'AVAILABLE': node['is_available'],
                                'FLEET': fleet_name,
                                'PERIPHERALS': node.get('peripheral_device_name_list', None),})

                    # Edge nodes (on-premise)
                    elif node['kuberos_role'] == 'edge':
                        edge_nodes.append({
                                'HOSTNAME': node['hostname'],
                                'GROUP': node.get('resource_group', None),
                                'SHARED RESOURCE': node.get('is_shared', None),
                                'AVAILABLE': node['is_available'],
                                'REACHABLE': node['is_alive']})

                    # unassigned nodes
                    elif node['kuberos_role'] == 'unassigned':
                        unassigned_nodes.append({
                                'HOSTNAME': node['hostname'],
                                'ROLE': node['kuberos_role'],
                                'REGISTERED': node['kuberos_registered'],
                                'AVAILABLE': node['is_available'],
                                'REACHABLE': node['is_alive'],})

                    # control plane nodes
                    elif node['kuberos_role'] == 'control_plane':
                        control_plane_nodes.append({
                                'HOSTNAME': node['hostname'],
                                'ROLE': node['kuberos_role'],
                                'REGISTERED': node['kuberos_registered'],
                                'AVAILABLE': node['is_available'],
                                'REACHABLE': node['is_alive'],})

                # display data
                num_of_single_dash = 80
                if len(onboard_devices) > 0:
                    print('Robot Onboard Computers')
                    print('-' * num_of_single_dash)
                    table = tabulate(onboard_devices, headers="keys", tablefmt='plain')
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
                    table = tabulate(unassigned_nodes, headers="keys", tablefmt='plain')
                    print(table)
                    print('\n')
                if len(control_plane_nodes) > 0:
                    print('Control Plane Nodes')
                    print('-' * num_of_single_dash)
                    table = tabulate(control_plane_nodes, headers="keys", tablefmt='plain')
                    print(table)
                    print('\n')
        else:
            print('error')

    def cluster_update(self, *args):
        """
        Update the inventory description
         - set node labels
        """
        parser = argparse.ArgumentParser(
            description='Init K8s Cluster with Inventory Description'
        )
        # parser.add_argument('cluster_name', help='Name of the cluster')
        parser.add_argument('-f', help='File path of inventory description')
        args = parser.parse_args(args)

        try:
            with open(args.f, 'r') as f:
                files = {'inventory_description': f}
                data = {
                    'updata': True # add more options todo later
                }
                # call API server
                _, res = self.__api_call(
                    'POST',
                    f'{self.api_server}/{endpoints.CLUSTER_INVENTORY}',
                    files=files,
                    data=data,
                    auth_token=self.auth_token
                )
                if res['res'] == 'success':
                    print(res)
                else:
                    print(res)
        except FileNotFoundError:
            print(f'Inventory description file: {args.f} not found.')
            sys.exit(1)


    def cluster_create(self, *args):
        """
        Add new cluster to be managed by KubeROS
        """
        parser = argparse.ArgumentParser(
            description='Add a new cluster to Kuberos Plattform'
        )
        parser.add_argument('--cluster_name', help='Name of the cluster')
        parser.add_argument('--host', help='Host URL of Kubernetes API server')
        parser.add_argument('--token', help='Admin service token')
        parser.add_argument('--ca_cert', help='Path of CA certificate')
        parser.add_argument('-f', help='File path of cluster registration')
        args = parser.parse_args(args)
        if args.f:
            cluster = self.parse_cluster_registration_yaml(args.f)
            ca_file_path = cluster.pop('ca_cert')
        else:
            cluster = {
                    'cluster_name': args.cluster_name,
                    'distribution': 'k3s',
                    'host_url': args.host,
                    'service_token_admin': args.token,
                }
            ca_file_path = args.ca_cert

        # call api server
        try:
            with open(ca_file_path, "r") as f:
                files = {'ca_crt_file': f}
                # call api server 
                _, res = self.__api_call(
                    'POST',
                    f'{self.api_server}/{endpoints.CLUSTER}',
                    files=files,
                    data=cluster,
                    auth_token=self.auth_token
                )
                if res['status'] == 'success':
                    print(res)
                else:
                    print(res)
        except FileNotFoundError:
            print(f'CA file: {args.ca_cert} not found.')
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


    def cluster_reset(self, *args):
        """
        # CHECK - DEPRECATED
        Reset the cluster that managed by KubeROS
            - clean labels
            - remove all kuberos related resources
        Reset can only be performed when the cluster is not in use and not registered in a fleet.
        Test command: 
        ./kuberos.py cluster reset bw1-prod-cluster
        """
        parser = argparse.ArgumentParser(
            description='Add a new cluster to Kuberos Plattform'
        )
        parser.add_argument('cluster_name', help='Name of the cluster')
        args = parser.parse_args(args)
        # call api server
        url = f'{endpoints.CLUSTER}{args.cluster_name}/'
        success, data = self.__api_call('DELETE',
                                        f'{self.api_server}/{url}',
                                        auth_token=self.auth_token)
        if success:
            json_str = json.dumps(data, indent=4)
            print(json_str)
        else:
            print('error')


    def cluster_delete(self, *args):
        """
        Subcommand to remove the cluster managed by KubeROS
        """
        parser = argparse.ArgumentParser(
            description='Remove cluster'
        )
        parser.add_argument('cluster_name', help='Cluster name')
        args = parser.parse_args(args)
        # call api server 
        url = f'{endpoints.CLUSTER}{args.cluster_name}/'
        success, data = self.__api_call('DELETE',
                                        f'{self.api_server}/{url}',
                                        auth_token=self.auth_token)
        if success:
            json_str = json.dumps(data, indent=4)
            print(json_str)
        else:
            print('error')

    ################################################
    ###            FLEET MANAGEMENT              ###
    ################################################
    def fleet(self, *args):
        """
            Fleet management command
        """
        parser = argparse.ArgumentParser(
            description='Manage Fleets',
            usage=help_texts.fleet,
        )
        parser.add_argument('subcommand', help='Subcommand to run')
        args = parser.parse_args(args[:1])
        # call subcommand
        if not hasattr(self, f'fleet_{args.subcommand}'):
            print(f'Unrecognized command: {args.subcommand}')
            sys.exit(1)
        getattr(self, f'fleet_{args.subcommand}')(*sys.argv[3:])


    def fleet_create(self, *args):
        """
        Create fleet from a fleet manifest file
        """
        parser = argparse.ArgumentParser(
            description='Create a fleet with Fleet Description'
        )
        parser.add_argument('-f', help='File path of fleet manifest')
        args = parser.parse_args(args)

        try:
            with open(args.f, 'r') as f:
                files = {'fleet_manifest': f}
                data = {
                    'create': True,
                }
                # call API server
                _, res = self.__api_call(
                    'POST',
                    f'{self.api_server}/{endpoints.FLEET}',
                    files=files,
                    data=data,
                    auth_token=self.auth_token
                )
                print(res)

        except FileNotFoundError:
            print(f'Fleet manifest file: {args.f} not found.')
            sys.exit(1)

    def fleet_list(self, *args):
        """
        Subcommand to get the list of fleets
        ./kuberos.py fleet list
        """
        parser = argparse.ArgumentParser(
            description='List the fleets in kuberos'
        )
        parser.add_argument('--verbose', help='Verbose output')
        args = parser.parse_args(args)
        # call api server
        success, response = self.__api_call('GET',
                                        f'{self.api_server}/{endpoints.FLEET}', 
                                        auth_token=self.auth_token)
        if success:
            data = response['data']
            data_to_display = [{
                'Name': item['fleet_name'],
                'Status': item['fleet_status'],
                'Alive Age': item['alive_age'],
                'Healthy': item['healthy'],
                'Main Cluster': item['k8s_main_cluster_name'],
                'Created since': item['created_since'],
            } for item in data]
            table = tabulate(data_to_display, headers="keys", tablefmt='plain')
            print(table)
        else:
            print('error')

    def fleet_info(self, *args):
        """
        Subcommand to get the details of a fleet
        ./kuberos.py fleet status bw0-fleet
        """
        parser = argparse.ArgumentParser(
            description='Get the details of a fleet'
        )
        parser.add_argument('fleet_name', help='Name of the fleet')
        parser.add_argument('-output', help='Output format (default is table. "yaml"/"dict")')
        args = parser.parse_args(args)

        # call api server
        url = f'{endpoints.FLEET}{args.fleet_name}/'
        success, data = self.__api_call('GET',
                                        f'{self.api_server}/{url}',
                                        auth_token=self.auth_token)

        if success and data['status'] == 'success':
            data = data['data']
            if args.output == 'json':
                json_str = json.dumps(data, indent=4)
                print(json_str)
            elif args.output == 'yaml':
                data_to_display = yaml.dump(data,
                                            default_flow_style=False,
                                            indent=2,
                                            sort_keys=False)
                print(data_to_display)
            else:
            # print fleet details
                # print(data)
                print(f"Fleet Name: {data['fleet_name']}")
                print(f"Healthy: {data['healthy']}")
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
                        'Status': item['status'],
                        'Shared Resource': item['shared_resource'],
                    } for item in data['fleet_node_set']]
                table = tabulate(data_to_display, headers="keys", tablefmt='plain')
                print(table)
        else:
            print(f"Response: {data['status']}")
            print(f"Error: {data['errors']}")
            print(f"Message: {data['msgs']}")

    def fleet_delete(self, *args):
        """
        Subcommand to disband the fleet.
        """
        parser = argparse.ArgumentParser(
            description='Delete a fleet by name'
        )
        parser.add_argument('fleet_name', help='Name of the fleet')
        args = parser.parse_args(args)
        # call api server
        url = f'{endpoints.FLEET}{args.fleet_name}/'
        success, data = self.__api_call('DELETE',
                                        f'{self.api_server}/{url}',
                                        auth_token=self.auth_token)
        if success:
            json_str = json.dumps(data, indent=4)
            print(json_str)
        else:
            print('error')

    ### DEPLOYMENT ###
    def deployment(self, *args):
        """
            Deployment management command
        """
        parser = argparse.ArgumentParser(
            description='Manage Deployments',
            usage=help_texts.deployment,
        )
        parser.add_argument('subcommand', help='Subcommand to run')
        args = parser.parse_args(args[:1])
        # call subcommand
        if not hasattr(self, f'deployment_{args.subcommand}'):
            print(f'Unrecognized command: {args.subcommand}')
            sys.exit(1)
        getattr(self, f'deployment_{args.subcommand}')(*sys.argv[3:])


    def deployment_force_delete(self, *args):
        """
        Subcommand to delete a deployment directly in database
        FOR DEVELOPMENT PURPOSES ONLY
        """
        parser = argparse.ArgumentParser(
            description='Get the details of a deployment'
        )
        parser.add_argument('deployment_name', help='Name of the deployment')
        args = parser.parse_args(args)
        # call api server
        url = f'api/v1/deployment/admin_only/deployments/{args.deployment_name}/'
        success, res = self.__api_call('DELETE',
                                        f'{self.api_server}/{url}',
                                        auth_token=self.auth_token)
        if res['status'] == 'success':
            print("ONLY the DEPLOYMENT in DATABASE is deleted! For TESTING PURPOSES ONLY!")
            print("Deployment including deployment events and jobs deleted successfully")
        else:
            print("[ERROR]")
            print(res)


    ### REGISTRY TOKEN ###
    def registry_token(self, *args):
        """
        Subcommand to add registry token
        """
        parser = argparse.ArgumentParser(
            description='Manage Registry Token',
            usage=help_texts.registry_token,
        )
        parser.add_argument('subcommand', help='Subcommand to run')
        args = parser.parse_args(args[:1])
        # call subcommand
        if not hasattr(self, f'registry_token_{args.subcommand}'):
            print(f'Unrecognized command: {args.subcommand}')
            sys.exit(1)
        getattr(self, f'registry_token_{args.subcommand}')(*sys.argv[3:])

    def registry_token_create(self, *args):
        """
        Create a registry token
        """
        parser = argparse.ArgumentParser(
            description='Create a registry token'
        )
        parser.add_argument('-f', help='File path of fleet manifest')
        args = parser.parse_args(args)

        try:
            with open(args.f, 'r') as yaml_file:
                registry_token = yaml.safe_load(yaml_file)
                meta_data = registry_token['metadata']
                data = {
                    'name': meta_data['name'],
                    'user_name': meta_data['userName'],
                    'registry_url': meta_data['registryUrl'],
                    'token': meta_data['token'],
                    'description': meta_data['description'],
                }
                # call API server
                _, res = self.__api_call(
                    'POST',
                    f'{self.api_server}/{endpoints.REGISTRY_TOKEN}',
                    data=data,
                    auth_token=self.auth_token
                )
                print(res)

        except FileNotFoundError:
            print(f'Container registry token file: {args.f} not found.')
            sys.exit(1)


    def registry_token_list(self, *args):
        """
        List all registry tokens
        """
        parser = argparse.ArgumentParser(
            description="List the registry tokens in kuberos"
        )
        args = parser.parse_args(args)
        success, response = self.__api_call(
            'GET',
            f'{self.api_server}/{endpoints.REGISTRY_TOKEN}', 
            auth_token=self.auth_token)
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


    def registry_token_attach(self, *args):
        """
            Attach the registry token to a cluster 
            
            --cluster: name of cluster
            --token: name of token
            --namespace: namespace of cluster
            
            # test command: 
            python kuberos.py registry_token attach --cluster bw1-prod-cluster --token kuberos-test-registry-token
        """

        parser = argparse.ArgumentParser(
            description="List the registry tokens in kuberos"
        )
        parser.add_argument('--cluster', help='Name of cluster')
        parser.add_argument('--token', help='Name of token')
        parser.add_argument('--namespace', default='ros-default', help='Name of cluster')
        args = parser.parse_args(args)
        sucess, data = self.__api_call(
            'POST', 
            f'{self.api_server}/{endpoints.REGISTER_TOKEN_TO_CLUSTER}',
            data={
                'cluster_name': args.cluster,
                'token_name': args.token,
                'namespace': args.namespace,
            },
            auth_token=self.auth_token
        )
        if sucess:
            print(data)
        else:
            print(data)


    ### GENERAL Management Command ###
    def apply(self, *args):
        """
        General purpose command to apply the manifest file, 
        like kubectl apply -f <file>
        """
        parser = argparse.ArgumentParser(
            description='Update the inventory, fleet description'
        )
        parser.add_argument('-file', required=True, help='Verbose output')
        pass


    ### PRIVATE METHODS ###
    def __api_call(self, method, url, data=None, json_data=None,
                   files=None, headers=None, auth_token=None):
        """
        Private method to call the API server
        Args:
            method (_type_): 'CREATE', 'GET', 'PUT', 'DELETE
            url (_type_): endpoint url
            data (_type_, optional): data
            files (_type_, optional): yaml files. Defaults to None.
            headers (_type_, optional): headers. Defaults to None.
            auth_token (_type_, optional): user token. Defaults to None.

        Returns:
            success (bool): True if success, False if failed and print error message
            data (dict): response data
        """
        if headers is None:
            headers = {}
            # headers = {'Content-Type': 'application/json'}
        if auth_token is not None:
            headers['Authorization'] = 'Token ' + auth_token
        try:
            resp = requests.request(method, url, data=data,
                                    json=json_data,
                                    files=files,
                                    headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return True, data

        except requests.exceptions.HTTPError:
            err_type = resp.status_code

            if err_type == 400:
                # Bad request
                print("[Bad Request '400'] Please check the request parameters.")

            if err_type == 401:
                # Unauthorized
                print("[Unauthorized '401'] Login is required. The cached token is expired.")

            if err_type == 404:
                # Requested resource not found
                print("[Not Found '404'] Check the resource name and try again.")

            if err_type == 500:
                print("[Internal Server Error '500'] Please contact the administrator.")

            sys.exit(1)

        except requests.exceptions.RequestException:
            # Connection error
            print("[ConnectionError] Can not connect to the API server. \
                    Please check your network and kuberos config.")
            sys.exit(1)

        except Exception as exc:
            # Unknown error
            print("[Unknown Error]", exc)
            sys.exit(1)


    ### CONFIGURATION ###
    def login(self, *args):
        """Login to KubeROS API server
        
        KubeROS uses the token based authentication.
        The token is renewed automatically after connecting to the API server.
        After 24 hours without any request, the token will be expired.
        """
        # load current config to get the apt server address
        with open(".kuberos.config", "r") as f:
            cached_config = yaml.safe_load(f)

        api_server_address = None if cached_config is None else cached_config['api_server_address']
        if api_server_address is None:
            api_server_address = input("KubeROS API server address: ")
        else:
            print(f"login to KubeROS API server: {cached_config['api_server_address']}")
            print('If you want to change the API server address, please run \n\
                kuberos config set api-server <api-server-address>')

        username = input("Username: ")
        password = getpass.getpass("Password: ")

        success, data = self.__api_call('POST',
                               f'{api_server_address}/{endpoints.LOGIN}', 
                               data={
                                    'username': username,
                                    'password': password}
                                )
        if not success:
            print("Login failed")
            sys.exit(1)

        # update
        config = {} if cached_config is None else cached_config
        config['token'] = data['token']
        config['api_server_address'] = api_server_address
        
        # save to file
        with open(".kuberos.config", "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        print('Login success')
        sys.exit(0)

    def logout(self, *args):
        """
        Logout from KubeROS API server
        """
        parser = argparse.ArgumentParser(
            description='Logout from KubeROS API server'
        )
        args = parser.parse_args(args)
        success, response = self.__api_call('POST',
                                        f'{self.api_server}/{endpoints.LOGOUT}',
                                        auth_token=self.auth_token)
        print(success, response)


    def register(self, *args):
        """ Register a new user
        Test: 
            python kuberos.py register --username test --password test --email test@test.dummy
        """

        parser = argparse.ArgumentParser(
            description='Register a new user'
        )
        parser.add_argument('--username', help='Username')
        parser.add_argument('--password', help='Password')
        parser.add_argument('--email', help='Email')

        args = parser.parse_args(args)

        # call api server
        success, response = self.__api_call('POST',
                                            f'{self.api_server}/{endpoints.REGISTER}',
                                            data={
                                                'username': args.username,
                                                'password': args.password,
                                                'email': args.email,
                                            })
        print(f'Success: {success}')
        print(response)


    def load_config(self):
        """
        Load the cached authentication token and api server address
        """
        # get the environment variable
        config_path = os.environ.get('KUBEROS_CONFIG', None)
        if config_path is None:
            config_path = '.kuberos.config'

        # load the config file
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            print(f'Config file not found in path: {config_path}')

        # set parameters
        self.api_server = config['api_server_address']
        self.auth_token = config['token']

    def config(self, *args):
        # change the configuration of kube api server
        # default, using
        # TODO
        pass


    ### INFO ###
    # @print_helper(help_text=help_texts.info)
    # def info(self, *args):
    #     parser = argparse.ArgumentParser(
    #         description='Display the Kuberos main api server information',
    #         usage=help_texts.info
    #     )

    def print_helper(self):
        print(help_texts.help_text_summary)

    def autocomplete(self):
        argcomplete.autocomplete(self.parser)


def main ():
    cli = KuberosCli()
   #  cli.autocomplete()

if __name__ == '__main__':
    main()



# TEST Commands
# Deploy:  python kuberos.py deploy --file /workspace/kuberos/pykuberos/examples/hello_world.kuberos.yml
# Delete:  python kuberos.py delete hello-world-humble-dev