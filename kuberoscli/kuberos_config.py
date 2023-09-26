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

    @classmethod
    def load_kuberos_config(cls) -> dict:
        """
        Load the cached authentication token and api server address
        """
        config_path = cls.get_config_path()

        # load the config file
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            os.mkdir(os.path.dirname(config_path))
            print(f'Config file not found in path: {config_path}')
            print("Create config folder in default path: ~/.kuberos/config ")
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

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config,
                           f,
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

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(new_config,
                           f,
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
            contexts = config['contexts']
            current_context = config['current-context']
        except KeyError:
            print("Error in config file, please check the config file")
            sys.exit(0)

        # get current context config
        current_config = None
        for con in contexts:
            if con['name'] == current_context:
                current_config = con
                break

        if current_config is None:
            print("No current context found")
            contexts_name = [con['name'] for con in contexts]
            print(f"Available contexts: {contexts_name}")
            sys.exit(1)

        return current_config

