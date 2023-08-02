#!/usr/bin/env python

# python
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


class KuberosCli(object):

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
            print('Unrecognized command: %s' % args.command)
            self.print_helper()
            exit(1)

        if args.command == 'login':
            self.login()
        else:
            self.config_path = ".kuberos.config" ## TODO change to ~/.kuberos/config
            self.load_config(self.config_path)
        
        # use dispatch pattern to invoke method with same name
        getattr(self, args.command)(*sys.argv[2:])


    ### BASIC COMMANDS ###
    def deploy(self, *args):
        """
        Deploy an ROS2 application through a deployment desciption file 
        or select software module from software manager.
        args: 
            - file: deployment description file
        ./kuberos.py deploy -f /workspace/kuberoscli/ros_deployment/hello_world_single_robot.kuberos.yml
        """
        parser = argparse.ArgumentParser(
            description='Deploy an application'
        )
        parser.add_argument('-f', required=True, help='YAML file')
        args = parser.parse_args(args)
        
        # load yaml file 
        try:
            with open(args.f, "r") as f:
                files = {'deployment_yaml': f}
                # call api server 
                _, res = self.__api_call(
                    'POST',
                    f'{self.api_server}/{endpoints.DEPLOYING}',
                    files=files,
                    auth_token=self.auth_token
                )
                if res['success'] == True:
                    print(res)
                else:
                    print(res)
                    # print('Status: {} \n Message: '.format(data['status'], data['msg']))
        except FileNotFoundError:
            print("Deployment description file: {} not found.".format(args.f))
            exit(1)

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

        url = '{}{}/'.format(endpoints.DEPLOYING, args.deployment_name)
        success, res = self.__api_call('DELETE', 
                                       f'{self.api_server}/{url}', 
                                       auth_token=self.auth_token)
        if res['status'] == 'success':
            print(res)
        else:
            print('[ERROR] {}'.format(res['msg']))

    ### CLUSTER MANAGEMENT ###
    def cluster(self, *args):
        parser = argparse.ArgumentParser(
            description='Manage clusters', 
            usage=help_texts.cluster,
        )
        parser.add_argument('subcommand', help='Subcommand to run')
        args = parser.parse_args(args[:1])
        # call subcommand
        if not hasattr(self, f'cluster_{args.subcommand}'):
            print('Unrecognized command: %s' % args.subcommand)
            exit(1)
        getattr(self, f'cluster_{args.subcommand}')(*sys.argv[3:])
    
    def cluster_list(self, *args):
        parser = argparse.ArgumentParser(
            description='List the registered clusters in kuberos'
        )
        parser.add_argument('--verbose', help='Verbose output')
        args = parser.parse_args(args)
        # call api server 
        success, data = self.__api_call('GET', f'{self.api_server}/{endpoints.CLUSTER}', 
                                        auth_token=self.auth_token)
        if success:
            # formatted = json.dumps(data, sort_keys=False, indent=4)
            data_to_display = [{
                'cluster_name': item['cluster_name'],
                'host_url': item['host_url'],
                'uuid': item['uuid'],
                # 'created_at': item['created_time'],
            } for item in data]
            
            table = tabulate(data_to_display, headers="keys", tablefmt='plain')
            print(table)
        else:
            print('error')

    def cluster_status(self, *args):
        """
        Retrieve the status of a cluster with the cluster name
        """
        parser = argparse.ArgumentParser(
            description='Get cluster details'
        )
        parser.add_argument('cluster_name', help='Name of the cluster')
        parser.add_argument('-sync', action='store_true', help='Sync the cluster with Kuberos')
        parser.add_argument('-output', help='Output format: table / json / yaml')
        args = parser.parse_args(args)
    
        # call API server
        # url = endpoints.CLUSTER_STATUS.replace('<cluster_name>', args.cluster_name)
        url = '{}{}/'.format(endpoints.CLUSTER, args.cluster_name)
        success, data = self.__api_call('GET', 
                                        f'{self.api_server}/{url}',
                                        auth_token=self.auth_token, 
                                        data={
                                            'sync': args.sync
                                        })
        if success:
            if args.output == 'json':
                json_str = json.dumps(data, indent=4)
                print(json_str)
            elif args.output == 'yaml':  
                data_to_display = yaml.dump(data, default_flow_style=False, indent=2, sort_keys=False)
                print(data_to_display)
            else:
                print('\n')
                print('Cluster Name: {}'.format(data['cluster_name']))
                print('API Server: {}'.format(data['host_url']))
                print('\n')
    
                # display onboard device 
                onboard_devices = []
                edge_nodes = []
                cloud_nodes = []
                control_plane_nodes = []
                unassigned_nodes = []
                
                for node in data['cluster_node_set']:
                    # onboard computers
                    if node['kuberos_role'] == 'onboard':
                        onboard_devices.append(
                            {
                                'ROBOT_NAME': node.get('robot_name', None),
                                'HOSTNAME': node['hostname'],
                                'DEVICE_GROUP': node['device_group'],
                                'AVAILABLE': node['is_available'],
                                'FLEET': node.get('assigned_fleet_name', None),
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
        ./kuberos.py cluster update -f /workspace/kuberoscli/inventory/bw1.inventory.kuberos.yml
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
            print("Inventory description file: {} not found.".format(args.inv))
            exit(1)
    
    
    def cluster_register(self, *args):
        """
        Add new cluster to be managed by KubeROS
        Test command: 
        python kuberos.py cluster register bw1-prod-cluster --host https://193.196.37.240:6443 --ca_cert /workspace/kuberos/pykuberos/config/ca_bw1.crt --token eyJhbGciOiJSUzI1NiIsImtpZCI6ImNwUVQ2ZmpzRDNJUVR4MFE1aEtvTzdCdUJDVnhxcGMtSW8zNmpId1BfQW8ifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6Imt1YmVyb3Mtc2VydmljZS1hY2NvdW50LXRva2VuLWh2am5oIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQubmFtZSI6Imt1YmVyb3Mtc2VydmljZS1hY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZXJ2aWNlLWFjY291bnQudWlkIjoiODU5NTJiOTQtYWZjYi00YTJmLWE2ZjYtMWEwMWExMzUwYzVkIiwic3ViIjoic3lzdGVtOnNlcnZpY2VhY2NvdW50OmRlZmF1bHQ6a3ViZXJvcy1zZXJ2aWNlLWFjY291bnQifQ.bkfWZOqN__DspAXQw5yzX0TTYbGrfhbYOJZKM7AMWKD2tsJduHkuK49tdpSId2_RZYOIAgHfvVF9Q7U9LMEtC5aTMP1ruQiGYqUa0S-emOqDkw_3K1aOmU4L4m6zXqZrCX_sTMJKJtiup6mfWT6dFqPe96o1_kWomiOF2zWzuaYVTRlukpnrXB2FPPC9uz3_ojyUPmur4GAr1xbTgA6UYAOAtPIf_VfM-Wq_OU4ntfncXVbqa5kktkSwr-vkRZktH0juEuz601F8b-2EyckXcynFF1mY3NNURb1LAreiMSltsqaSkJWNlr8ybCAaVZV9LslpNcjbeRmNOmjwRZq0Hg
        """
        parser = argparse.ArgumentParser(
            description='Add a new cluster to Kuberos Plattform'
        )
        parser.add_argument('cluster_name', help='Name of the cluster')
        parser.add_argument('--host', help='Host URL of Kubernetes API server')
        parser.add_argument('--token', help='Admin service token')
        parser.add_argument('--ca_cert', help='Path of CA certificate')
        args = parser.parse_args(args)
        # call api server
        try:
            with open(args.ca_cert, "r") as f:
                files = {'ca_crt_file': f}
                data = {
                    'name': args.cluster_name,
                    'host_url': args.host,
                    'service_token_admin': args.token,
                }
                # call api server 
                _, res = self.__api_call(
                    'POST',
                    f'{self.api_server}/{endpoints.CLUSTER}',
                    files=files,
                    data=data,
                    auth_token=self.auth_token
                )
                if res['status'] == 'success':
                    print(res)
                else:
                    print(res)
        except FileNotFoundError:
            print("CA file: {} not found.".format(args.ca_cert))
            exit(1)
            
    
    def cluster_reset(self, *args):
        """
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
        url = f'{endpoints.CLUSTER_INVENTORY}{args.cluster_name}/'  
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
        parser = argparse.ArgumentParser(
            description='Manage Fleets', 
            usage=help_texts.fleet,
        )
        parser.add_argument('subcommand', help='Subcommand to run')
        args = parser.parse_args(args[:1])
        # call subcommand
        if not hasattr(self, f'fleet_{args.subcommand}'):
            print('Unrecognized command: %s' % args.subcommand)
            exit(1)
        getattr(self, f'fleet_{args.subcommand}')(*sys.argv[3:])    
    
    
    def fleet_create(self, *args):
        """
        Create fleet from a fleet manifest file
        ./kuberos.py fleet create -f /workspace/kuberoscli/fleet_description/fleet_bw0.v1.kuberos.yaml
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
            print("Fleet manifest file: {} not found.".format(args.f))
            exit(1)
    
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
        success, data = self.__api_call('GET', 
                                        f'{self.api_server}/{endpoints.FLEET}', 
                                        auth_token=self.auth_token)
        if success:
            data_to_display = [{
                'Name': item['fleet_name'],
                'Main Cluster': item['k8s_main_cluster_name'],
                'UUID': item['uuid'],
                'Created at': item['created_time'],
            } for item in data]
            table = tabulate(data_to_display, headers="keys", tablefmt='plain')
            print(table)
        else:
            print('error')
    
    def fleet_status(self, *args):
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
        
        if success and data['success']:
            data = data['data']
            if args.output == 'json':
                json_str = json.dumps(data, indent=4)
                print(json_str)
            elif args.output == 'yaml':
                data_to_display = yaml.dump(data, default_flow_style=False, indent=2, sort_keys=False)
                print(data_to_display)
            else:
                
                # print(data)
                
                print("Fleet Name: {}".format(data['fleet_name']))
                print("Active: {}".format(data['active']))
                print("Main Cluster: {}".format(data['k8s_main_cluster_name']))
                print("Description: {}".format(data['description']))
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
            print('error')
            print(data['msg'])
    
    def fleet_disband(self, *args):
        """
        Subcommand to disband the fleet.
        """
        parser = argparse.ArgumentParser(
            description='Get the details of a fleet'
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
        parser = argparse.ArgumentParser(
            description='Manage Fleets', 
            usage=help_texts.deployment,
        )
        parser.add_argument('subcommand', help='Subcommand to run')
        args = parser.parse_args(args[:1])
        # call subcommand
        if not hasattr(self, f'deployment_{args.subcommand}'):
            print('Unrecognized command: %s' % args.subcommand)
            exit(1)
        getattr(self, f'deployment_{args.subcommand}')(*sys.argv[3:])    
    
    def deployment_list(self, *args):
        """
        Subcommand to get the list of deployments
        """
        parser = argparse.ArgumentParser(
            description='List the fleets in kuberos'
        )
        # parser.add_argument('--verbose', help='Verbose output')
        args = parser.parse_args(args)
        # call api server 
        success, data = self.__api_call('GET',
                                        f'{self.api_server}/{endpoints.DEPLOYMENT}', 
                                        auth_token=self.auth_token)
        if success: 
            data_to_display = [{
                'name': item['name'],
                'status': item['status'],
                'fleet': item['fleet_name'],
                'running_since': item['running_since'],
            } for item in data]
            table = tabulate(data_to_display, headers="keys", tablefmt='plain')
            print(table)
        else:
            print('error')
    
    def deployment_status(self, *args):
        """
        Subcommand to get the details of a deployment
        """
        parser = argparse.ArgumentParser(
            description='Get the details of a deployment'
        )
        parser.add_argument('deployment_name', help='Name of the deployment')
        args = parser.parse_args(args)
        # call api server 
        url = '{}{}/'.format(endpoints.DEPLOYMENT, args.deployment_name)
        success, res = self.__api_call('GET', 
                                        f'{self.api_server}/{url}',
                                        auth_token=self.auth_token)
        if res['status'] == 'success':
            # meta info
            print("Deployment Name: {}".format(res['data']['name']))
            print("Status: {}".format(res['data']['status']))
            print("Fleet: {}".format(res['data']['fleet_name']))
            print("Running Since: {}\n".format(res['data']['running_since']))
            
            # dep jobs summary
            num_of_single_dash = 60
            print('Deployment Jobs Summary')
            print('-' * num_of_single_dash)
            dep_job_set = res['data']['deployment_job_set']
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
                print("Deployment Job Nr. {}".format(i))
                print("Robot Name: {}".format(job['robot_name']))
                print("Job Phase: {}".format(job['job_phase']))
                print('-' * num_of_single_dash)
                data_to_display = [{
                        'Resource Name': pod['name'],
                        'Type': 'Pod',
                        'Status': pod['status'],
                    } for pod in job['all_pods_status']]
                data_to_display += [{
                        'Resource Name': svc['name'],
                        'Type': 'Service',
                        'Status': svc['status'],
                } for svc in job['all_svcs_status']]
                table = tabulate(data_to_display, headers="keys", tablefmt='plain')
                print(table)
            
            # data_to_display = yaml.dump(res['data'], default_flow_style=False, indent=2, sort_keys=False)
            # print(data_to_display)
        else:
            print('[ERROR] {}'.format(res['msg']))
    
    def deployment_delete(self, *args):
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
        url = '{}/{}/'.format(endpoints.DEPLOYMENT, args.deployment_name)
        success, res = self.__api_call('DELETE', 
                                        f'{self.api_server}/{url}',
                                        auth_token=self.auth_token)
        if res['status'] == 'success':
            print("ONLY the DEPLOYMENT in DATABASE is deleted! For TESTING PURPOSES ONLY!")
            print("Deployment include Deployment events deleted successfully")
        else:
            print('[ERROR] {}'.format(res['msg']))
    
    
    ### REGISTRY TOKEN ###
    def registry_token(self, *args):
        parser = argparse.ArgumentParser(
            description='Manage Registry Token', 
            usage=help_texts.registry_token,
        )
        parser.add_argument('subcommand', help='Subcommand to run')
        args = parser.parse_args(args[:1])
        # call subcommand
        if not hasattr(self, f'registry_token_{args.subcommand}'):
            print('Unrecognized command: %s' % args.command)
            exit(1)
        getattr(self, f'registry_token_{args.subcommand}')(*sys.argv[3:])    
    
    def registry_token_list(self, *args):
        parser = argparse.ArgumentParser(
            description="List the registry tokens in kuberos"
        )
        args = parser.parse_args(args)
        success, data = self.__api_call(
            'GET',
            f'{self.api_server}/{endpoints.REGISTRY_TOKEN_LIST}', 
            auth_token=self.auth_token)
        if success: 
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
            f'{self.api_server}/{endpoints.REGISTRY_TOKEN_ATTACH_REMOVE}',
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
    def __api_call(self, method, url, data=None, files=None, headers=None, auth_token=None):
        if headers is None:
            headers = {}
            # headers = {'Content-Type': 'application/json'}
        if auth_token is not None:
            headers['Authorization'] = 'Token ' + auth_token
        try:
            resp = requests.request(method, url, data=data, files=files, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return True, data
        except requests.exceptions.HTTPError as e:
            error_type = resp.status_code
            if error_type == 401:
                print("Unauthorized, login is required. The previous cached token is expired.")
            exit(1)
        except requests.exceptions.RequestException as e:
            print("[ConnectionError] Can not connect to the API server. Please check your network and kuberos config.")
            exit(1)
        except Exception as e:
            print(e)
            exit(1)
    
    
    ### CONFIGURATION ###
    def login(self, *args):
        # load current config to get the apt server address 
        with open(".kuberos.config", "r") as f:
            cached_config = yaml.safe_load(f)
        
        api_server_address = None if cached_config is None else cached_config['api_server_address']
        if api_server_address is None:
            api_server_address = input("KubeROS API server address: ")
        else:
            print('login to KubeROS API server: {}'.format(cached_config['api_server_address']))
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
            exit(1)

        # update
        config = {} if cached_config is None else cached_config
        config['token'] = data['token']
        config['api_server_address'] = api_server_address
        
        # save to file 
        with open(".kuberos.config", "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)
        print('Login success')
        exit(0)
        
    def load_config(self, path):
        try:
            with open(".kuberos.config", "r") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            print("Config file not found.")
        self.api_server = config['api_server_address']
        self.auth_token = config['token']

    def config(self):
        # change the configuration of kube api server
        # default, using 
        # TODO
        pass
        
    
    ### INFO ###
    @print_helper(help_text=help_texts.info)
    def info(self, *args):
        parser = argparse.ArgumentParser(
            description='Display the Kuberos main api server information', 
            usage=help_texts.info
        )
        
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