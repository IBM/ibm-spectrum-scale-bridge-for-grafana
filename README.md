
[![CircleCI](https://circleci.com/gh/IBM/ibm-spectrum-scale-bridge-for-grafana.svg?style=svg)](https://app.circleci.com/pipelines/github/IBM/ibm-spectrum-scale-bridge-for-grafana?branch=master)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/5787/badge)](https://bestpractices.coreinfrastructure.org/projects/5787)

The ***IBM Storage Scale bridge for Grafana*** could be used for exploring IBM Storage Scale performance data on [Grafana dashboards](https://grafana.com/grafana/).

Grafana Bridge is a standalone Python application. It translates the IBM Storage Scale metadata and performance data collected by the [IBM Storage Scale performance monitoring tool (ZiMon)](https://www.ibm.com/docs/en/storage-scale/5.1.8?topic=monitoring-using-performance-tool) to the query requests acceptable by the [Grafana integrated openTSDB plugin](https://grafana.com/docs/features/datasources/opentsdb/).


<p align="center">
  <img src="/docs/grafana_bridge_overview.png" />
</p>


## Getting started

### Installation guides:

* [Setup the grafana bridge on a classic IBM Storage Scale cluster](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki/Setup-the-IBM-Spectrum-Scale-Performance-Monitoring-Bridge-for-classic-IBM-Spectrum-Scale-devices)
* [Run the grafana bridge in a docker container](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki/Running-the-IBM-Spectrum-Scale-Performance-Monitoring-Bridge-in-a-docker-container)
* [Setup a Grafana environment for monitoring performance data of a CNSA cluster in a k8s OCP environment](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki/Setup-Grafana-for-monitoring-a-CNSA-cluster--in-a-k8s-OCP-environment)

The ***latest article***:
* [How to setup Grafana instance to monitor multiple IBM Storage Scale clusters running in a cloud or mixed environment](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki/How-to-setup-Grafana-instance-to-monitor-multiple-IBM-Storage-Scale-clusters-running-in-a-cloud-or-mixed-environment)

Find more helpful information about the bridge usage in the project [Wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki)


## Contributing

At this time, third party contributions to this code will not be accepted.



## License

IBM Storage Scale bridge for Grafana is licensed under version 2.0 of the Apache License. See the [LICENSE](LICENSE.txt) file for details.
