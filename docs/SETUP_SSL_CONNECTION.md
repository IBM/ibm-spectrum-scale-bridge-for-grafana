### How to setup HTTPS(SSL) connection for IBM Spectrum Scale Performance Monitoring Bridge

To set up SSL communication between the bridge and the Grafana complete the following steps:


1. On the host, where you are running the bridge, generate a private key. For example, you can use openssl command and follow the OpenSSL ‘howto’ instructions:

```shell
# openssl genrsa -out privkey.pem 2048
```


2. Generate a certificate.

```shell
# openssl req -new -x509 -days 365 -key privkey.pem -out cert.pem
```

Openssl will then ask you a series of questions. You can enter whatever values are applicable, or leave most fields blank. The one field you must fill in is the ‘Common Name’: enter the hostname which will be used to access the bridge (where the Grafana server running).

Note: The file names for key and the certificate should be ‘privkey.pem’ and ‘cert.pem’.


3. Install CherryPy (version 5.0 or above)from the [CherryPy](https://cherrypy.org/) download page.

Note: If you are using python3, please check which cherryPy version is compatible with your setup. In our lab, we have tested python version 3.4.3 with cherryPy version 8.2.0.


4. Start the bridge listening on the socket port 8443. Don't forget to provide the location of ‘privkey.pem’ and ‘cert.pem’ (-k option), otherwise you will get the error message:

```shell
# python3 zimonGrafanaIntf.py -p 8443 -k /opt/registry/certs
```


#### Read more about HTTPS(SSL) connection
 [CherryPy openSSL documentation](https://docs.cherrypy.org/en/latest/deploy.html#ssl-support)
