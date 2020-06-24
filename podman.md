The ***IBM Spectrum Scale bridge for Grafana*** can be built as a podman container using:

```shell
# podman build -t grafana-bridge .
```

and then deployed as a pod together with the official grafana container by:



```shell
# podman volume create grafana-storage
# podman pod create --name grafanapod -p 3000:3000
# podman run --pod grafanapod -e ZSERVER=10.33.23.176 -it localhost/grafana-bridge
# podman run --pod grafanapod --name=grafana -v grafana-storage:/var/lib/grafana grafana/grafana
```

Point the ZSERVER to your zimon-collector host (which by default is only open from localhost, so you might need to change the queryinterface in /opt/IBM/zimon/ZIMonCollector.cfg). By running both containers in the same *pod*, they will be able to communicate over localhost. Therefore no ports needs to be exposed on the grafana-bridge, only the grafana web-port is exposed.

Then you can log into http://host:3000 as admin/admin to configure your data source (http://localhost:4242/), and upload the dashboards. Grafana configuration changes are persisted to the graphana-storage volume (/var/lib/containers/storage/volumes/grafana-storage/).
