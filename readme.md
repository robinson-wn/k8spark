# Running a spark application in Docker and on Kubernetes
The simplest steps to run a spark application using Spark Operator are:
* Install Cloud Code ([IDE plugin](https://cloud.google.com/code/docs))
* [Install WSL2 on Windows (Windows only)](#Install-WSL2-on-Windows)
* [Install Docker for Desktop](https://docs.docker.com/desktop/)
* [Install Helm](https://helm.sh/docs/intro/install/)
* [Install the spark operator using Helm](#Install-the-spark-operator-using-Helm)
  * Run the setup.sh script in the terminal is preferred until [issue 1401](https://github.com/GoogleCloudPlatform/spark-on-k8s-operator/issues/1404) is fixed. 
    ```shell
    ./setup.sh)
    ```
* Press the Play button on the Run configuration in PyCharm to configure a Cloud Code configuration.

**If you do the above, then you don't need to read the following.**
Here's a bit more information.

# Install WSL2 on Windows
*Only needed for Windows operating system*.

On windows, I generally use WSL2 rather than the Windows command prompt, 
because nearly all Kubernetes and Docker examples and help are written for Linux scripts. 
Here are guides for the WSL2 install:
* [WSL for Windows 11](https://pureinfotech.com/install-wsl-windows-11/)
* [WSL for Windows 10 install](https://ubuntu.com/tutorials/install-ubuntu-on-wsl2-on-windows-10#1-overview)
* [Nick's old but good guide to WSL2](https://nickjanetakis.com/blog/a-linux-dev-environment-on-windows-with-wsl-2-docker-desktop-and-more)

Once installed, run all the scripts in the WSL2 (Ubuntu  terminal).
Note that your there will be **Kubernetes settings** in ~/.kube/config in WSL2 directories.

# Install the spark operator using Helm
Install Helm. See [Helm install](https://helm.sh/docs/intro/install/).
(On WSL2 or Linux, follow the Debian/Ubuntu section)
Run the included setup.sh script is simplest. It does the steps described in the following.

Update your local cache:
```shell
helm repo update
```
You can list your charts or those available with:
```shell
helm list -A
helm search repo
```

Ensure that you are using the correct context (local desktop or remote cluster)
```shell
kubectl config get-contexts
kubectl config use-context  docker-desktop
```

Install the operator and it's webhook. (If you set the sparkJobNamespace in the operator install, 
then the [namespace](https://kubernetes.io/docs/tasks/administer-cluster/namespaces-walkthrough/) must exist and it 
must match that specified in the SparkApplication yaml file.)
From the [Spark Operatior documentation](https://github.com/GoogleCloudPlatform/spark-on-k8s-operator/blob/master/docs/quick-start-guide.md)
You could do the following:
```shell
helm repo add spark-operator https://googlecloudplatform.github.io/spark-on-k8s-operator
helm install my-release spark-operator/spark-operator --create-namespace --namespace spark-operator --set webhook.enable=true
```
But **I recommend the following instead**. That's because if you want to use jupyter notebook with spark-operator
(or any other software that required exposed ports),
then you'll need a fixed version of the operator newer than 1.1.26. (See [issue 1401](https://github.com/GoogleCloudPlatform/spark-on-k8s-operator/issues/1404).)
You can install my fixed version (included herein), as follows:
```shell
helm install my-release spark-operator-1.1.26_fixed.tgz --create-namespace --namespace spark-operator --set webhook.enable=true
```


If necessary, you can uninstall a helm chart by referring to its name:
```shell
 helm uninstall my-release --namespace spark-operator
```
The name, my-release, is arbitrary; you can give it any name.


# Create Spark account
Ensure a spark service account, according to [RBAC guide](https://spark.apache.org/docs/latest/running-on-kubernetes.html).
```shell
kubectl create serviceaccount spark
kubectl create clusterrolebinding spark-role --clusterrole=edit --serviceaccount=default:spark --namespace=default
kubectl get serviceaccounts
```

### The following is unnecessary if you are using the Cloud Code ([IDE plugin](https://cloud.google.com/code/docs)).
The Clod Code plugin runs Docker and skaffold to perform these operations.

# Running a spark operator application
Run and then view an application. Here the application is spark_hello; refer to the name inside the yaml file.
```shell
kubectl apply -f resources/spark_hello.yaml
kubectl get sparkapplications spark-hello -o=yaml
kubectl describe sparkapplication spark-hello
```

# Get data off the driver
Assuming that the application wrote data to the driver (rather than mount a resource), the data can be copied to the local drive as follows:
```shell
#kubectl cp namespace/pod:remote_path local_path
kubectl cp default/gha-driver:/opt/spark/work-dir/result.json ./result.json
```

# Eventually, remove the spark application
```shell
kubectl get sparkapplications --all-namespaces
kubectl get deployments --all-namespaces
kubectl delete sparkapplications spark-hello
```

# Problems?
* You may need to remove the spark application to redeploy it.
```shell
delete sparkapplications spark-hello
```

# Cluster references
Development on Docker for Desktop with its local Docker registry is simpler than connecting to a remote cluster.
Various configurations require a hostname, which is simply **localhost** for running on a local Docker for Desktop cluster.
Below are guidelines for working with a remote (microk8s, GKE) cluster, which may be ignored if you are using a local cluster.
Local or remote cluster, you will need to [install the spark operator using Helm](#Install-the-spark-operator-using-Helm).

## microk8s privary registry
When using [microk8s](https://ubuntu.com/tutorials/install-a-local-kubernetes-with-microk8s#1-overview), 
the various configurations that require a hostname must reference the cluster manager hostname.
If you are using the [microk8s built-in registry](https://microk8s.io/docs/registry-built-in), ensure that you can access it from outside the cluster.
After enabling it, edit the cert.d directory includes the hosts.toml file which allows access via the cluster manager hostname. 
```shell
# /var/snap/microk8s/current/args/certs.d/
server = "http://HOSTNAME:32000"

[host."http://HOSTNAME:32000"]
  capabilities = ["pull", "resolve", "push"]
  plain-http = true
```
Do not use **localhost** with port forwarding; a [bug blocks access using localhost](https://github.com/docker/for-mac/issues/3611).

## Configure local Docker for microk8s built-in registry
In the Docker for Desktop settings (available from the Docker task icon), Docker Engine:
```shell
"insecure-registries" : ["HOSTNAME:32000"]
```
Where, HOSTNAME is the remote hostname.

## Images for microk8s built-in registry
Images in the yaml files (for the spark operator and skaffold) must refer to the hostname when using the built-in registry. 
```shell
apiVersion: "sparkoperator.k8s.io/v1beta2"
kind: SparkApplication
...
  image: "HOSTNAME:32000/k8sparkgha"
  # Always update the image
  imagePullPolicy: Always
```
```shell
apiVersion: skaffold/v2beta25
kind: Config
metadata:
  name: gha
build:
  tagPolicy:
    # Ensure that skaffold marks the image as latest
    sha256: {}
  artifacts:
  - image: HOSTNAME:32000/k8sparkgha
 ...
```
The image repository, for Cloud Code ([IDE plugin](https://cloud.google.com/code/docs)), 
should be the cluster manager hostname and registry port (when using the built-in registry).
```shell
HOSTNAME:32000
```

## Removing Images for microk8s built-in registry
Removing images from the microk8s built-in registry is not easy. 
See the prune.sh script, copied from [microk8s cheat sheet](https://www.devops.buzz/public/microk8s/cheat-sheet). 

## Accessing remote cluster services
Applications on the cluster are exposed through ports, which may be only accessible from within the cluster.
When using a remote cluster, use kubectl port-forward to access the cluster ports from your local computer. Here are some common ports:

Spark UI (at 4040)
```shell
kubectl port-forward  --namespace=default --address localhost service/gha-ui-svc 4040:4040
```
Kubernetes Dashboard (at 10443)
```shell
kubectl port-forward -n kube-system service/kubernetes-dashboard 10443:443
```
Kubernetes Docker private registry (at 32000); typically, unnecessary. Instead, use the cluster manager node in image references.
```shell
kubectl port-forward  --namespace=container-registry --address localhost service/registry 32000:5000
```

To access the Kubernetes Dashboard, you'll need to obtain a token. See the [dashboard instructions](https://microk8s.io/docs/addon-dashboard).
```shell
token=$(microk8s kubectl -n kube-system get secret | grep default-token | cut -d " " -f1)
microk8s kubectl -n kube-system describe secret $token
```

# Custom docker image
You can build your own Docker image to run custom spark applications.
Review this [explanation of using Spark Docker image on Kubernetes](https://levelup.gitconnected.com/spark-on-kubernetes-3d822969f85b).
Review the images on [datamechanics/spark](https://hub.docker.com/r/datamechanics/spark).
After editing your docker file, build your image. Below, it is tagged in preparation for uploading to GCP. 
Note, that you need to use your own project name instead of my (gcr.io/project1), for GCP.
Use your own account (login) ID instead MYID.
In any case, this works on a local Docker for Desktop. (See docker_build.sh)
```shell
docker build -t MYID/myk8spark:1.0 -t MYID/myk8spark:latest \
  -t gcr.io/project1/myk8spark:1.0 -t gcr.io/project1/myk8spark:latest .
```

After building the image, open a terminal to it to see that it's correct. (Your image name may be different.)
```shell
docker run -it myk8spark /bin/bash
```
Try your program, which will be in the location copied by the Dockerfile and referenced in the spark operator yaml file (mainApplicationFile).
```shell
$SPARK_HOME/bin/spark-submit k8spark/runpi.py
```

## Custom UI ports
If your application uses custom ports, you'll need to expose them.
See this explanation of [accessing the Spark UI on Kubernetes](https://kudo.dev/docs/runbooks/spark/submission.html#accessing-spark-ui).

# Using the Cloud Code plugin
The Cloud Code ([IDE plugin](https://cloud.google.com/code/docs)) can build and deploy the spark application.
* Ensure that the Deployment Configuration points to the correct image repository. 
  It is likley to be localhost:32000 (local cluster) or HOSTNAME:32000 (remote cluster) or some public repository (like DockerHub)
* Ensure that the Kubeconfig file setting is correct in the advanced Deployment Configuration 
* The skaffold file should (generally) use the sha256 tag so that new images are deployed.
