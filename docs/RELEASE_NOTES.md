# Version 9.0.1 (12/19/2025)
Published [example dashboard](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/blob/master/examples/grafana_dashboards/GPFS_cluster_communication_statistics/IBM%20Storage%20Scale%20Network%20Overview-1763571518612.json) for observing the Network issues within the IBM Storage Scale clusters
Switched to a non-root user in a docker image
Addressed the findings of the MEND security scan
Improved performance of prometheus scrap job queries by skipping the transfer of the domain RangeData
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi10/ubi:10.0-1762765098

Tested with OpenTSDB version 2.4
Tested with Grafana version 12.0.2
Tested with RedHat community-powered Grafana operator v.5



# Version 9.0.0 (10/30/2025)
Added example yaml files to configure Openshift ServiceMonitor for a scale cluster running outside of this Openshift cluster
Expanded configuration parameters to allow grafana-bridge socket host to bind to ip of specific network interface
Removed python3.9 support, set required minimum level to 3.11
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi10/ubi:10.0-1760519443 

Tested with OpenTSDB version 2.4
Tested with Grafana version 12.0.0
Tested with RedHat community-powered Grafana operator v.5



# Version 8.1.0 (10/24/2025)
Added check for empty/not acceptable values in the configuration file
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.6-1760340943 

Tested with OpenTSDB version 2.4
Tested with Grafana version 12.0.0
Tested with RedHat community-powered Grafana operator v.5



# Version 8.0.9 (09/01/2025)
* Fixed issue with version tag.

Tested with OpenTSDB version 2.4
Tested with Grafana version 12.0.0
Tested with RedHat community-powered Grafana operator v.5



# Version 8.0.8 (09/01/2025)
Fixed the issue with PrometheusExporter handling the 'counter' type metric when rawCounters is set to false.

Tested with OpenTSDB version 2.4
Tested with Grafana version 12.0.0
Tested with RedHat community-powered Grafana operator v.5



# Version 8.0.7 (08/14/2025)
Published example dashboards for monitoring ESS Hardware metrics with Prometheus: \
- ESS Hardware Performance overview \
- HW Components Temperature \
- HW Fan Rotation \
- PSU Power(mA*Volt) \
Added support for Prometheus scrape job params config \
Added GPFSEvents, GPFSEXPEL, GPFSEXPELNODE sensors to PrometheusExporter supported sensors\
Added helpful HTTP REST API endpoints for working with PrometheusExporter:
/endpoints
/labels
/filters
Modified handling of config file allowing to store and invoke custom config file outside the repository

Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.6-1754586119 \ 

Tested with OpenTSDB version 2.4
Tested with Grafana version 12.0.0
Tested with RedHat community-powered Grafana operator v.5



# Version 8.0.6 (05/28/2025)
Published example dashboard for observing high level health status of all gpfs devices rgistered and managed with Grafana\
Improved rawCounters setting management by PrometheusExporter\
Added RAWDATA to the Dockerfile editable command line arguments\
Added HTTP Api REST endpoint for querying sensor metrics details\

Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.6-1747219013 \ 

Tested with OpenTSDB version 2.4
Tested with Grafana version 12.0.0
Tested with RedHat community-powered Grafana operator v.5



# Version 8.0.5 (05/10/2025)
Published example dashboards for monitoring ESS Hardware metrics: \
- ESS Hardware Performance overview \
- HW Components Temperature \
- HW Fan Rotation \
- PSU Power(mA*Volt) \
Published example dashboards for monitoring the IBM Storage Scale cloud native project as part of Openshift Monitoring stack: \
- Openshift cluster and IBM Storage Scale cloud native project overview\
Added example yaml file for Deploying Prometheus as Grafanadatasource on an Openshift cluster via Grafana-operator v5. \
Added example yaml file for Deploying GrafanaDashboard resource for monitoring IBM Storage Scale container native project on an Openshift cluster via Grafana-operator v5. \
Added GPFSTSCOM sensor to PrometheusExporter supported sensors\

Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.5-1745854298 \ 

Tested with OpenTSDB version 2.4
Tested with Grafana version 12.0.0
Tested with RedHat community-powered Grafana operator v.5



