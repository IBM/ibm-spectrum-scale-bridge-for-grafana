# Importing example dashboards

Example dashboards can easily be imported in a running Grafana environment.
Follow these [instructions](https://grafana.com/docs/grafana/latest/reference/export_import/)  to import your preferred dashboard into your Grafana installation.


## Default Dashboards set

This directory contains such dashboards that could form the basis of a performance analysis for an IBM Spectrum Scale cluster. 


## Advanced Dashboards set

This directory summarizes those dashboards that allow a deeper analysis of individual components, such as GPFSWaiters or Filesets Capacity Utilization


## Example Dashboards bundle

With the bridge version 4, the new collection of example dashboards "Example Dashbords bundle" has been added to the available for free download resources. These new dashboards could be used for managing a multi-cluster environment. Also the "Default Dashboards set" and  "Advanced Dashboards set"  have been merged into this download package.

The package content consists of several folders:

- Predefined Basic Dashboards - including all dashboard examples from "Default Dashboard set" package
- Advanced Dashboards -  including all dashboard examples from "Advanced Dashboards set" package
- HOWTO - including dashboard examples with learning effect, f.e. Grafana's helpful features
- NamedQueries - including dashboard examples for monitoring Linux(Network) metrics
- Protocols - including dashboard examples for monitoring SMB and NFS metrics
- TCT - including dashboard examples for monitoring TCT/cloud data transfers

You can create the same folder structure in your running Grafana environment and sort the imported dashboards into it, but this is not a mandatory step.



Each dashboard, included in the download package, can be imported and used as stand-alone dashboard, independent from all other dashboards in the package.  Only the "Available Dashboards" and the "Main Dashboard" are linked with children dashboards and do represent an example of the dashboards structuring.



If you want to make a usage of the dashboards list overview as shown in the screenshot below, it is recommended to set the Grafana's home dashboard to the "Available Dashboards". For more information about how to change the home dashboard settings in Grafana read [this](https://community.grafana.com/t/change-home-dashboard/7441) Grafana's Community post.

![](/docs/AvailableDashboards.PNG)
