# Example how you can import dashboards and data sources configuration by provisioning Grafana


### Provision a data source


1. Copy the datasource.yaml file in the ***provisioning/datasources/*** directory of your Grafana instance:

   ```
    cd /etc/grafana/provisioning/datasources/
    svn export https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/trunk/examples/grafana_provisioning/datasource.yaml
   ```
2. Open the datasource.yaml file in the edit mode and replace the *<host-ip>* in the URL string with ip of the host running the grafana-bridge. 

3. Restart Grafana to load the new changes.

4. In the sidebar, hover the cursor over the Configuration (gear) icon and click Data Sources. The TestData DB appears in the list of data sources.

For complete deployment examples please check the project [Wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki)
