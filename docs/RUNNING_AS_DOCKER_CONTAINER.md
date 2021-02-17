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

# podman build -t bridge_image:gpfs505 .
```


4. Start the bridge running in a container:

```shell
# podman run -dt -p 4242:4242 -e "SERVER=9.XXX.XXX.XXX" --pod new:my-pod --name grafana_bridge bridge_image:gpfs505

# podman logs grafana_bridge

```

Now you can add the host running the bridge container to the Grafana monitoring Datasource list.



### Using HTTPS(SSL) connection for the IBM Spectrum Scale Performance Monitoring Bridge running in a container


1. Follow the instructions [How to setup HTTPS(SSL)](./SETUP_SSL_CONNECTION.md) to generate a private key and certificate for 

2. Start the bridge running in a container:

```shell
# podman run -dt -p 4242:4242,8443:8443 -e "SERVER=9.XXX.XXX.XXX" -e "PORT=8443" -e "KEYPATH=/opt/registry/certs" \ -v /tmp:/opt/IBM/bridge/logs -v /opt/registry/certs:/opt/registry/certs \ --pod new:my-bridge-ssl-test-pod --name bridge-ssl-test bridge_ssl_test:grafana 

# podman logs bridge-ssl-test
Connection to the collector server established successfully
Successfully retrieved MetaData
Received sensors:

CPU     DiskFree        GPFSFilesystem  GPFSFilesystemAPI       GPFSNSDDisk     GPFSNSDFS       GPFSNSDPool     GPFSNode        GPFSNodeAPI     GPFSRPCS        GPFSVFS GPFSWaiters     Load    Memory  Netstat Network GPFSDiskCap     GPFSFileset GPFSFilesetQuota        GPFSInodeCap    GPFSPool        GPFSPoolCap
Initial cherryPy server engine start have been invoked. Python version: 3.6.8 (default, Dec  5 2019, 15:45:45)
[GCC 8.3.1 20191121 (Red Hat 8.3.1-5)], cherryPy version: 18.6.0.
server started
```