# Version 8.0.4 (04/10/2025)
Added Deployment scripts to expose GPFS metrics to the Openshift Monitoring stack
Published example dashboards for monitoring ESS devices: \
- System load overview \
- CPU utilization details \
- Network Data transfer details \
- InfiniBand Data transfer details \
- Filesystem Data transfers rate \
- Filesystem Data transfer rate per Node\
- Filesystem Data transfers rate \
Reworked Dockerfile allowing compile python requirements list during grafana-bridge image build \
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.5-1742918310 \ 

Tested with Grafana version 11.5.0
Tested with RedHat community-powered Grafana operator v.5



# Version 8.0.3 (01/20/2025)
Added GPFSPoolCap, GPFSInodeCap and GPFSFCMDA sensors to the supported PrometheusExporter endpoints \
Added HTTP Api REST endpoint for querying last metric sample (OpenTSDB plugin)
Reworked Dockerfile allowing build grafana-bridge image from Redhat UBI9/Python3.9 \
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.5-1736404036 \ 

Tested with Grafana version 11.0.0
Tested with RedHat community-powered Grafana operator v.5



# Version 8.0.2 (12/18/2024)
Added GPFSNSDPool, GPFSNSDFS sensors to the supported PrometheusExporter endpoints
Added LOGLEVEL to the Dockerfile editable command line arguments
Removed psutil package from Python requirements list 

Tested with Grafana version 11.0.0
Tested with RedHat community-powered Grafana operator v.5



# Version 8.0.1 (12/10/2024)
Added HTTP Api REST endpoints allowing to query: \
-  Performance Monitoring Tool sensors configuration in use \
-  Timestamp of the latest metadata local cache refresh \
Added plugin for generating Promtheus config file authomatically based on the actual Performance Monitoring Tool sensors configuration \
Added GPFSmmhealth sensor to the PrometheusExporter supported endpoints \
Improved the  performance of the OpenTSDB HTTP Api REST  search/loookup endpoint \
Added monitoring thread  observing if MetaData refresh is required \
Published example dashboards showing: \
- GPFS Cluster overview using OpenTSDB Datasource \
- GPFS Cluster overview using Prometheus Datasource \
- GPFSmmhealth metrics \
- GPFS physical disks wait times \
- GPFS fileset quota reporting \
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.5-1732804088 \

Tested with Grafana version 11.0.0
Tested with RedHat community-powered Grafana operator v.5



# Version 8.0.0 (04/26/2024)
The Grafana Bridge has been refactored to allow several APIs to be registered and run as standalone plugins. The OpenTSDB API now needs to be explicitly registered via port configuration in config.ini before it can be used with Grafana. 
Added the new Prometheus Exporter plugin which collects metrics and exposes them in a format that can be scraped by the Prometheus timeseries database. This plugin also needs to be enabled via port configuration. 
Added Prometheus server configuration file examples. 
Added a Client Basic Authentication over HTTP/S support. 
Added features to collect and report the internal performance statistics of grafana-bridge. 

Tested with Grafana version 10.2.3
Tested with RedHat community-powered Grafana operator v.5



# Version 7.2.1 (01/15/2025)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.5-1736404036 \

Tested with Grafana version 11
Tested with RedHat community-powered Grafana operator v.5



# Version 7.2.0 (12/06/2024)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.5-1732804088 \
Speed up OpenTSDB /search/lookup REST Api endpoint response time \
Backported important fixes that improve overall bridge performance \

Tested with Grafana version 11
Tested with RedHat community-powered Grafana operator v.5



# Version 7.1.9 (09/27/2024)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.4-1214.1726694543 \

Tested with Grafana version 11
Tested with RedHat community-powered Grafana operator v.5



# Version 7.1.8 (08/29/2024)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.4-1181.1724035907 \

Tested with Grafana version 11
Tested with RedHat community-powered Grafana operator v.5



# Version 7.1.7 (08/27/2024)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.4-1181 \

Tested with Grafana version 11
Tested with RedHat community-powered Grafana operator v.5



