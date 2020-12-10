# IBM Spectrum Scale bridge for Grafana

![](/grafana-bridge/grafana-bridge.png)


The IBM Spectrum Scale bridge for Grafana is an Opensource software and could be used for exploring IBM Spectrum Scale performance data on Grafana dashboards.

The source code and the documentation of [the IBM Spectrum Scale bridge for Grafana](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana) could be found on the public GitHub webpage, under IBM organization projects or by spectrum-scale tag.

The public bridge repository includes a Dockerfile, which allows the user/customer to build the grafana-bridge image locally.
For the development and test team the built image is stored on the Artifactory, under
"sys-spectrum-scale-team-cloud-native-docker-local.artifactory.swg-devops.com/scale-grafana-bridge:dev". The grafana-bridge deployment script provided in this repository points to the Artifactory image location as well.
If you want to use your personal grafana-bridge image, you have to edit the bridge-deployment.yaml file and replace the image location.


Setup
-------------------
* [Bridge setup](/grafana-bridge/grafana_bridge_deployment_ocp.md)
* [Grafana setup](/grafana-bridge/grafana_deployment_ocp.md)


## Setup


### Prerequisites

Before deploying the IBM Spectrum Scale bridge for Grafana you must install the software prerequisites. Those are:
1. [Performance Monitoring tool](https://www.ibm.com/support/knowledgecenter/en/STXKQY_5.0.5/com.ibm.spectrum.scale.v5r05.doc/bl1adv_PMToverview.htm) installed and configured on your IBM Spectrum Scale device
2. On the [collector node](https://www.ibm.com/support/knowledgecenter/en/STXKQY_5.0.5/com.ibm.spectrum.scale.v5r05.doc/bl1adv_configurecollector.htm) the following software need to be installed:
- [Python3.6](https://www.python.org/downloads/release/python-369/)
- [CherryPy](https://cherrypy.org/)



### Dependencies
- IBM Spectrum Scale cloud native devices having minimum release level 5.1.0.1 and above
- RedHat community-powered Grafana operator version 3.6.0


### Deployment
* [IBM Spectrum Scale bridge for Grafana deployment](/docs/grafana_bridge_deployment_ocp.md)
* [Grafana instance deployment](/docs/grafana_deployment_ocp.md)
* [Connecting grafana-bridge datasource to the Grafana instance]
