#!/bin/sh
# Run this script in the terminal (./setup.sh) to prepare for deployment using Cloud Code.
echo "Updating helm"
helm repo add spark-operator https://kubeflow.github.io/spark-operator
helm repo update

if [ -z "$1" ]
  then
    echo "Changing context to docker-desktop"
    kubectl config use-context docker-desktop
  else
    echo "Using existing Kubernetes context"
fi

echo "Installing spark operator (ignore name in use error)"
helm install my-spark-operator spark-operator/spark-operator \
  --namespace spark-operator \
  --create-namespace \
  --set webhook.enable=true

echo "Creating spark service account (ignore already exists error)"
kubectl create serviceaccount spark || true
kubectl create clusterrolebinding spark-role --clusterrole=edit --serviceaccount=default:spark --namespace=default || true
