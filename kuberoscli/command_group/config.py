"""
Command group Config
"""

import sys
import getpass
import requests
from tabulate import tabulate

from argcomplete.completers import BaseCompleter

from ..endpoints import Endpoints
from .base import CommandGroupBase
from ..kuberos_config import KuberosConfig


CONFIG_HELP = '''
KubeROS CLI [config] command group

Usage:
    kuberos config <command> [context_name] [-args]
    
Commands:
    create       Add new context to the config file
                 --name: context name (unique)
                 --server: KubeROS api server
                 --user: username in KubeROS

    list         List all contexts
    
    switch       Switch the current context
    
    login        Login to the KubeROS api server
    
    logout       Logout from the KubeROS api server
    
    delete       Delete a context from the config file
'''


class ContextNameCompleter(BaseCompleter):
    """
    Get the list of context names from the config file
    """

    def __call__(self, **kwargs):
        return KuberosConfig.get_context_names()


class ConfigCommandGroup(CommandGroupBase):
    """
    Command group [config] for KubeROS CLI
    """

    COMMAND_LIST = ['login', 'logout', 'switch', 'list', 'create', 'delete']

    def __init__(self, subparsers) -> None:
        super().__init__(subparsers, 'config')

        self.init_subcommand_switch()
        self.init_subcommand_create()
        self.init_subcommand_delete()

    def init_subcommand_switch(self):
        """
        Initialize the subcommand switch
        """
        parser = self.commands['switch']
        parser.add_argument('context_name',
                            help="Name of the context").completer = ContextNameCompleter()

    def init_subcommand_create(self):
        """
        Initialize the subcommand create
        """
        parser = self.commands['create']
        parser.add_argument('--name', required=True,
                            help="Context name (unique)")
        parser.add_argument('--server', required=True,
                            help="KubeROS API server address")
        parser.add_argument('--user', required=True, help="KubeROS username")

    def init_subcommand_delete(self):
        """
        Initialize the subcommand delete
        """
        parser = self.commands['delete']
        parser.add_argument('context_name',
                            help="Name of the context").completer = ContextNameCompleter()

    def list(self, *args):
        """
        List the contexts
        """
        config = KuberosConfig.load_kuberos_config()
        print("Current context: ", config['current-context'])

        data_to_display = [{
            'Context': item['name'],
            'Server': item['server'],
            'User': item['user'],
        } for item in config['contexts']]
        table = tabulate(data_to_display, headers="keys", tablefmt='plain')
        print(table)

    def create(self, *args):
        """
        Add a new context in the local cli config file
        """
        parser = self.commands['create']
        args = parser.parse_args(args)
        context = {
            'name': args.name,
            'server': args.server,
            'user': args.user,
            'token': ''
        }
        KuberosConfig.update_config(context=context,
                                    current_context=context['name'])
        print("Add new context successfully")

    def delete(self, *args):
        """
        Delete a context from the local cli config file
        """
        parser = self.commands['delete']
        args = parser.parse_args(args)
        current_ctx = KuberosConfig.get_current_config()
        if args.context_name == current_ctx['name']:
            print("Please change the current context before deleting")
            sys.exit(0)

        if args.context_name not in KuberosConfig.get_context_names():
            print("Context not found")
            print("Available contexts: ", KuberosConfig.get_context_names())
            sys.exit(0)

        # delete the context
        KuberosConfig.delete_context(args.context_name)
        print(f'Successfully delete context: {args.context_name}')

    def switch(self, *args):
        """
        Switch the current context
        """
        parser = self.commands['switch']
        args = parser.parse_args(args)

        KuberosConfig.update_config(current_context=args.context_name)
        print(f"Switch config context to: {args.context_name}")

    def login(self):
        """
        Login to the api server
        """
        config_context = KuberosConfig.get_current_config()
        print('current api server: ', config_context['server'])
        print("Login to kuberos: >>>")
        username = input("Username: ")
        password = getpass.getpass("Password: ")

        success, res = self._call_auth_api('POST',
                                           f"{config_context['server']}/{Endpoints.LOGIN}",
                                           json_data={
                                               'username': username,
                                               'password': password}
                                           )
        if not success:
            print("Login failed")
            sys.exit(1)

        # update the config file
        config_context['token'] = res['token']
        config_context['user'] = username
        KuberosConfig.update_config(config_context)
        print("Login successfully")

    def logout(self):
        """
        Logout from the api server
        """
        config_context = KuberosConfig.get_current_config()
        success, _ = self._call_auth_api('POST',
                                         f"{config_context['server']}/{Endpoints.LOGOUT}",
                                         auth_token=config_context['token']
                                         )
        if success:
            print("Logout successfully")

    def _call_auth_api(self, method, url, json_data=None, auth_token=None):
        """
        Modified version of call_api in command_group/base.py
        For status code handling in login and logout process
        """
        headers = {}
        if auth_token is not None:
            headers['Authorization'] = 'Token ' + auth_token

        try:
            resp = requests.request(method,
                                    url,
                                    json=json_data,
                                    headers=headers,
                                    timeout=3)

            status_code = resp.status_code

            if status_code == 400:
                print("Username or password is incorrect")
                return False, None

            elif status_code == 401:
                print("Unauthorized / Already logged out")
                return True, None

            elif status_code == 204:
                return True, None

            elif status_code == 500:
                print(
                    "[Internal Server Error '500'] Please contact the administrator.")
            else:
                data = resp.json()
                return True, data
            sys.exit(0)

        except Exception as exc:
            # Catch unknown error
            print("[Unknown Error]", exc)
            sys.exit(1)

    def print_help(self):
        """
        Print the help text
        """
        print(CONFIG_HELP)
