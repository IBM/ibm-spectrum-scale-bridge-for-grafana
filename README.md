The ***IBM Spectrum Scale bridge for Grafana*** could be used for exploring IBM Spectrum Scale performance data on [Grafana dashboards](https://grafana.com/grafana/).

Grafana Bridge is a standalone Python application. It translates the IBM Spectrum Scale metadata and performance data collected by the [IBM Spectrum Scale performance monitoring tool (ZiMon)](https://www.ibm.com/support/knowledgecenter/en/STXKQY_4.2.3/com.ibm.spectrum.scale.v4r23.doc/bl1adv_PMToverview.htm) to the query requests acceptable by the [Grafana integrated openTSDB plugin](https://grafana.com/docs/features/datasources/opentsdb/).



## Setup

### Prerequisites

Before installing the IBM Spectrum Scale bridge for Grafana you must install the software prerequisites. Those are:
1. [Performance Monitoring tool](https://www.ibm.com/support/knowledgecenter/en/STXKQY_4.2.3/com.ibm.spectrum.scale.v4r23.doc/bl1adv_PMToverview.htm) installed and configured on your IBM Spectrum Scale device
2. On the [collector node](https://www.ibm.com/support/knowledgecenter/en/STXKQY_4.2.3/com.ibm.spectrum.scale.v4r23.doc/bl1adv_configurecollector.htm) the following software need to be installed:
- [Python2.7](https://www.python.org/downloads/release/python-2717/)/ [Python3.6](https://www.python.org/downloads/release/python-369/)
- [CerryPy](https://cherrypy.org/)


### Dependencies
This package could be used for: 
- IBM Spectrum Scale devices having mimimum release level 4.2.3 FP8 and above
- Grafana 5.0.0 and above

To use this tool on the older IBM Spectrum Scale devices please refer to the [SUPPORT_MATRIX](SUPPORT_MATRIX.md) file.



### Installation, Configuration and Usage

#### Step 1. Ensure that IBM Spectrum Scale meets prerequisite conditions

The IBM Spectrum Scale system must run 4.2.1. or above. Run mmlsconfig to view the current configuration data of a GPFS™ cluster).

The bridge works in permanent communication with the pmcollector. Therefore it is recommended to install and run this tool directly on a pmcollector node.

In a multi-collector environment, there is no need to run the bridge on each pmcollector node separately, provided that they are configured in federated mode. Federation basically allows collectors to connect and collaborate with their peer collectors. If the peers have been specified, any query for measurement data must be directed to any of the collectors listed in the peer definition. The chosen collector will collect and assemble a response based on all relevant data from all collectors. For more information, see [Performance Monitoring tool overview](https://www.ibm.com/support/knowledgecenter/en/STXKQY_4.2.3/com.ibm.spectrum.scale.v4r23.doc/bl1adv_PMToverview.htm) in IBM Spectrum Scale: Advanced Administration Guide.



#### Step 2. Verify Python and CherryPy

Ensure that Python and CherryPy have been installed on the IBM Spectrum Scale system. 
Check the [SUPPORT_MATRIX](SUPPORT_MATRIX.md) file for the recommended version.



#### Step 3. Set up IBM Spectrum Scale Performance Monitoring Bridge

Download the zip package and unpack it in your favorite directory on the collector node :

```shell
# unzip zimonGrafanaIntf.zip
```

Start the bridge application by issuing:

```shell
# python zimonGrafanaIntf.py 
```

If the bridge did establish the connection to the specified pmcollector and the initialization of the metadata was performed successfully, you should get the message "server started" at the end of line. Otherwise check the zserver.log stored in the zimonGrafanaIntf  directory.  Additionally, check the pmcollector service running properly by issuing:

```shell
# systemctl status pmcollector
```



#### Step 4. Install Grafana

Download and install [Grafana](https://grafana.com/get) according to the given instructions. Before you start Grafana for the first time, check [the configuration options](http://docs.grafana.org/installation/configuration/) for port settings. Start the Grafana server as it described on the Grafana configuration pages.



#### Step 5. Establish connection to the running bridge in Grafana

Define a new data source (Data Sources -> Add New)

![](Add_DataSource_2.3.png)

**NOTE**: The IBM Spectrum Scale bridge listens on port 4242 for HTTP connections, and on port 8443 for HTTPS connections

Grafana now can talk to Spectrum Scale Performance Monitoring tool via the bridge. Follow the grafana instructions to create dashboards.



## Contributing

At this time, third party contributions to this code will not be accepted.



## License

IBM Spectrum Scale bridge for Grafana is licensed under version 2.0 of the Apache License. See the [LICENSE](LICENSE.txt) file for details.



