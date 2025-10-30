# Example of setting up Openshift metrics collection for Remote Storage Cluster 



You can use the scripts in this folder to expose GPFS metrics from a remote cluster that is used as a storage server for a CNSA cluster to the OpenShift Monitoring Stack

## Prerequisite steps on Remote Storage Cluster

A number of preleminary tasks must be executed on the IBM Storage Scale storage cluster. 

Setup IBM Storage Scale bridge for Grafana with PrometheusExporter enabled.
Ensure that the node on which PrometheusExporter is running is accessible from the OpenShift cluster.
Copy the SSL/TLS key and certificate configured for the IBM Storage Scale bridge for Grafana on the remote cluster to the OpenShift cluster.

## Deployment steps on Openshift Cluster

Enable monitoring for user-defined projects
```shell
oc apply -f https://raw.githubusercontent.com/IBM/ibm-spectrum-scale-bridge-for-grafana/refs/heads/master/examples/openshift_deployment_scripts/cnsa_workload_monitoring/cluster-monitoring-config.yml
```

Create new project
```shell
oc new-project ibm-external-storage
```

Create tls secret from tls key/certificate files
```shell
oc create secret tls grafanabridge-external-tls-data --cert=</path/to/cert.crt> --key=</path/to/cert.key> -n ibm-external-storage
```

Open external_storage_endpoint.yaml in edit mode and update the ip field with the the ip adress of the remote storage cluster node running PrometheusExporter.
Apply the external_storage_endpoint.yaml
```shell
oc apply -f external-storage-endpoint.yaml
```

Deploy ibm-example-external-storage-service Service resource
```shell
oc apply -f external-storage-endpoint-service.yml
```

Deploy prometheus-grafanabridge-external-monitor ServiceMonitor resource 
```shell
oc apply -f grafanabridge-external-service-monitor.yml