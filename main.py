from kubernetes import client,config
import os, yaml
from datetime import datetime
import time


def create_pod(pod_manifest, namespace):
    """
    create_pod
    """
    if os.path.isfile(pod_manifest):
        with open(pod_manifest) as stream:
            pod_manifest = yaml.safe_load(stream)

    api_instance = client.CoreV1Api()
    pod_name = pod_manifest['metadata']['name']
    pod_name = datetime.now().strftime(f"{pod_name}-%Y%m%d%H%M%S")
    pod_manifest['metadata']['name'] = pod_name
    print(f"Creating pod {pod_name}...")
    try:
        # Try creating the pod
        pod = api_instance.create_namespaced_pod(body=pod_manifest, namespace=namespace)
        print(f"Pod '{pod_name}' created.")
    except client.rest.ApiException as ex:
        print(f"Unknown error:{ex}")
    
    while pod.status.phase == "Pending":
        print(f"{pod.status.phase}...")
        pod = api_instance.read_namespaced_pod(name=pod_name, namespace=namespace)
        time.sleep(0.5)

    try:
        logs = api_instance.read_namespaced_pod_log(name=pod_name, namespace=namespace, follow=True, _preload_content=False)
        for line in logs.stream():
            print(line.decode('utf-8'))
    except client.rest.ApiException as e:
        print(f"Exception when retrieving Pod logs: {e}")

    # delete the pod
    try:
        api_instance.delete_namespaced_pod(name=pod_name, namespace=namespace, body=client.V1DeleteOptions())
        print(f"Pod '{pod_name}' deleted.")
    except client.rest.ApiException as ex:
        print(f"Exception when deleting Pod: {e}")

def main():
    """
    main function
    """
    config.load_kube_config()
    pod_manifest = 'conf/gdal.yml'
    create_pod(pod_manifest, namespace="default")

if __name__ == "__main__":
    main()