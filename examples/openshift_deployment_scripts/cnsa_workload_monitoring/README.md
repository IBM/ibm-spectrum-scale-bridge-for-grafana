# Example of setting up Openshift metrics collection for ibm-spectrum-scale project



Using the scripts in this folder you can expose CNSA(gpfs) internal metrics to the Openshift Monitoring Stack

Enable monitoring for user-defined projects
```shell
oc apply -f https://raw.githubusercontent.com/IBM/ibm-spectrum-scale-bridge-for-grafana/refs/heads/master/examples/openshift_deployment_scripts/cnsa_workload_monitoring/cluster-monitoring-config.yml
```

To allow ingress and egress communication from the openshift-user-workload-monitoring namespace to the ibm-spectrum-scale namespace within your Red Hat OpenShift cluster, label it with the label scale.spectrum.ibm.com/networkpolicy=allow
```shell
oc label namespace openshift-user-workload-monitoring scale.spectrum.ibm.com/networkpolicy=allow
```

Deploy ServiceMonitor resource in the ibm-spectrum-scale namespace to scrape metrics from the ibm-spectrum-scale-grafana-bridge service endpoint
```shell
oc project ibm-spectrum-scale
```

```shell
oc apply -f https://raw.githubusercontent.com/IBM/ibm-spectrum-scale-bridge-for-grafana/refs/heads/master/examples/openshift_deployment_scripts/cnsa_workload_monitoring/grafana-bridge-service-monitor.yaml
```



## Accessing metrics with third-party applications from outside of the Openshift cluster



Create the OpenShift Container Platform API route to access Thanos Querier externally by running the following command
```shell
https://raw.githubusercontent.com/IBM/ibm-spectrum-scale-bridge-for-grafana/refs/heads/master/examples/openshift_deployment_scripts/cnsa_workload_monitoring/route-external-access-thanos-querier.yaml
```



## Visualizing and monitoring metrics exposed to the openshift-monitoring stack with the Grafana dashboard within the Openshift cluster



Deploy Grafana instance in the "grafana-for-cnsa" project

Create the Prometheus GrafanaDatasource
```shell
oc apply -f https://raw.githubusercontent.com/IBM/ibm-spectrum-scale-bridge-for-grafana/refs/heads/master/examples/openshift_deployment_scripts/cnsa_workload_monitoring/grafana-prometheus-datasource.yml
```

Create the GrafanaDashboard resources
```shell
oc apply -f https://raw.githubusercontent.com/IBM/ibm-spectrum-scale-bridge-for-grafana/refs/heads/master/examples/openshift_deployment_scripts/cnsa_workload_monitoring/cnsa-openshift-cluster-dashboards.yaml
```

For the complete deployment guide please check the project [Wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki)