# Deploying Grafana instance for monitoring the IBM Spectrum Scale Container Native Storage Access(CNSA) in a k8s/OCP environment


Using the scripts in this folder you can deploy an Grafana instance in the project 'grafana-for-cnsa'

```
oc new-project grafana-for-cnsa
oc apply -f operator-group.yaml
oc apply -f grafana-operator-subscription.yaml
oc apply -f grafana-instance-for-cnsa.yaml

```

Alternatively you can install a Grafana instance using the OpenShift Container Platform web console. Please check the instructions described in the deployment examples stored in the project [Wiki](/docs/grafana_deployment_ocp.md)
