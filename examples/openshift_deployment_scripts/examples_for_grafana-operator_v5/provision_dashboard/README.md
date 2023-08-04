# Example of a simple dashboard provisioning to your Grafana instance running in a k8s/OCP environment


Using the scripts in this folder you can provision an example dashboard to the Grafana instance running in the project 'grafana-for-cnsa'

```shell
NAMESPACE=grafana-for-cnsa
```
```shell
echo $NAMESPACE
```
```shell
oc apply -f cnsa-cluster-simple-dashboard-v5.yaml --namespace=$NAMESPACE
```
