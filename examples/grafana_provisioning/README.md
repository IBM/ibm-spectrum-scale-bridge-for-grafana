# Import dashboards and data sources configuration via Grafana provisioning


### Provision a data source


1. Copy the datasource.yaml file in the ***provisioning/datasources/*** directory of your Grafana instance:

   ```
    cd /etc/grafana/provisioning/datasources/
    svn export https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/trunk/examples/grafana_provisioning/datasource.yaml
   ```
2. Open the datasource.yaml file in the edit mode and replace the *<host-ip>* in the URL string with ip of the host running the grafana-bridge.

3. Restart Grafana to load the new changes.

4. In the sidebar, hover the cursor over the Configuration (gear) icon and click Data Sources. The TestData DB appears in the list of data sources.



### Provision a dashboard


1. Copy the default.json file to your Grafana instance host:

   ```
    mkdir -p /etc/dashboards
    cd /etc/dashboards
    svn export https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/trunk/examples/grafana_dashboards/default.json
   ```
2. Copy the dashboard.yaml file in the ***provisioning/dashboards/*** directory of your Grafana instance:

   ```
    cd /etc/grafana/provisioning/dashboards/
    svn export https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/trunk/examples/grafana_provisioning/dashboard.yaml
   ```
3. Restart Grafana to load the new changes



### Provision a bundle of dashboards with the folders structure


1. Copy the ***Example_Dashboards_bundle*** directory to your Grafana instance host:

   ```
    mkdir -p /etc/dashboards
    cd /etc/dashboards
    svn export https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/trunk/examples/grafana_dashboards/Example_Dashboards_bundle
   ```
2. Copy the dashboards.yaml file in the ***provisioning/dashboards/*** directory of your Grafana instance:

   ```
    cd /etc/grafana/provisioning/dashboards/
    svn export https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/trunk/examples/grafana_provisioning/dashboards.yaml
   ```
3. Update the grafana server config file to set the ***home dashboard path*** to the Available_Dashboards.json file

   ```
    cat /etc/grafana/grafana.ini
    
    [dashboards]
    # Path to the default home dashboard. If this value is empty, then Grafana uses StaticRootPath + "dashboards/home.json"
    default_home_dashboard_path = /etc/dashboards/Example_Dashboards_bundle/Home/Available_Dashboards.json
   ```

4. Restart Grafana to load the new changes.

5. You should see the **Available Dashboards** view as soon as you are logged in to the Grafana web interface.



For complete deployment examples please check the project [Wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki)