# Version 7.1.6 (06/28/2024)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.4-1123 \

Tested with Grafana version 11
Tested with RedHat community-powered Grafana operator v.5



# Version 7.1.5 (06/07/2024)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.4-947.1717074712 \

Tested with Grafana version 9.5
Tested with RedHat community-powered Grafana operator v.5



# Version 7.1.4 (05/07/2024)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.4 \

Tested with Grafana version 9.5
Tested with RedHat community-powered Grafana operator v.5



# Version 7.1.3 (03/08/2024)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.3-1610 \

Tested with Grafana version 9.5
Tested with RedHat community-powered Grafana operator v.5



# Version 7.1.2 (02/28/2024)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.3-1552 \

Tested with Grafana version 9.5
Tested with RedHat community-powered Grafana operator v.5



# Version 7.1.1 (01/18/2024)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.3 \

Tested with Grafana version 9.5
Tested with RedHat community-powered Grafana operator v.5



# Version 7.1.0 (11/20/2023)
Added a watch function observing changes in zimon sensor configuration and initiating the metadata refresh. \
Added methods to get metric attributes
Added method logging query time execution
Internal code restructuring

Tested with Grafana version 9.5
Tested with RedHat community-powered Grafana operator v.5



# Version 7.0.9 (08/20/2023)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi9/ubi:9.2 \
Added example yaml files for Deploying Grafana instance on an Openshift cluster via Grafana-operator v5. \
Added example yaml files for Deploying grafana-bridge as Grafanadatasource on an Openshift cluster via Grafana-operator v5. \
Added example yaml file for grafana-bridge service route allowing an external Grafana instance query data from grafana-bridge running inside an Openshift cluster\
Added example Dashboards compatible with Grafana 9.5 \

Tested with Grafana version 9.5
Tested with RedHat community-powered Grafana operator v.5



# Version 7.0.8 (12/06/2022)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi8/ubi:8.7 \
Made Dockerfile compatibe with OpenShift style allowing to specify user/group settings at the image build time. \
Added Workaround for Disk Capacity sensors allowing to query and fetch data from the archived (on disk data). \

Tested with Grafana version 7.5.17 and 9.0.0
Tested with RedHat community-powered Grafana operator v.4.8



# Version 7.0.7 (09/21/2022)
Fixed issue in parsing zimon sensors config, having new filter format for Network sensor

Tested with Grafana version 7.5.16 and 9.0.0
Tested with RedHat community-powered Grafana operator v.4.6



# Version 7.0.6 (04/12/2022)
Fetch raw data for GPFSDiskCap metrics as workaround for the zimon issue not returning all capacity metrics results. \
Added non root user to the Dockerfile. This way the main process will be started with a non-root user when running in a container.  \
Added labels to the Dockerfile

Tested with Grafana version 8.0.3
Tested with RedHat community-powered Grafana operator v.4.1



# Version 7.0.5 (02/10/2022)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi8/ubi:8.5 \
Added 'caCertPath' to the configurable parameters, which allows the user to enable or disable CA certificate verification for the REST API HTTPS connections to the pmcollector. \
Added 'retryDelay' to the configurable parameters. Using this parameter the user can control how long the bridge should sleep before re-attempting to query the MetaData, in case no data was returned by pmcollector through the initial bridge startup

Tested with Grafana version 7.5.1 and 8.0.3
Tested with RedHat community-powered Grafana operator v.4.1



# Version 7.0.4 (09/22/2021)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi8/ubi:8.4-209 \
Moved out the documentation files from the repository content. They have been placed on the [project Wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki).

Tested with Grafana version 7.5.1 and 8.0.3
Tested with RedHat community-powered Grafana operator v.3.10.3



# Version 7.0.3 (08/13/2021)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi8/ubi:8.4-206 \
Added requirements_ubi8.txt file including the python versions packages needed to be installed to run the bridge in an OpenShift production environment, on top of the redhat UBI8 image

Tested with Grafana version 7.5.1 and 8.0.3
Tested with RedHat community-powered Grafana operator v.3.10.3



