# Example deployment of a GrafanaDataSource instance in a k8s/OCP environment


Using the scripts in this folder you can deploy a GrafanaDataSource instance for the IBM Spectrum Scale Performance Monitoring Bridge for Grafana running in in the project 'grafana-for-cnsa'

```
NAMESPACE=grafana-for-cnsa
```
```
echo $NAMESPACE
```
```
oc adm policy add-cluster-role-to-user ibm-spectrum-scale-operator -z grafana-serviceaccount
```
```
oc apply -f grafana-bridge-datasource.yaml --namespace=$NAMESPACE
```
```
oc describe GrafanaDataSource bridge-grafanadatasource --namespace=$NAMESPACE
```

For complete deployment examples please check the project [Wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki)
