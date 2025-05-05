# Example dashboards

Example dashboards can easily be imported in a running Grafana environment.
Follow these [instructions](https://grafana.com/docs/grafana/latest/reference/export_import/) to import your preferred dashboard into your Grafana installation.
The Grafana provisioning feature might be helpful, if you are going to import multiple dashboards. For more info please read [Make usage of Grafana Provisioning feature](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki/Make-usage-of-Grafana-Provisioning-feature)


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

You can create the same folder structure in your running Grafana environment via provisioning folders structure from filesystem to Grafana.
Follow [step-by-step instructions](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki/Make-usage-of-Grafana-Provisioning-feature#provision-the-example-dashboards-bundle-collection-with-folders-structure-to-grafana) available in the project Wiki.


