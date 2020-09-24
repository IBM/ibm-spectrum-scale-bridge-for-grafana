## Running the IBM Spectrum Scale Performance Monitoring Bridge as Docker Container

The IBM Spectrum Scale system must run 5.0.5 or above.


### On the IBM Spectrum Scale cluster node running pmcollector, enable data query remote connection


```shell
# vi /opt/IBM/zimon/ZIMonSensors.cfg

  # Interface over which incoming queries are accepted (default: 127.0.0.1 to
  # prevent queries from remote machines).
  queryinterface = "0.0.0.0"

# systemctl restart pmcollector

```


1. On the host, where you are running the bridge, generate a private key. For example, you can use openssl command and follow the OpenSSL ‘howto’ instructions:

```shell
# openssl genrsa -out privkey.pem 2048
```


### On the host running docker/podman perform the following steps:

1. Clone this repository using git in your favourite directory :

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
