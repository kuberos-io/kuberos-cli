"""
Base class for command group
 - KubeROSBaseCompleter
 - CommandGroupBase
"""

import sys
import requests
from argcomplete.completers import BaseCompleter

from ..kuberos_config import KuberosConfig


class KubeROSBaseCompleter(BaseCompleter):
    """
    Base class for autocompletion
    """

    def __init__(self, resource_url: str) -> None:
        """Initialize the completer with resource url

        Args:
            resource_url (str): resource url to get the list for autocompletion
        """
        super().__init__()
        self.token = ''
        self.url = resource_url

    def __call__(self, **kwargs):
        return self.get_data_for_completion()

    def cache_data(self, data):
        """
        Cache the data for autocompletion
        """
        pass

    def get_data_for_completion(self) -> list:
        """
        Return the list of data for autocompletion
        """
        return NotImplementedError

    def call_api(self, url=None):
        """
        Call the API server to get the list for autocompletion
        """
        config = KuberosConfig.get_current_config()

        if url is None:
            url = self.url

        try:
            resp = requests.request('GET',
                                    f"{config['server']}/{url}",
                                    headers={
                                        'Authorization': 'Token ' + config['token']},
                                    timeout=3)
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
                print(
                    "[Unauthorized '401'] Login is required. The cached token is expired.")

            if err_type == 404:
                # Requested resource not found
                print("[Not Found '404'] Check the resource name and try again.")

            if err_type == 500:
                print(
                    "[Internal Server Error '500'] Please contact the administrator.")

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


class CommandGroupBase:
    """
    Base class for command group
    """

    COMMAND_LIST = []

    def __init__(self, subparsers, group_name) -> None:
        self.parser = subparsers.add_parser(group_name,
                                            help="Configure KubeROS CLI")
        self.subparsers = self.parser.add_subparsers(dest='subcommand',
                                                     help=f'config command: {self.COMMAND_LIST}')

        self.commands = {}
        for command in self.COMMAND_LIST:
            self.commands.update({
                command: self.subparsers.add_parser(command)
            })

    def run(self, *args):
        """
        Run the subcommand
        """
        if len(args) > 0:
            parsed_args = self.parser.parse_args(args)
            getattr(self, parsed_args.subcommand)(*args[1:])
        else:
            self.print_help()

    def call_api(self,
                 method: str,
                 url: str,
                 data=None,
                 json_data=None,
                 files=None,
                 headers=None,
                 auth_token=None):
        """
        Private method to call the API server
        Args:
            method (str): 'CREATE', 'GET', 'PUT', 'DELETE
            url (str): endpoint url
            data (dict, optional): data
            files (_type_, optional): yaml files. Defaults to None.
            headers (dict, optional): headers. Defaults to None.
            auth_token (str, optional): user token. Defaults to None.

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
            resp = requests.request(method,
                                    url,
                                    data=data,
                                    json=json_data,
                                    files=files,
                                    headers=headers,
                                    timeout=5)
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
                print(
                    "[Unauthorized '401'] Login is required. The cached token is expired.")

            if err_type == 404:
                # Requested resource not found
                print("[Not Found '404'] Check the resource name and try again.")

            if err_type == 500:
                print(
                    "[Internal Server Error '500'] Please contact the administrator.")

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

    def print_help(self):
        print("To be implemented")
