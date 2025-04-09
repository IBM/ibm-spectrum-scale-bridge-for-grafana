# Example setting up Openshift metrics collection for ibm-spectrum-scale project



Using the scripts in this folder you can expose CNSA(gpfs) internal metrics to the Openshift Monitoring Stack

```shell
oc apply -f cluster_monitoring_config.yml
```

```shell
oc label namespace openshift-user-workload-monitoring scale.spectrum.ibm.com/networkpolicy=allow
```

```shell
NAMESPACE=ibm-spectrum-scale
```

```shell
oc apply -f grafana_bridge_service_monitor.yaml --namespace=$NAMESPACE
```


