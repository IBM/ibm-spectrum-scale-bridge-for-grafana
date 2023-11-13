# Example deployment of a GrafanaDatasource instance in a k8s/OCP environment


Using the scripts in this folder you can deploy a GrafanaDatasource instance for the IBM Storage Scale Performance Monitoring Bridge for Grafana running in in the project 'grafana-for-cnsa'

```shell
NAMESPACE=grafana-for-cnsa
```
```shell
echo $NAMESPACE
```
```shell
oc label namespace $NAMESPACE scale.spectrum.ibm.com/networkpolicy=allow
```
```shell
oc adm policy add-cluster-role-to-user ibm-spectrum-scale-operator -z grafana-for-cnsa-sa
```
```shell
oc apply -f bridge-tls-secret-v5.yaml
```
```shell
TLS_CERT=`oc get secret ibm-spectrum-scale-grafana-bridge-service-cert -n ibm-spectrum-scale -o json |jq '.data["tls.crt"]' | tr -d \"`
```
```shell
TLS_KEY=`oc get secret ibm-spectrum-scale-grafana-bridge-service-cert -n ibm-spectrum-scale -o json |jq '.data["tls.key"]' | tr -d \"`
```
```shell
oc get secrets grafana-bridge-tls-cert -n $NAMESPACE -o json \
 | jq ".data[\"tls.key\"] |= \"$TLS_KEY\"" | jq ".data[\"tls.crt\"] |= \"$TLS_CERT\""| oc apply -f -
```
```shell
oc apply -f grafana-bridge-datasource-v5.yaml --namespace=$NAMESPACE
```
```shell
oc describe GrafanaDatasource bridge-grafanadatasource --namespace=$NAMESPACE
```

For complete deployment examples please check the project [Wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki)
