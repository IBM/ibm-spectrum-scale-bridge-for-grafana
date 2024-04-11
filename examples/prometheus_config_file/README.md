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
