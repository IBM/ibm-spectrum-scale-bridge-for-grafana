# Install and configure Prometheus server

Go to the official [Prometheus downloads page](https://prometheus.io/download/) and download the latest package.
Perform required setup steps.

   ```
   tar -zxpvf prometheus-2.47.2.linux-amd64.tar.gz
   useradd -m -s /bin/false prometheus
   mkdir /etc/prometheus
   mkdir /var/lib/prometheus
   chown prometheus /etc/prometheus
   chown prometheus /var/lib/prometheus/

   cd prometheus-2.47.2.linux-amd64
   cp prometheus /usr/local/bin
   cp promtool /usr/local/bin
   cp -r consoles /etc/prometheus
   cp -r console_libraries /etc/prometheus
   ```


# Prepare prometheus config file

All the prometheus configurations should be present in /etc/prometheus/prometheus.yml file.
You need to register the target in the prometheus.yml file to get the metrics from the source systems.


   1. Copy the example prometheus.yml file to your Prometheus server host

   ```
    scp prometheus.yml /etc/prometheus/prometheus.yml
   ```

   2. Open the copied file in the edit mode

   ```
    vi /etc/prometheus/prometheus.yml
   ```

   3. Replace the *<prometheus_server_ip>* string with the prometheus server ip

   ```
    static_configs:
      - targets: ["<prometheus_server_ip>:9090"]
   ```

   4. Replace all the *<grafana_bridge_ip>* strings with ip of the host running the grafana-bridge

   ```
   static_configs:
    - targets: ['<grafana_bridge_ip>:9250']
   ```

   5. If HTTP/S Basic Authentication is enabled, replace the sample password with one you have generated
   ```
   basic_auth:
      username: 'scale_admin'
      password: 'TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg=='
   ```


# Start Prometheus server

   Reload the systemd service to register the prometheus service and start the prometheus service

   ```
   systemctl daemon-reload
   systemctl start prometheus
   systemctl enable prometheus
   ```

For more configuration details, please read the content of the  'Prometheus setup' section in the project [wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki).

# Using the bridge-generated scrape file with scrape_config_files

Prometheus 2.43 and later support the `scrape_config_files` key in `prometheus.yml`.
It lets you reference external files that contain only a `scrape_configs` list.
This is useful when you already manage your own `prometheus.yml` and only want the
bridge to contribute its scrape jobs.

## Step 1 – Add scrape_config_files to your prometheus.yml

```yaml
scrape_config_files:
  - /etc/prometheus/scrape_configs/*.yml
```

## Step 2 – Fetch the file from the bridge

Run the following on the Prometheus host, for example as a cron job or a systemd timer.
The atomic `mv` prevents Prometheus from reading a half-written file.

```bash
curl -sf http://<bridge_ip>:9250/scrape_configs.yml \
     -o /etc/prometheus/scrape_configs/gpfs_bridge.yml.tmp \
  && mv /etc/prometheus/scrape_configs/gpfs_bridge.yml.tmp \
        /etc/prometheus/scrape_configs/gpfs_bridge.yml \
  && promtool check config /etc/prometheus/prometheus.yml \
  && curl -sf -XPOST http://localhost:9090/-/reload
```

With HTTPS and basic auth:

```bash
curl -sf --cacert /etc/prometheus/certs/ca.pem \
     -u scale_admin:TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg== \
     https://<bridge_ip>:9250/scrape_configs.yml \
     -o /etc/prometheus/scrape_configs/gpfs_bridge.yml.tmp \
  && mv /etc/prometheus/scrape_configs/gpfs_bridge.yml.tmp \
        /etc/prometheus/scrape_configs/gpfs_bridge.yml \
  && curl -sf -XPOST http://localhost:9090/-/reload
```

## Query parameters

Both `/prometheus.yml` and `/scrape_configs.yml` accept the following query parameters.

| Parameter | Default | Description |
|---|---|---|
| `job_suffix` | empty | Literal string appended to every generated `job_name`. Pattern: `^[A-Za-z0-9_.:-]{1,64}$`. Use this to avoid job-name clashes when several bridges or clusters feed one Prometheus instance, for example `?job_suffix=_clusterA`. |
| `internal_metrics` | `false` | `true` or `false`. When `true`, adds two scrape jobs for the bridge's own internal endpoints: `GrafanaBridgeHttpMetrics` (`/http_metrics`) and `GrafanaBridgeInternalStats` (`/internal_stats`), both scraped every 60 s. Returns HTTP 400 if internal metrics are disabled in `analytics.py`. |

Examples:

```
GET /scrape_configs.yml?job_suffix=_clusterA
GET /scrape_configs.yml?internal_metrics=true
GET /scrape_configs.yml?job_suffix=_clusterA&internal_metrics=true
```

## Note on out-of-order timestamps

`/http_metrics` re-emits timestamped samples on every scrape.
If you enable `internal_metrics=true`, add the following to your `prometheus.yml` to
prevent ingestion errors:

```yaml
storage:
  tsdb:
    out_of_order_time_window: 2d
```

The full `/prometheus.yml` endpoint already includes this setting.

---

