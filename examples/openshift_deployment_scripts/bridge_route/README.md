# Example deployment of the Route for a grafana-bridge running in a k8s/OCP environment


In some situations an instance of the IBM Storage Scale Performance Monitoring Bridge for Grafana (grafana-bridge), running inside of a k8s/OCP environment, needs to be connected to a Grafana instance running outside of this k8s/OCP environment. In this case a Route needs to be created for a service that exposes the grafana-bridge deployment.
Using the script in this folder you can deploy a Route instance for the grafana-bridge service. 

1. Get grafana-bridge application namespace

```
# BRIDGE_APP_NAMESPACE=`oc get deployment  --all-namespaces -o json |jq '.items[] |select(.metadata.name | contains("grafana-bridge"))| .spec.selector.matchLabels."app.kubernetes.io/instance" '| tr -d \"`

# echo $BRIDGE_APP_NAMESPACE
ibm-spectrum-scale
```

2. Get grafana-bridge application name

```
# BRIDGE_APP_NAME=`oc get deployment --all-namespaces -o json |jq '.items[] |select(.metadata.name | contains("grafana-bridge"))| .spec.selector.matchLabels."app.kubernetes.io/name" ' | tr -d \" `

# echo $BRIDGE_APP_NAME
grafanabridge
```

3. Get grafana-bridge application service name

```
# oc get svc --all-namespaces -l app.kubernetes.io/name=$BRIDGE_APP_NAME
NAME                                TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)    AGE
ibm-spectrum-scale-grafana-bridge   ClusterIP   172.30.83.155   <none>        8443/TCP   35h
```

4. If the grafana-bridge application name, namespace and service name are different from the examples above, you must change them in the route-ocp-bridge.yaml script before applying grafana-bridge route.

5. Deploy a Route instance

```
oc apply -f route-ocp-bridge.yaml -n $BRIDGE_APP_NAMESPACE
```

6. Verify the grafanabridge route was deployed successfully

```
# oc get route -n $BRIDGE_APP_NAMESPACE
NAME                     HOST/PORT                                                           PATH   SERVICES                            PORT    TERMINATION   WILDCARD
grafanabridge            grafanabridge-ibm-spectrum-scale.apps.hw.cp.fyre.ibm.com                   ibm-spectrum-scale-grafana-bridge   https   passthrough   None
ibm-spectrum-scale-gui   ibm-spectrum-scale-gui-ibm-spectrum-scale.apps.hw.cp.fyre.ibm.com          ibm-spectrum-scale-gui              <all>   reencrypt     None

```

For complete setup example please check the project [Wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki)
