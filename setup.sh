#!/bin/sh
# Run this script in the terminal (./setup.sh) to prepare for deployment using Cloud Code.
echo "Updating helm"
helm repo update
if [ -z "$1" ]
  then
    echo "Changing context to docker-desktop"
    kubectl config use-context docker-desktop
  else
    echo "Using existing Kubernetes context"
fi


echo "Installing spark operator (ignore name in use error)"
helm install my-spark-operator spark-operator-1.1.26_fixed.tgz  --create-namespace --namespace spark-operator --set webhook.enable=true || true
# If they ever fix the bug, then install newer operator
# https://github.com/GoogleCloudPlatform/spark-on-k8s-operator/issues/1404
#helm install my-spark-operator spark-operator/spark-operator  --create-namespace --namespace spark-operator --set webhook.enable=true || true
echo "Creating spark service account (ignore already exists error)"
kubectl create serviceaccount spark || true
kubectl create clusterrolebinding spark-role --clusterrole=edit --serviceaccount=default:spark --namespace=default || true
