# Explore Grafana WEB interface for CNSS project in a k8s/OCP environment



Explore the grafana-route instance properties

```
[root@mycluster-inf grafana_deployment]# oc get route
NAME            HOST/PORT                                                PATH   SERVICES          PORT   TERMINATION   WILDCARD
grafana-route   grafana-route-my-grafana.apps.mycluster.os.fyre.ibm.com          grafana-service   3000   edge          None

[root@mycluster-inf grafana_deployment]# oc describe route grafana-route
Name:                   grafana-route
Namespace:              my-grafana
Created:                21 hours ago
Labels:                 <none>
Annotations:            openshift.io/host.generated=true
Requested Host:         grafana-route-my-grafana.apps.mycluster.os.fyre.ibm.com
                          exposed on router default (host apps.mycluster.os.fyre.ibm.com) 21 hours ago
Path:                   <none>
TLS Termination:        edge
Insecure Policy:        <none>
Endpoint Port:          3000

Service:        grafana-service
Weight:         100 (100%)
Endpoints:      10.254.12.208:3000

```


In a browser put the 'Requested Host' URL to open a Grafana user interface. Click on ‘Sign In’ from the bottom left menu of Grafana, and log in using the default username and password configured earlier(root/secret). 

![](/docs/grafana_ui_login_view.png)


Click on Configuration > Data Sources in the side menu and you’ll be taken to the data sources page where you can review and test grafana-bridge datasource settings.

![](/docs/grafana_ui_datasource_view.png)


Now, an editable Grafana interface appears and you can view your custom Grafana dashboards or create your own.
