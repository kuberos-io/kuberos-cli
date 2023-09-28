
class Endpoints:
    """
    Kuberos API endpoints
    """
    # Deploying
    DEPLOYING = 'api/v1/deploying/deploy_rosmodule/'

    # Batch job
    BATCH_JOB = 'api/v1/batch_jobs/batch_jobs/'
    BATCH_DATA = 'api/v1/batch_jobs/data_management/'

    # Auth
    LOGIN = 'api/v1/auth/user_login/'
    LOGOUT = 'api/v1/auth/user_logout/'
    REGISTER = 'api/v1/auth/user_register/'

    # Fleet
    FLEET = 'api/v1/fleet/manage_fleet/'

    # Cluster Management
    CLUSTER = 'api/v1/cluster/clusters/'
    CLUSTER_INVENTORY = 'api/v1/cluster_operating/cluster_inventory_management/'

    # Deployment
    DEPLOYMENT = 'api/v1/deployment/deployments/'

    # Registry token
    REGISTRY_TOKEN = 'api/v1/cluster/container_registry_access_tokens/'
    REGISTER_TOKEN_TO_CLUSTER = 'api/v1/cluster_operating/container_registry_access_token/'