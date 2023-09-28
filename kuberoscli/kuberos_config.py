"""
KubeROS Config object to handle the config file
"""

import os
import sys
import yaml


class KuberosConfig:
    """
    Class to handle the Kuberos CLI config file
    """

    @staticmethod
    def get_config_path() -> str:
        """
        Get the path of the config file
        Default path:  ~/.kuberos/config
        """
        config_path = os.environ.get('KUBEROS_CONFIG', None)
        if config_path is None:
            config_path = '~/.kuberos/config'

        config_path = os.path.expanduser(config_path)
        return config_path

    @staticmethod
    def create_config_file(config_path: str):
        """
        Create a new config file
        """
        if os.path.isfile(config_path):
            print("Config file already exists")
        else:
            # check if the config folder exists
            if not os.path.isdir(os.path.dirname(config_path)):
                os.mkdir(os.path.dirname(config_path))

            # create the config file
            with open(config_path, "w", encoding="utf-8") as file:
                yaml.safe_dump({
                    'current-context': '',
                    'contexts': []
                },
                    file,
                    default_flow_style=False)
            print(f'Create config file in path: {config_path}')

    @classmethod
    def load_kuberos_config(cls) -> dict:
        """
        Load the cached authentication token and api server address
        """
        config_path = cls.get_config_path()

        if os.path.isfile(config_path):
            with open(config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)
        else:
            cls.create_config_file(config_path)
            print("Cannot find config file")
            print(f"create a new config file in default path: {config_path}")
            print("Please add a new context by using command: kuberos config create")
            sys.exit(1)

        return config

    @classmethod
    def update_config(cls,
                      context: dict = None,
                      current_context: str = None):
        """
        Update the local cli config file
        """
        config_path = cls.get_config_path()
        config = cls.load_kuberos_config()

        # update contexts
        if context is not None:
            # add new context
            if context['name'] not in cls.get_context_names():
                config['contexts'].append(context)
            else:
                # update context
                for con in config['contexts']:
                    if con['name'] == context['name']:
                        con.update(context)
                        break

        # update current context
        if current_context is not None:
            config['current-context'] = current_context

        with open(config_path, "w", encoding="utf-8") as file:
            yaml.safe_dump(config,
                           file,
                           default_flow_style=False)
        # print('Update config file success')

    @classmethod
    def delete_context(cls,
                       context_name: str):
        """
        Delete a context from local config file
        """
        config = cls.load_kuberos_config()
        config_path = cls.get_config_path()

        new_config = {
            'current-context': config['current-context'],
            'contexts': [],
        }

        for con in config['contexts']:
            if con['name'] != context_name:
                new_config['contexts'].append(con)

        with open(config_path, "w", encoding="utf-8") as file:
            yaml.safe_dump(new_config,
                           file,
                           default_flow_style=False)

    @classmethod
    def get_context_names(cls) -> list:
        """
        Get the list of context names
        """
        config = cls.load_kuberos_config()
        return [con['name'] for con in config['contexts']]

    @classmethod
    def get_current_config(cls) -> dict:
        """
        Get config of the current context
        """

        config = cls.load_kuberos_config()

        try:
            current_context = config['current-context']
        except KeyError:
            print("Error in config file, please check the config file")
            print(f"Config file path: {config}")
            print("Quick fix: delete the config file and create a new context using command: kuberos config create")
            sys.exit(0)

        # get current context confi
        current_config = cls.get_context_by_name(current_context)

        return current_config

    @classmethod
    def get_context_by_name(cls,
                            ctx_name: str) -> dict:
        """
        Get the context config by name

        Args:
            ctx_name (str): context name

        Returns:
            ctx_config (dict): context config
        """
        config = cls.load_kuberos_config()
        ctx_config = None

        try:
            contexts = config['contexts']
        except KeyError:
            print("Error in config file, please check the config file")
            print(f"Config file path: {config}")
            print("Quick fix: delete the config file and \
                create a new context using command: kuberos config create")
            sys.exit(0)

        for con in contexts:
            if con['name'] == ctx_name:
                ctx_config = con
                break

        if ctx_config is None:
            print(f"Context [{ctx_name}] not found")
            contexts_name = [con['name'] for con in contexts]
            print(f"Available contexts: {contexts_name}")
            sys.exit(1)

        return ctx_config
