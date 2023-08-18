
# Summary
help_text_summary = '''KubeROS Command Line Interface

Usage:
    kuberos <command> [<subcommand>] [<args]

Basic Commands:

    deploy       Deploy an ROS2 application
    list         List all deployments
    info         Display the status of the deployment request
    delete       Delete deployed application via file or deployment name
    upgrade      Upgrade an existing deployment -> TODO
    check        Check the deployment request -> TODO
    
Management Commands:

    apply        Update the inventory, fleet description
    
    fleet   
        list     Get the list of fleets
        info     Get a fleet by name
        create   Build a new fleet (Fleet name must be unique)
                 -f --fleet_manifest: fleet manifest file
        update   Update a fleet with fleet description
        delete   Remove a fleet from Kuberos (remove all kuberos labels)
                 
    cluster      Manage clusters
        create   Register a new cluster to Kuberos 
                    -f: cluster registration yaml file
        list     List all clusters
        update   Update a cluster inventory description
                    -f: cluster inventory file
        delete   Remove a cluster from Kuberos
        
    deployment 
        force_delete   Delete a deployment by the name (BE CAREFUL!!! ONLY FOR DEV PURPOSES)
    
    registry_token
        list     Get token list
        create   Add a new token to the registry (Once token is created, it cannot be read anymore)
        update   Update a token (If you forget, you can replace it with a new one) -> Deprecated
        delete   Delete a token -> TODO
        attach   Attach a token to a new cluster (A service account with appropriate role is required.)
        
    repository   
        read     Add a new repository to the registry
        get      
        update
        delete
    
    repo 
        list rosmodules 
        list deployment
        search -name 
        
    device 
        list 
        search 
        add 
        remove
        
Setting Commands:
    login        Login to the Kuberos server and save the token to ~/.kuberos/config
    info         Display Kuberos cluster information
    config       
        get      Get the current config
        set_default_fleet  
        
ROS Introspection Commands (Experimental):
    # require current deployment is set in the config file
    topic
        list     List all topics
        echo     Echo a topic
        

Advanced Commands:
    bridges
    public_cloud 
    vpn

Global Settings:
    --config     Kuberos config file (default is $HOME/.kuberos/config)
    --output     Output format (default is table. 'yaml'/'dict')
'''


# INFO
info = '''Get Kuberos Cluster Information
Usage: 
    # print the address of API server, status and software version
    kuberos cluster_info'''


# CLUSTER
cluster = '''Clusters Management Command
subcommand:
    create   Register a new cluster to Kuberos 
                -f: cluster registration yaml file
    list     List all clusters   ***  GET
    update   Update a cluster inventory description
                -f: cluster inventory file
    info     Get a cluster by the cluster name   *** GET 
                -sync force sync with kubernetes
    delete   Remove a cluster from Kuberos

'''


### FLEET
fleet = '''Fleet Management Command
subcommand:
    list     Get the list of fleets
    info     Get a fleet by name
    create   Build a new fleet (Fleet name must be unique)    POST
                -f --fleet_manifest: fleet manifest file
    update   Update a fleet with fleet description   PATCH 
    delete   Remove a fleet from Kuberos (remove all kuberos labels)    DELETE
'''


### DEPLOYMENT
deployment = '''Deployment Management Command
subcommand:
    list     List all deployments
    status   Get a deployment by name
    delete   Delete a deployment by the name (BE CAREFUL!!! ONLY FOR DEV PURPOSES)
'''

### BATCH JOB
BATCH_JOB = '''
Batch Job Management Command
subcommand:
    list     List all batchjob 
    status   Get a batchjob by name
    delete   Delete a batchjob by the name
'''

### REGISTRY TOKENS  
# TODO
registry_token = '''Registry Token Management Command
subcommand:
    list     Get token list
    create   Add a new token to the registry (Once token is created, it cannot be read anymore)
    update   Update a token (If you forget, you can replace it with a new one)
    delete   Delete a token
    attach   Attach a token to a new cluster (A service account with appropriate role is required.)
    remove
'''