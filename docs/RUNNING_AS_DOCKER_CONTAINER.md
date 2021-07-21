## Running the IBM Spectrum Scale Performance Monitoring Bridge in a docker container

IMPORTANT The IBM Spectrum Scale system must run 5.0.5.2 or above.



### On the IBM Spectrum Scale cluster node running pmcollector, enable query remote connection:


```shell
# vi /opt/IBM/zimon/ZIMonSensors.cfg

  # Interface over which incoming queries are accepted (default: 127.0.0.1 to
  # prevent queries from remote machines).
  queryinterface = "0.0.0.0"

# systemctl restart pmcollector

```



### On a host running docker/podman perform the following steps:


1. Clone this repository using git in your favourite directory

```shell
# git clone https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana.git grafana_bridge
```


2. Copy the 'mmsdrfs' file from your IBM Spectrum Scale cluster to the 'grafana_bridge/source/gpfsConfig' directory
cp grafana_bridge/source/gpfsConfig

```shell
# scp <my_gpfs_cluster_node>:/var/mmfs/gen/mmsdrfs grafana_bridge/source/gpfsConfig

```


3. Create the bridge container image

```shell
# cd grafana_bridge/source

# podman build -t bridge_image:latest .
```


4. Start the bridge running in a container:

```shell
# podman run -dt -p 4242:4242 -e "SERVER=9.XXX.XXX.XXX" -e "APIKEYVALUE=XXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" --pod new:my-pod --name grafana_bridge bridge_image:latest

# podman logs grafana_bridge
2021-04-25 16:02 - INFO     -  *** IBM Spectrum Scale bridge for Grafana - Version: 7.0 ***
2021-04-25 16:02 - INFO     - Successfully retrieved MetaData
2021-04-25 16:02 - INFO     - Received sensors:CPU, DiskFree, GPFSFilesystem, GPFSFilesystemAPI, GPFSNSDDisk, GPFSNSDFS, GPFSNSDPool, GPFSNode, GPFSNodeAPI, GPFSRPCS, GPFSVFSX, GPFSWaiters, Load, Memory, Netstat, Network, TopProc, CTDBDBStats, CTDBStats, SMBGlobalStats, SMBStats, GPFSDiskCap, GPFSFileset, GPFSInodeCap, GPFSPool, GPFSPoolCap
2021-04-25 16:02 - INFO     - Initial cherryPy server engine start have been invoked. Python version: 3.6.8 (default, Aug 18 2020, 08:33:21)
[GCC 8.3.1 20191121 (Red Hat 8.3.1-5)], cherryPy version: 18.6.0.
2021-04-25 16:02 - INFO     - server started

```

Now you can add the host running the bridge container to the Grafana monitoring Datasource list.



### Using HTTPS(SSL) connection for the IBM Spectrum Scale Performance Monitoring Bridge running in a container


1. Follow the instructions [Generate SSL certificates](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki/How-to-setup-HTTPS%28SSL%29-connection-for-the-IBM-Spectrum-Scale-bridge-for-Grafana#generate-ssl-certificates) to generate a private ssl key and a ssl certificate

2. Start the bridge running in a container:

```shell
# podman run -dt -p 4242:4242,8443:8443 -e "SERVER=9.XXX.XXX.XXX" -e "APIKEYVALUE=XXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" -e "PORT=8443" -e "PROTOCOL=https" -e "TLSKEYPATH=/etc/bridge_ssl/certs" -e "TLSKEYFILE=privkey.pem" -e "TLSCERTFILE=cert.pem" \ -v /tmp:/var/log/ibm_bridge_for_grafana -v /etc/bridge_ssl/certs:/etc/bridge_ssl/certs \ --pod new:my-bridge-ssl-test-pod --name bridge-ssl-test bridge_image:latest

# podman logs bridge-ssl-test
2021-04-25 16:05 - INFO     -  *** IBM Spectrum Scale bridge for Grafana - Version: 7.0 ***
2021-04-25 16:05 - INFO     - Successfully retrieved MetaData
2021-04-25 16:05 - INFO     - Received sensors:CPU, DiskFree, GPFSFilesystem, GPFSFilesystemAPI, GPFSNSDDisk, GPFSNSDFS, GPFSNSDPool, GPFSNode, GPFSNodeAPI, GPFSRPCS, GPFSVFSX, GPFSWaiters, Load, Memory, Netstat, Network, TopProc, CTDBDBStats, CTDBStats, SMBGlobalStats, SMBStats, GPFSDiskCap, GPFSFileset, GPFSInodeCap, GPFSPool, GPFSPoolCap
2021-04-25 16:05 - INFO     - Initial cherryPy server engine start have been invoked. Python version: 3.6.8 (default, Aug 18 2020, 08:33:21)
[GCC 8.3.1 20191121 (Red Hat 8.3.1-5)], cherryPy version: 18.6.0.
2021-04-25 16:05 - INFO     - server started
```
