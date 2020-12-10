# Grafana instance deployment in a k8s/OCP environment



### Dependencies


- RedHat community-powered Grafana operator v.3.6.0

    Grafana instances provided with the Openshift monitoring stack (and its dashboards) are read-only. To solve this problem, you can use the RedHat community-powered Grafana operator provided by OperatorHub.

    The Operator can deploy and manage a Grafana instance on Kubernetes and OpenShift. The following features are supported:

        Install Grafana to a namespace
        Configure Grafana through the custom resource
        Import Grafana dashboards from the same or other namespaces
        Import Grafana data sources from the same namespace
        Install Plugins (panels)


    The Grafana operator image could be found at [quay.io/integreatly/grafana-operator:v3.6.0](https://quay.io/integreatly/grafana-operator:v3.6.0)



## Deploying Grafana instance for the IBM Spectrum Scale cloud native (CNSS) project in a k8s/OCP environment


1. create a new project, for example: my-grafana

```
[root@mycluster-inf ~]# oc new-project my-grafana
Now using project "my-grafana" on server "https://api.mycluster.os.fyre.ibm.com:6443".

You can add applications to this project with the 'new-app' command. For example, try:

    oc new-app django-psql-example

to build a new example application in Python. Or use kubectl to deploy a simple Kubernetes application:

    kubectl create deployment hello-node --image=gcr.io/hello-minikube-zero-install/hello-node

```


2. Navigate to OperatorHub and select the community-powered Grafana Operator. Press Continue to accept the disclaimer, press Install, and press Subscribe to accept the default configuration values and deploy to the my-grafana namespace.

![](/docs/operator_hub.png)


Within some time, the Grafana operator will be made available in the my-grafana namespace.

![](/docs/grafana-operator-installed.png)


You can also verify the grafana operator successfully installed in the 'my-grafana' namespace using command line

```
[root@mycluster-inf ~]# oc get po -n my-grafana
NAME                                READY   STATUS    RESTARTS   AGE
grafana-operator-857c86c65d-62t7m   1/1     Running   0          78s

```


3. Change to the directory example_deployment_scripts/grafana_deployment/ and apply the grafana-instance-for-cnss.yaml file

```
[root@mycluster-inf ~]# cd /opt/example_deployment_scripts/grafana_deployment

[root@mycluster-inf grafana_deployment]# oc create -f grafana-instance-for-cnss.yaml
grafana.integreatly.org/grafana-for-cnss created

[root@mycluster-inf grafana_deployment]# oc get Grafana
NAME               AGE
grafana-for-cnss   42s

```
