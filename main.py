import os
import time
import yaml
import re
from kubernetes import client, config
import shlex, logging
from datetime import datetime


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


def manifest_from_file(fileyml):
    """
    manifest_from_file
    """
    pod_manifest = None
    print(fileyml, os.path.isfile(fileyml))
    if os.path.isfile(fileyml):
        with open(fileyml) as stream:
            pod_manifest = yaml.safe_load(stream)
            #patch the name
            name = pod_manifest["metadata"]["name"]
            pod_name = datetime.now().strftime(f"{name}-%Y%m%d%H%M%S")
            pod_manifest["metadata"]["name"] = pod_name

    return pod_manifest


def create_manifest(image):
    """
    create_manifest
    """
    # image = "docker.io/valluzzi/gdal:latest"
    name = image.split("/")[-1].split(":")[0]

    pod_name = datetime.now().strftime(f"{name}-%Y%m%d%H%M%S")

    pod_manifest = {
        "apiVersion": "v1", 
        "kind": "Pod", 
        "metadata": {
            "name": pod_name, 
            "labels": {
                "run": name
            }
        }, 
        "spec": {
            "containers": [
                {
                    "image": image, 
                    "name":  name, 
                    "command": ["gdalinfo"], 
                    "args": ["--version"]
                }], 
            "dnsPolicy": "ClusterFirst", 
            "restartPolicy": "Never"
        }
    }
    return pod_manifest


def create_pod(command):
    """
    create_pod
    """
    args = shlex.split(command)
    command = args[0]
    args = args[1:]

    pod_manifest = manifest_from_file(f"./conf/{command}.yml")
    pod_name = pod_manifest["metadata"]["name"]
    pod_manifest["spec"]["containers"][0]["command"] = [command, ]
    pod_manifest["spec"]["containers"][0]["args"] = args
    
    api_instance = client.CoreV1Api()

    LOGGER.debug(f"Creating pod {pod_name}...")
    try:
        # Try creating the pod
        pod = api_instance.create_namespaced_pod(body=pod_manifest, namespace="default")
        LOGGER.debug(f"Pod '{pod_name}' created.")
        return pod
    except client.rest.ApiException as ex:
        LOGGER.error(f"Unknown error:{ex}")
        return None
    

def parse_progress(line):
    """
    parse_progress - parse a log line in search for a progress percentage
    """
    if line:
        # match percentage in the line 
        # regexp with named group 'percentage'
        m=re.match(r".*?(?P<percent>\d+(\.\d*)?)\s*%.*?", line)
        percent = m.group("percent") if m else -1
        return float(percent)
    return -1


def read_log(pod, close=False):
    """
    read_log
    """
    res = ""
    try:
        if pod and pod.metadata:
            api_instance = client.CoreV1Api()
            pod_name = pod.metadata.name
            namespace = pod.metadata.namespace
            # wait for the pod to be running
            while pod.status.phase == "Pending":
                LOGGER.debug(f"{pod.status.phase}...")
                pod = api_instance.read_namespaced_pod(name=pod_name, namespace=namespace)
                time.sleep(0.5)
            # get the pod logs
            logs = api_instance.read_namespaced_pod_log(name=pod_name, namespace=namespace, follow=True, _preload_content=False)
            for line in logs.stream():
                line = line.decode('utf-8')
                p = parse_progress(line)
                if p>=0:
                    print(f"{p}%")
                res += line

            if close:
                api_instance.delete_namespaced_pod(name=pod_name, namespace=namespace, body=client.V1DeleteOptions())
                LOGGER.debug(f"Pod '{pod_name}' deleted.")
    
    except client.rest.ApiException as ex:
        LOGGER.error(f"Exception when retrieving Pod logs: {ex}")
    return res


def delete_pod(pod):
    """
    delete_pod
    """
    res = False
    if pod and pod.metadata:
        pod_name = pod.metadata.name
        namespace = pod.metadata.namespace
        api_instance = client.CoreV1Api()
        try:
            api_instance.delete_namespaced_pod(name=pod_name, namespace=namespace, body=client.V1DeleteOptions())
            LOGGER.debug(f"Pod '{pod_name}' deleted.")
            res = True
        except client.rest.ApiException as ex:
            LOGGER.error(f"Exception when deleting Pod: {ex}")

    return res


def execute(command):
    """
    execute
    """
    pod = create_pod(command)
    return read_log(pod, True)
    



def main():
    """
    main function
    """
    config.load_kube_config()
    #fileyml = 'conf/timec.yml'
    output = execute("python main.py 100")
    print(output)

if __name__ == "__main__":
    main()