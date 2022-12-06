
[![CircleCI](https://circleci.com/gh/IBM/ibm-spectrum-scale-bridge-for-grafana.svg?style=svg)](https://app.circleci.com/pipelines/github/IBM/ibm-spectrum-scale-bridge-for-grafana?branch=master)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5787/badge)](https://bestpractices.coreinfrastructure.org/projects/5787)

The ***IBM Spectrum Scale bridge for Grafana*** could be used for exploring IBM Spectrum Scale performance data on [Grafana dashboards](https://grafana.com/grafana/).

Grafana Bridge is a standalone Python application. It translates the IBM Spectrum Scale metadata and performance data collected by the [IBM Spectrum Scale performance monitoring tool (ZiMon)](https://www.ibm.com/support/knowledgecenter/en/STXKQY_4.2.3/com.ibm.spectrum.scale.v4r23.doc/bl1adv_PMToverview.htm) to the query requests acceptable by the [Grafana integrated openTSDB plugin](https://grafana.com/docs/features/datasources/opentsdb/).


<p align="center">
  <img src="/docs/bridge_overview.PNG" />
</p>


## Getting started

### Installation guides:

* [Setup the grafana bridge on a classic IBM Spectrum Scale cluster](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki/Setup-the-IBM-Spectrum-Scale-Performance-Monitoring-Bridge-for-classic-IBM-Spectrum-Scale-devices)
* [Run the grafana bridge in a docker container](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki/Running-the-IBM-Spectrum-Scale-Performance-Monitoring-Bridge-in-a-docker-container)
* [Setup the grafana bridge for performance monitoring of a CNSA cluster in a k8s OCP environment](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki/Setup-Grafana-for-monitoring-a-CNSA-cluster--in-a-k8s-OCP-environment)

Find more helpful information about the bridge usage in the project [Wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki)


## Contributing

At this time, third party contributions to this code will not be accepted.



## License

IBM Spectrum Scale bridge for Grafana is licensed under version 2.0 of the Apache License. See the [LICENSE](LICENSE.txt) file for details.
