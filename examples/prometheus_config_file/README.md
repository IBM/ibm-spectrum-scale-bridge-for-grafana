# Install and configure Prometheus server

Go to the official [Prometheus downloads page](https://prometheus.io/download/) and download the
latest release for your architecture (e.g. `prometheus-2.53.0.linux-amd64.tar.gz`).

## 1. Extract and install binaries

```bash
tar -xzf prometheus-*.linux-amd64.tar.gz
cd prometheus-*.linux-amd64

# Create a dedicated system user (no login shell, no home directory)
useradd -M -r -s /bin/false prometheus

# Create config and data directories
mkdir -p /etc/prometheus /var/lib/prometheus

# Install binaries
cp prometheus promtool /usr/local/bin/
chown root:root /usr/local/bin/prometheus /usr/local/bin/promtool

# Copy the bundled console templates (present in Prometheus 2.x releases)
cp -r consoles console_libraries /etc/prometheus/

# Fix ownership so the prometheus user can read config and write TSDB data
chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus
```

## 2. Create the systemd service unit

```bash
cat > /etc/systemd/system/prometheus.service << 'EOF'
[Unit]
Description=Prometheus monitoring system
Documentation=https://prometheus.io/docs/introduction/overview/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=prometheus
Group=prometheus
Restart=on-failure
ExecStart=/usr/local/bin/prometheus \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/var/lib/prometheus \
    --web.console.templates=/etc/prometheus/consoles \
    --web.console.libraries=/etc/prometheus/console_libraries \
    --web.listen-address=0.0.0.0:9090 \
    --web.enable-lifecycle
ExecReload=/bin/kill -HUP $MAINPID

[Install]
WantedBy=multi-user.target
EOF
```

> **Note:** `--web.enable-lifecycle` is required for the `POST /-/reload` hot-reload
> used in the fetch commands below.


# Prepare prometheus config file

There are two ways to configure Prometheus to scrape the bridge.
Choose the one that fits your setup.

## Approach 1 – Let the bridge generate the full prometheus.yml

The `/prometheus.yml` endpoint returns a complete, ready-to-use `prometheus.yml`
that includes all scrape jobs, TLS settings, and (optionally) the
`storage.tsdb.out_of_order_time_window` block.
Use this approach for a fresh Prometheus installation or when you want the bridge
to be the single source of truth for scrape configuration.

Run once on the Prometheus host (or via the push pattern described below):

```bash
curl -sf http://<bridge_ip>:9250/prometheus.yml \
     -o /etc/prometheus/prometheus.yml.tmp \
  && mv /etc/prometheus/prometheus.yml.tmp \
        /etc/prometheus/prometheus.yml \
  && promtool check config /etc/prometheus/prometheus.yml \
  && curl -sf -XPOST http://localhost:9090/-/reload
```

With HTTPS and basic auth:

```bash
curl -sf --cacert /etc/prometheus/certs/ca.pem \
     -u scale_admin:TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg== \
     https://<bridge_ip>:9250/prometheus.yml \
     -o /etc/prometheus/prometheus.yml.tmp \
  && mv /etc/prometheus/prometheus.yml.tmp \
        /etc/prometheus/prometheus.yml \
  && promtool check config /etc/prometheus/prometheus.yml \
  && curl -sf -XPOST http://localhost:9090/-/reload
```

## Approach 2 – Extend your existing prometheus.yml with scrape_config_files

Use this approach when you already manage your own `prometheus.yml` (for alerting
rules, remote write, or other scrape jobs) and only want the bridge to contribute
its scrape jobs.
Requires Prometheus 2.43 or later.

Add the following to your existing `prometheus.yml`:

```yaml
scrape_config_files:
  - /etc/prometheus/scrape_configs/*.yml
```

Then keep the bridge-generated scrape file up to date using a cron job or systemd
timer — see the [section below](#using-the-bridge-generated-scrape-file-with-scrape_config_files)
for the full fetch and reload commands.


## 3. Enable and start the service

```bash
systemctl daemon-reload
systemctl enable prometheus
systemctl start prometheus
systemctl status prometheus
```

For more configuration details, see the 'Prometheus setup' section in the project [wiki](https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana/wiki).

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

Choose whichever option fits your topology.

### Option A – Pull: run on the Prometheus host

Use this when the Prometheus host can reach the bridge over HTTP/S.
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

### Option B – Push: run on the bridge host

Use this when the bridge host can reach the Prometheus host over SSH but not the
other way around (common when the bridge runs inside a storage-cluster network).
The `target` parameter tells the bridge to embed the correct scrape address in the
generated file instead of auto-detecting it.

`scp` copies the file as the connecting SSH user, so `chown` is required to make
the file readable by the `prometheus` process.

```bash
curl -sf "http://localhost:9250/scrape_configs.yml?target=<bridge_ip>:9250" \
     -o /tmp/gpfs_bridge.yml.tmp \
  && scp /tmp/gpfs_bridge.yml.tmp \
         <ssh_user>@<prometheus_ip>:/etc/prometheus/scrape_configs/gpfs_bridge.yml.tmp \
  && ssh <ssh_user>@<prometheus_ip> \
         "mv /etc/prometheus/scrape_configs/gpfs_bridge.yml.tmp \
             /etc/prometheus/scrape_configs/gpfs_bridge.yml \
          && chown prometheus:prometheus \
             /etc/prometheus/scrape_configs/gpfs_bridge.yml \
          && curl -sf -XPOST http://localhost:9090/-/reload"
```

With HTTPS and basic auth:

```bash
curl -sf --cacert /etc/bridge/certs/ca.pem \
     -u scale_admin:TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg== \
     "https://localhost:9250/scrape_configs.yml?target=<bridge_ip>:9250" \
     -o /tmp/gpfs_bridge.yml.tmp \
  && scp /tmp/gpfs_bridge.yml.tmp \
         <ssh_user>@<prometheus_ip>:/etc/prometheus/scrape_configs/gpfs_bridge.yml.tmp \
  && ssh <ssh_user>@<prometheus_ip> \
         "mv /etc/prometheus/scrape_configs/gpfs_bridge.yml.tmp \
             /etc/prometheus/scrape_configs/gpfs_bridge.yml \
          && chown prometheus:prometheus \
             /etc/prometheus/scrape_configs/gpfs_bridge.yml \
          && curl -sf -XPOST http://localhost:9090/-/reload"
```

## Query parameters

Both `/prometheus.yml` and `/scrape_configs.yml` accept the following query parameters.

| Parameter | Default | Description |
|---|---|---|
| `job_suffix` | empty | Literal string appended to every generated `job_name`. Pattern: `^[A-Za-z0-9_.:-]{1,64}$`. Use this to avoid job-name clashes when several bridges or clusters feed one Prometheus instance, for example `?job_suffix=_clusterA`. |
| `internal_metrics` | `false` | `true` or `false`. When `true`, adds two scrape jobs for the bridge's own internal endpoints: `GrafanaBridgeHttpMetrics` (`/http_metrics`) and `GrafanaBridgeInternalStats` (`/internal_stats`), both scraped every 60 s. Returns HTTP 400 if internal metrics are disabled in `analytics.py`. |
| `target` | auto-detected | Override the scrape target written into the generated config. Accepts `<host>` or `<host>:<port>`. When only `<host>` is given the configured prometheus port is used. When omitted the bridge auto-detects its outbound IP. Returns HTTP 400 if the port is not a number or the host is empty. Example: `?target=10.0.0.5:9250`. |
| `path` | none | Absolute path on the **bridge filesystem** to write the generated file to, in addition to returning it in the response body. If the path points to a directory, the file is written as `prometheus.yml` or `scrape_configs.yml` inside it. Returns HTTP 400 if the path is not absolute or the parent directory does not exist. Example: `?path=/etc/prometheus/scrape_configs`. |

Examples:

```
GET /scrape_configs.yml?job_suffix=_clusterA
GET /scrape_configs.yml?internal_metrics=true
GET /scrape_configs.yml?job_suffix=_clusterA&internal_metrics=true
GET /scrape_configs.yml?target=10.0.0.5:9250
GET /scrape_configs.yml?target=mybridge.example.com
GET /scrape_configs.yml?path=/etc/prometheus/scrape_configs
GET /scrape_configs.yml?target=10.0.0.5:9250&job_suffix=_clusterA&path=/etc/prometheus/scrape_configs
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

