
# Summary
help_text_summary = '''KubeROS Command Line Interface

Usage: 
    kuberos <command> [<subcommand>] [<args]

Basic Commands:

    deploy       Deploy an ROS2 application
    status       Display the status of the deployment request
    delete       Delete deployed application via file or deployment name/uuid
    upgrade      Upgrade an existing deployment -> TODO
    check        Check the deployment request -> TODO
    
Management Commands:

    apply        Update the inventory, fleet description
    
    deployment 
        list     List all deployments
        status   Get a deployment by name
        delete   Delete a deployment by the name (BE CAREFUL!!! ONLY FOR DEV PURPOSES)
    
    fleet   
        list     Get the list of fleets   GET 
        status   Get a fleet by name      GET 
        create   Build a new fleet (Fleet name must be unique)    POST
                 -f --fleet_manifest: fleet manifest file
        update   Update a fleet with fleet description   PATCH 
        disband  Remove a fleet from Kuberos (remove all kuberos labels)    DELETE
                 
    cluster      Manage clusters
        register Register a new cluster to Kuberos  -- first step!   CREATE
        list     List all clusters   ***  GET
        update   Update a cluster inventory description
                 -f: inventory description file
        status   Get a cluster by the cluster name   *** GET 
                 args: -free-nodes-only   
                       -sync force sync with kubernetes
        
        reset    Reset the cluster (remove all kuberos labels)
        remove   Remove a cluster from Kuberos
        
    registry_token
        list     Get token list
        create   Add a new token to the registry (Once token is created, it cannot be read anymore)
        update   Update a token (If you forget, you can replace it with a new one)
        delete   Delete a token
        attach   Attach a token to a new cluster (A service account with appropriate role is required.)
        remove
        
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
    register Register a new cluster to Kuberos  -- first step!   CREATE
    list     List all clusters   ***  GET
    update   Update a cluster inventory description
                -f: inventory description file
    status   Get a cluster by the cluster name   *** GET 
                args: -free-nodes-only   
                    -sync force sync with kubernetes
    
    reset    Reset the cluster (remove all kuberos labels)
    remove   Remove a cluster from Kuberos
'''


### FLEET
fleet = '''Fleet Management Command
subcommand:
    list     Get the list of fleets   GET 
    status   Get a fleet by name      GET 
    create   Build a new fleet (Fleet name must be unique)    POST
                -f --fleet_manifest: fleet manifest file
    update   Update a fleet with fleet description   PATCH 
    disband  Remove a fleet from Kuberos (remove all kuberos labels)    DELETE
'''


### DEPLOYMENT
deployment = '''Deployment Management Command
subcommand:
    list     List all deployments
    status   Get a deployment by name
    delete   Delete a deployment by the name (BE CAREFUL!!! ONLY FOR DEV PURPOSES)
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