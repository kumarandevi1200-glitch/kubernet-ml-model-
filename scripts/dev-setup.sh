#!/bin/bash
set -e

echo "Starting dev-setup..."

echo "Starting Minikube..."
minikube start --memory 8192 --cpus 4 --driver=docker

echo "Enabling Minikube addons..."
minikube addons enable metrics-server
minikube addons enable ingress

echo "Adding Helm repos..."
helm repo add kedacore https://kedacore.github.io/charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

echo "Installing KEDA..."
helm upgrade --install keda kedacore/keda --namespace keda --create-namespace

echo "Installing Prometheus/Grafana..."
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace

echo "Installing Redis..."
helm upgrade --install redis bitnami/redis --set auth.enabled=false --namespace ml-serving --create-namespace

echo "Dev setup complete."
