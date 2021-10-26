# Example deployment of a GrafanaDataSource instance in a k8s/OCP environment


Using the scripts in this folder you can deploy a GrafanaDataSource instance for the IBM Spectrum Scale Performance Monitoring Bridge for Grafana running in container

```
oc adm policy add-cluster-role-to-user ibm-spectrum-scale-operator -z grafana-serviceaccount
oc apply -f grafana-bridge-datasource.yaml
oc describe GrafanaDataSource bridge-grafanadatasource

```

For complete deployment examples please check the project [Wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki)