# Version 7.0.2 (08/02/2021)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi8/ubi \
Changed the sleep time = 60 seconds for re-attempting to get the MetaData from the pmcollector in case no data have been returned during the bridge start instead of stopping the process directly

Tested with Grafana version 7.5.1 and 8.0.3
Tested with RedHat community-powered Grafana operator v.3.10.3



# Version 7.0.1 (07/21/2021)
Added support for [IBM Spectrum Scale Container Native Storage Access 5.1.1.1](https://www.ibm.com/docs/en/scalecontainernative?topic=spectrum-scale-container-native-storage-access-5111)
- updated example deployment yaml files according the API key authentication changes introduced to the IBM Spectrum Scale Performance monitoring tool

Modified config.ini allowing to specify the file path, where the 'apiKeyValue' is stored, instead of entering a key value in this file

Added the new command line argument'protocol'
- using this argument the user can decide if the bridge incoming requests should happen over HTTP or HTTPS connection
Removed fixed port numbers for HTTP/HTTPS connections.
- 4242 and 8443 still default ports for the bridge HTTP/HTTPS cnnections, but not fixed anymore

Added logic to re-attempt to get the MetaData from the pmcollector in case no data have been returned during the bridge start instead of stopping the process directly
- MAX_RETRY_COUNT = 3

Expanded test module with more unit tests

Tested with Grafana version 7.5.1 and 8.0.3



# Version 7 (04/26/2021)

Added support for [IBM Spectrum Scale 5.1.1](https://www.ibm.com/docs/en/spectrum-scale/5.1.1?topic=summary-changes)
- added IBM Spectrum Scale Performance monitoring API key authentication
- added command line arguments('apiKeyName' and 'apiKeyValue') allowing to submit the API key authentication data at the bridge start
- changed default serverPort to 9980
Added the article "Configuring a performance monitoring API key for the IBM Spectrum Scale Performance Monitoring Bridge" to the Wiki



# Version 6.1.4 (07/21/2021)

Added support for the 'protocol' command line argument.
Removed fixed port numbers for HTTP/HTTPS connections.

Expanded test module with more unit tests

Tested with Grafana 8.0.3 version



# Version 6.1.3 (05/21/2021)

Added support for the 'includeDiskData' command line argument.
- using the 'includeDiskData' option allows to query and fetch data from the archived (on disk data) for better precision. 

Expanded test module with more unit tests

Tested with Grafana 7.5.1 version



# Version 6.1.2 (03/20/2021)

Removed the "switching to the multi-threaded zimon port automatically" feature
Added logic closing the socket connection in case the query to the pmcollector ends up in an Exception
Added new "MOREINFO" level to the logger
Added log tracing for the cherrypy server process pid

Expanded test module with unit tests for the bridgeLogger module



# Version 6.1.1 (03/05/2021)

Added version tracking inside the bridge module
Added "config.ini" file with the default configuration settings, which can be updated, saved away and restored by the user
Expanded list of the editable command line arguments
- added argument:'tlsKeyFile'; Name of TLS key file, f.e.: privkey.pem
- added argument:'tlsCertFile'; Name of TLS certificate file, f.e.: cert.pem
- splitted the 'logFile' argument in the 'logPath', allowing to modify the location of the log files, and the 'logFile', editable log file name
Moved the default log location outside the bridge source code
- default location path of the log file set to: "/var/log/ibm_bridge_for_grafana"

Expanded test module with more unit tests

Added Wiki link to the README
Improved the documentation about the bridge setup in a cloud native environment(CNSA)
Updated documentation about the bridge configuration using http(ssl) connection



# Version 6.1 (12/10/2020)

Added support for [IBM Spectrum Scale Container Native Storage Access 5.1.0.1](https://www.ibm.com/support/knowledgecenter/STXKQY_CNS_SHR/com.ibm.spectrum.scale.cns.v5r101.doc/introduction.html)
- added example yaml files which can be used to run the bridge in a cloud native environment.
- added example yaml files which can be used to connect the bridge to a Grafana instance running in a cloud native environment.
- added instructions describing how to deploy the bridge in a container running in a k8s/Openshift environment
- added instructions describing how to deploy a Grafana instance via grafana-operator powered by RedHad community in a k8s/Openshift environment

Make cherryPy server settings editable for a user

Added test module for a basic parameter verification with the pytest framework
Enabled source code changes verification using circleCi CI/CD pipeline 



# Version 6 (10/20/2020)

Removed python2 support

Added Dockerfile which can be used to run the bridge in a docker container.
Added instructions describing how to build the bridge image and run it in a container 

Set default location of the log file: './logs/zserver.log' 

Source code refactoring(moved source code and example dashboards to the separate sub-directories)

Fixed the issue "GPFSNSDFS/GPFSNSDPool sensor metrics are not found by the bridge"



# Version 5 (12/01/2019)

Moved the source code & documentation to the IBM GITHUB

Source code refactoring(bridge internal optimization)
- metadata retrieval optimizations (time performance)



# Version 4 (04/08/2019)

Added aggregation support to query interval 
- set the query interval automatically to the metric data polling interval if the downsampling is disabled explicitly
- allow usage of AVG, MIN, MAX, SUM aggregators for the downsampled polling intervals

Changed the logic for checking the metric sensor configuration data.
- Reason: GPFSFSInodeCap and GPFSPoolCap are virtual sensors. The config settings for this sensors need to be derived from the sensor GPFSDiskCap.



# Version 3 (08/06/2018)

Added python3.6 support 

Source code changes based on [openTSDB datasource](https://github.com/grafana/grafana/tree/master/public/app/plugins/datasource/opentsdb) plugin supported by Grafana
- Query requests and results in [openTSDB API 2.3 supported format](http://opentsdb.net/docs/build/html/api_http/query/index.html)
- Fixed [alias tag issue](https://github.com/grafana/grafana/issues/7560)

Source code changes based on latest configuration updates to IBM Spectrum Scale performance monitoring tool (ZIMon):
- changed '-s --server' option from required to optional. If not specified the server will be automatically set to 'localhost'. \
   **NOTE**: Since Spectrum Scale version 5.0.0 the ZImon pmcollector allows query requests, per default, only from local host.
- added vlaidity check for '-P --serverPort'
- added configuration check for multithreaded serverPort. If configured, this will be automatically used for querying pmcollector.

Source code refactoring(bridge internal optimization)
- refactoring of GET, POST Handler result objects (bridge internal)
- metadata retrieval optimizations (time performance)

Improved logging, more options for troubleshooting
- improved trace messages for logging connection issues
- improved trace messages for logging wrong input parameters f.e. tag names, tag values



# Version 2 (05/24/2017)

Added HTTPS(SSL) connection support(via port 8443)
- required [CherryPy version 4.0](download from: https://pypi.python.org/pypi/CherryPy/4.0.0) or higher 
- required [SSL private key and certificate](http://cherrypy.readthedocs.io/en/latest/deploy.html#ssl-support) to be generated
- start the bridge with '-k' option (followed by the SSLkey location path) and port 8443 (-p option)

Source code changes based on [openTSDB datasource](https://github.com/grafana/grafana/tree/master/public/app/plugins/datasource/opentsdb) plugin supported by Grafana
- allowing the multiple filters usage in the [lookup](http://opentsdb.net/docs/build/html/api_http/search/lookup.html?) queries
- Query requests and results in [openTSDB API 2.3 query format](http://opentsdb.net/docs/build/html/api_http/query/index.html)

Improved logging, more options for troubleshooting 
- added python version, cherryPy version and the list of enabled sensors to the console message during the bridge start
- added trace messages for logging received requests from Grafana and processed queries stored in zserver.log(INFO-level)
- added trace messages for logging process details at different places (DEBUG-level)
- added HTTPError codes to the error trace messages(if the error cause is known)
- cherrypy_access.log enabled (automatically created with the bridge start)
- cherrypy_error.log (automatically created with the bridge start)

Source code refactoring(bridge internal optimization)
- moved to the new QueryHandler(backend query engine)
- metadata retrieval simplification (all methods quering metadata moved to the separate module)



# Version 1 (06/16/2016)

Initial version
