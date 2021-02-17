## Building a docker image for the IBM Spectrum Scale Performance Monitoring Bridge



**IMPORTANT:** for the building an image you need a host running docker/podman on it.


1. Clone this repository using git in your favourite directory

```shell
# git clone https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana.git grafana_bridge
```


2. Create the bridge container image

```shell
# cd grafana_bridge/source

# podman build -t bridge_image:latest .
```

