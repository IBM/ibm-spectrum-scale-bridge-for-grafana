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
- changed '-s --server' option from required to optional. If not specified the server will be automatically set to 'localhost'.
>> **NOTE**: Since Spectrum Scale version 5.0.0 the ZImon pmcollector allows query requests, per default, only from local host.
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
