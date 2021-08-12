# Version 7.0.3 (08/13/2021)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi8/ubi:8.4-206
Added requirements_ubi8.txt file including the python versions packages needed to be installed to run the bridge in an OpenShift production environment, on top of the redhat UBI8 image

Tested with Grafana version 7.5.1 and 8.0.3
Tested with RedHat community-powered Grafana operator v.3.10.3



# Version 7.0.2 (08/02/2021)
Changed the Dockerfile parent image to the registry.access.redhat.com/ubi8/ubi
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
