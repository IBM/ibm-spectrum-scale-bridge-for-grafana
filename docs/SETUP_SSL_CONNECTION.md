### How to setup HTTPS(SSL) connection for IBM Spectrum Scale Performance Monitoring Bridge

To set up SSL communication between the bridge and the Grafana complete the following steps:


1. On the host, where you are running the bridge, generate a private key. For example, you can use openssl command and follow the OpenSSL ‘howto’ instructions:

```shell
# openssl genrsa -out privkey.pem 2048
```


2. Generate a certificate.

```shell
# openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/bridge_ssl/certs/privkey.pem -out /etc/bridge_ssl/certs/cert.pem
```

Openssl will then ask you a series of questions. You can enter whatever values are applicable, or leave most fields blank. The one field you must fill in is the ‘Common Name’: enter the hostname which will be used to access the bridge (where the Grafana server running).

Note: The file names for the key and the certificate should be ‘privkey.pem’ and ‘cert.pem’.


3. Start the bridge listening on the socket port 8443 using HTTPS protocol. Don't forget to provide the location and the file name of the tls private key and the tls certificate:

```shell
# python3 zimonGrafanaIntf.py -p 8443 -r https -t /etc/bridge_ssl/certs -k privkey.pem -m cert.pem
```


#### Read more about HTTPS(SSL) connection
 [CherryPy openSSL documentation](https://docs.cherrypy.org/en/latest/deploy.html#ssl-support)
