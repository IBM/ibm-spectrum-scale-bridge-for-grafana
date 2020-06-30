The ***IBM Spectrum Scale bridge for Grafana*** can be built as a podman container using:

```shell
# podman build -t grafana-bridge .
```

I've pushed x86_64 and ppc64le images to the dockerhub. The "lastest" tag is for x86_64, and "ppc64le" for, eh.. ppc64le. To launch the container on the same node as is running the ZimonCollector, I would suggest using "host" networking. Then it will have access to the ZimonCollector which is by default only listening on 127.0.0.1:

```shell
# podman run --net host -it janfrode/grafana-bridge:latest
```

Or on POWER (f.ex. on the ESS EMS):

```shell
# podman run --net host -it janfrode/grafana-bridge:ppc64le
```

If running somewhere else than on the ZimonCollector host, you need to tell it the IP-address to connect to using SERVER environment setting, and also expose the bridge ports:

```shell
# podman run -e SERVER=10.33.23.176 -p 4242:4242 -it janfrode/grafana-bridge
```


To run a full "POD" with the grafana-bridge and grafana, with persistent storage for grafana:


```shell
# podman volume create grafana-storage
# podman pod create --name grafanapod -p 3000:3000
# podman run --pod grafanapod -e SERVER=10.33.23.176 -it localhost/grafana-bridge
# podman run --pod grafanapod --name=grafana -v grafana-storage:/var/lib/grafana grafana/grafana
```


Then you can log into http://host:3000 as admin/admin to configure your data source (http://10.33.23.176:4242/), and upload the dashboards. Grafana configuration changes are persisted to the graphana-storage volume (/var/lib/containers/storage/volumes/grafana-storage/).
