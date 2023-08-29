#!/usr/bin/env python3

import os
import paramiko
import stat


class CollectFilesSSH():
    
    def __init__(self,
                ssh_key_path: str,
                 port: int = 22,
                 ) -> None:
        
        self._port = port
        self._ssh_key = paramiko.RSAKey(filename=ssh_key_path)
        self._ssh_client = paramiko.SSHClient()
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
    def collect_one(self,
                    host: str,
                    username: str,
                    remote_folder: str,
                    local_folder: str):
        
        self._ssh_client.connect(host,
                                 self._port,
                                 username,
                                 pkey=self._ssh_key)
        
        sftp_client = self._ssh_client.open_sftp()

        self.recursive_download(sftp_client, remote_folder, local_folder)

        sftp_client.close()
        self._ssh_client.close()

    def recursive_download(self, sftp_client, remote_folder, local_folder):
        """
        Recursively download files and folders from a remote folder 
        to a local folder.

        :param remote_folder: Path to remote folder
        :param local_folder: Path to local folder
        """
        os.makedirs(local_folder, exist_ok=True)

        # list items in remote folder
        remote_items = sftp_client.listdir_attr(remote_folder)

        for item in remote_items:
            remote_path = os.path.join(remote_folder, item.filename)
            local_path = os.path.join(local_folder, item.filename)

            if stat.S_ISDIR(item.st_mode):
                self.recursive_download(sftp_client = sftp_client,
                                        remote_folder=remote_path,
                                        local_folder=local_path)

            else:
                sftp_client.get(remote_path, local_path)
                print(f"Copied {remote_path} to {local_path}")

