# KubeROS Command Line Interface Tools

This repo contains the cli tools for users to interact with KubeROS platform. 

## Usage
This tool follows the style of ROS2 CLI. Run `kuberos.py` or `kuberos --help` to get all available commands.
```
kuberos <command> <verb> <-args>
```

For example, to list all active deployed applications: 
```
kuberos deployment list 
```
Check the status of the target fleet before deploying a new application. 

```
./kuberos.py fleet status bw1-fleet

Fleet Name: bw1-fleet
Active: True
Main Cluster: bw1-prod-cluster
Description: Test Fleet on BwCloud 1
========================================
Robot Name      Id  Hostname         Computer Group    Status      Shared Resource
simbot-1         1  k8s-sim-robot-1  simbot-pc         deployable  False
simbot-2         2  k8s-sim-robot-2  simbot-pc         deployable  False

```
## TODOs: 
 - Separate the code into subcommand modules, similiar to ros2cli 
 - Add auto-completion

## Issues: 
 - If you run this script inside a devcontainer, it will not be able to reach localhost. Since this script has only a few dependencies, you can use it with the local Python interpreter.


### Enable auto completion
Due to unknown bugs, it currently doesn't work inside the devContainer. A working example, cli_autocomplete_test.py, has been added as a reference for future implementation

```
eval "$(register-python-argcomplete my_cli_tool.py)"
```