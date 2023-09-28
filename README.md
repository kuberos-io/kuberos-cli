# KubeROS Command Line Tool

This repo contains the cli tools for users to interact with KubeROS platform. 

## Installation

There are three methods to install the cli tool.


### 1. Install in local path
KubeROS CLI tool depends only on the following common packages, it should not cause the compatibility problem with other packages.
 - argcomplete
 - PyYAML
 - requests
 - tabulate

Required python version: `python >= 3.8`
```bash
# install python3-pip
sudo apt update
sudo apt install python3-pip
```


**Optional 1**: install this system-wide

The python packages will be installed in `/usr/lib/python3/dist-packages`

The `kuberos` script will be installed in `/usr/local/bin`

```bash
# Instal KubeROS CLI
sudo pip install --system kuberos-cli
# enable autocompletion
activate-global-python-argcomplete
```

**Opotion 2**: using the default [User Scheme](https://pip.pypa.io/en/stable/user_guide/#user-installs)

The packages are installed in `~/.local/lib/python3/`

The executable scripts are in `~/.local/bin`

In this case, you have to add the `~/.local/bin` to the `$PATH`
```bash
# Instal KubeROS CLI
pip install kuberos-cli

# export ~/.local/bin to $PATH in .bashrc or .bash_profile
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
source ~/.bashrc

# enable autocompletion
activate-global-python-argcomplete
```



### 2. Install in Virtual Environment (Venv)

You can install this CLI tool in an isolated Python environment with [venv](https://docs.python.org/3/library/venv.html) to avoid interfering with other projects due to dependencies.

Create a `Venv` and add the `venv/bin` to `$PATH`
```bash
sudo apt update
sudo apt install python3-venv

# create a virtual environment
cd <work directory>
python3 -m venv kuberos_cli_venv

# add the kuberos_cli_venv/bin to PATH
cd kuberos_cli_venv/bin
pwd # get the absolute path <local-bin-path-in-venv>

# replace the <local-bin-path-in-venv> with the path printed above 
# add it to .bashrc, or another profile depending on the terminal tool you are using
echo 'export PATH=$PATH:<local-bin-path-in-venv>' >> ~/.bashrc
```

Install `kuberos-cli` with `pip`:
```bash
pip install kuberos-cli
# enable autocompletion gobally
activate-global-python-argcomplete
```


### 3. From source (For Development)

```bash
git clone https://github.com/kuberos-io/kuberos-cli.git
cd kuberos-cli
pip install -r requirements.txt
# build it (optional)
python3 -m build
pip3 install -U .
# enable arg auto completion
eval "$(register-python-argcomplete kuberos)"
# override the python path to use the library from source
echo $PYTHONPATH=$PYTHONPATH:<path-to-source-code> # e.g. ~/ws/kuberos-cli
```


## Usage
This CLI tool follows the conventions of the `ROS2 CLI` and uses the following style.
```bash
kuberos <command_group> <command> [name] [-args]
```
You can get the help for each command group with `kuberos <command_group> -h` or just type `kuberos <command_group>`.

For example, to deploy, check and delete deployments, you can use following commands:
```bash
# Create a deployment 
kuberos deploy create -f <path-to-deployment-manifest>
# List all deployments
kuberos deploy list
# Get the deployment status 
kuberos deploy info <deployment-name> 
# Delete a deployment
kuberos deploy delete <deployment-name>
```


### Examples

Get the cluster status using `kuberos cluster info -s -u <cluster-name>`. 
```t
Cluster Name: kube
API Server: https://<api-server>:6443
Alive Age: 1 month, 1 week
Since Last Sync: 0 minutes

Robot Onboard Computers
--------------------------------------------------------------------------------
ROBOT_NAME    HOSTNAME        DEVICE_GROUP    IS_ALIVE    AVAILABLE    FLEET    PERIPHERALS
simbot-2      kube-simbot-02  simbot-pc       True        False        xx       ['rs-d435']
simbot-1      kube-simbot-01  simbot-pc       True        False        xx       ['rs-d435']

Edge Nodes
--------------------------------------------------------------------------------
HOSTNAME             GROUP    SHARED RESOURCE    IS_ALIVE    AVAILABLE    REACHABLE
kube-edge-worker-02  public   True               True        True         True
kube-edge-worker-01  public   True               True        True         True
kube-edge-worker-03  public   True               True        True         True
kube-edge-worker-04  public   True               True        True         True
kube-storage         storage  True               True        True         True

Control Plane Nodes
--------------------------------------------------------------------------------
HOSTNAME     ROLE           REGISTERED    IS_ALIVE    AVAILABLE    REACHABLE
kube-master  control_plane  True          True        False        True

Resource Usages
--------------------------------------------------------------------------------
HOSTNAME             CPU (Cores)    Memory (Gb)        Storage (Gb)
kube-edge-worker-02  0.04/4 (0.9%)  1.99/8.1 (24.4%)   N/A/40.5
kube-master          0.12/4 (3.0%)  4.37/8.1 (53.7%)   N/A/12.3
kube-simbot-02       0.06/4 (1.5%)  3.77/8.1 (46.4%)   N/A/40.5
kube-edge-worker-01  0.04/8 (0.5%)  3.98/16.4 (24.3%)  N/A/50.6
kube-simbot-01       0.04/8 (0.4%)  2.81/16.4 (17.1%)  N/A/50.6
kube-edge-worker-03  0.04/8 (0.5%)  3.46/16.4 (21.1%)  N/A/40.5
kube-edge-worker-04  0.04/8 (0.5%)  3.10/16.4 (18.9%)  N/A/50.6
kube-storage         0.03/4 (0.7%)  2.94/8.1 (36.1%)   N/A/203.1
```


For example, check the status of the target fleet before deploying a new application with `kuberos fleet info example-fleet`. 

```t
Fleet Name: example-fleet
Healthy: True
Fleet status: idle
Alive Age: 15 hours, 14 minutes
Main Cluster: kube
Description: Test fleet
Created since: 15 hours, 14 minutes
========================================
Robot Name      Id  Hostname        Computer Group    Reachable    Status      Shared Resource
simbot-1         1  kube-simbot-01  simbot-pc         True         deployable  False
simbot-2         2  kube-simbot-02  simbot-pc         True         deployable  False
```


