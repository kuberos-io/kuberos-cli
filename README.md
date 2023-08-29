# KubeROS Command Line Interface Tools

This repo contains the cli tools for users to interact with KubeROS platform. 

## Setup

```bash
pip install -r requirements.txt
chmod +x kuberos.py
```

## Basic Commands
To deploy, delete, update and monitor deployments, KubeROS provides the following short commands with the style `./kuberos.py <verb> <-args>`.
```bash
# Create a deployment 
./kuberos.py deploy -f <path-to-deployment-manifest>
# List all deployments
./kuberos.py list
# Get the deployment status 
./kuberos.py info <deployment name> 
# Delete a deployment
./kuberos.py delete <deployment name>
```


## Management Commands

KubeROS follows the style of ROS2 CLI. Run `kuberos.py` or `kuberos --help` to get all available commands.

```bash
kuberos <command> <verb> <-args>
```


Get the cluster status using `./kuberos.py cluster info -sync <cluster-name>`. 
```t
Cluster Name: kube
API Server: https://<api-server-ip>:6443
Alive Age: 4 minutes
Since Last Sync: 0 minutes


Robot Onboard Computers
--------------------------------------------------------------------------------
ROBOT_NAME    HOSTNAME        DEVICE_GROUP    AVAILABLE    FLEET    PERIPHERALS
simbot-1      kube-simbot-01  simbot-pc       True         N/A      ['rs-d435']
simbot-2      kube-simbot-02  simbot-pc       True         N/A      ['rs-d435']


Edge Nodes
--------------------------------------------------------------------------------
HOSTNAME             GROUP    SHARED RESOURCE    AVAILABLE    REACHABLE
kube-edge-worker-01  public   True               True         True
kube-edge-worker-02  public   True               True         True


Control Plane Nodes
--------------------------------------------------------------------------------
HOSTNAME     ROLE           REGISTERED    AVAILABLE    REACHABLE
kube-master  control_plane  True          False        True
```


For example, check the status of the target fleet before deploying a new application. 

```t
./kuberos.py fleet info iras-fleet

Fleet Name: iras-fleet
Healthy: True
Fleet status: pending
Alive Age: N/A
Main Cluster: iras-k8s
Description: Test mini fleet in the lab
Created since: 16 hours, 37 minutes
========================================
Robot Name      Id  Hostname        Computer Group    Status      Shared Resource
simbot-1         1  iras-irl1-lin   simbot-pc         deployable  False
simbot-2         2  iras-irl4-lin   simbot-pc         deployable  False
```


## TODOs: 
 - [ ] Separate the code into subcommand modules, similiar to ros2cli 
 - [ ] Add auto-completion


## Issues: 
 - If you run this script inside a devcontainer, it will not be able to reach localhost. Since this script has only a few dependencies, you can use it with the local Python interpreter.


### Enable auto completion
Due to unknown bugs, it currently doesn't work inside the devContainer. A working example, cli_autocomplete_test.py, has been added as a reference for future implementation

```
eval "$(register-python-argcomplete my_cli_tool.py)"
```
