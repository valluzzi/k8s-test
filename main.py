from kubernetes import client,config,utils

def main():
    config.load_kube_config()
    k8s_client = client.ApiClient()
    yml = 'conf/nginx.yml'
    utils.create_from_yaml(k8s_client, yml, verbose=True)

if __name__ == "__main__":
    main()