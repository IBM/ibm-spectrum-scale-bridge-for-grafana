
[![CircleCI](https://circleci.com/gh/IBM/ibm-spectrum-scale-bridge-for-grafana.svg?style=svg)](https://app.circleci.com/pipelines/github/IBM/ibm-spectrum-scale-bridge-for-grafana?branch=master)


The ***IBM Spectrum Scale bridge for Grafana*** could be used for exploring IBM Spectrum Scale performance data on [Grafana dashboards](https://grafana.com/grafana/).

Grafana Bridge is a standalone Python application. It translates the IBM Spectrum Scale metadata and performance data collected by the [IBM Spectrum Scale performance monitoring tool (ZiMon)](https://www.ibm.com/support/knowledgecenter/en/STXKQY_4.2.3/com.ibm.spectrum.scale.v4r23.doc/bl1adv_PMToverview.htm) to the query requests acceptable by the [Grafana integrated openTSDB plugin](https://grafana.com/docs/features/datasources/opentsdb/).


<p align="center">
  <img src="/docs/bridge_overview.PNG" />
</p>


## Getting started

### Installation guides:

* [Setup the grafana bridge on a classic IBM Spectrum Scale cluster](/docs/CLASSIC_SETUP.md)
* [Run the grafana bridge in a docker container](/docs/RUNNING_AS_DOCKER_CONTAINER.md)
* [Deploying the grafana bridge for an IBM CNSA project in a k8s/OCP environment](/docs/grafana_bridge_deployment_ocp.md)
* [Deploying a Grafana instance for the IBM CNSA project in a k8s/OCP environment](/docs/grafana_deployment_ocp.md)
* [Connecting the grafana-bridge datasource to the Grafana instance in a k8s/OCP environment](/docs/connect_bridge_to_grafana_ocp.md)
* [Explore the Grafana WEB interface for the IBM CNSA project in a k8s/OCP environment](/docs/explore_grafana_ocp.md)



## Contributing

At this time, third party contributions to this code will not be accepted.



## License

IBM Spectrum Scale bridge for Grafana is licensed under version 2.0 of the Apache License. See the [LICENSE](LICENSE.txt) file for details.
