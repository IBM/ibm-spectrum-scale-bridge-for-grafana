# IBM Spectrum Scale bridge for Grafana deployment in a k8s/OCP environment



### Dependencies
This instructions could be used for: 
- IBM Spectrum Scale Container Native Storage Access(CNSA) devices having minimum release level 5.1.0.1 and above
- IBM Spectrum Scale bridge for Grafana *version 6.1.2* (Checkout the branch 6.1)


1. Follow the [instructions](/docs/BUILDING_DOCKER_IMAGE.md) and create the IBM Spectrum Scale bridge for Grafana image


2. Make sure you have deployed the IBM Spectrum Scale Container Native Storage Access(CNSA) cluster including the ibm-spectrum-scale-pmcollector pods.
For more information about how to deploy a CNSA cluster please refer to the [IBM Spectrum Scale Knowledge Center](https://www.ibm.com/support/knowledgecenter/STXKQY_CNS_SHR/com.ibm.spectrum.scale.cns.v5r101.doc/introduction.html)

```
[root@mycluster-inf ~]# oc get po -o wide
NAME                                           READY   STATUS    RESTARTS   AGE   IP              NODE                               NOMINATED NODE   READINESS GATES
ibm-spectrum-scale-core-8gqvm                  1/1     Running   0          19h   10.16.105.140   worker1.mycluster.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-core-h5m6n                  1/1     Running   0          19h   10.16.105.141   worker2.mycluster.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-core-mwstf                  1/1     Running   0          19h   10.16.97.21     worker0.mycluster.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-gui-0                       9/9     Running   0          19h   10.254.16.108   worker1.mycluster.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-operator-79cd7dfb68-q4k49   1/1     Running   0          19h   10.254.12.168   worker2.mycluster.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-pmcollector-0               2/2     Running   0          19h   10.254.4.84     worker0.mycluster.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-pmcollector-1               2/2     Running   0          19h   10.254.16.109   worker1.mycluster.os.fyre.ibm.com   <none>           <none>
```

Also verify the service 'ibm-spectrum-scale-perf-query' is deployed and the service has a clusterIP assigned

```
[root@mycluster-inf ~]# oc get svc
NAME                              TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)               AGE
ibm-spectrum-scale                ClusterIP   172.30.46.239   <none>        22/TCP                19h
ibm-spectrum-scale-gui            ClusterIP   172.30.49.237   <none>        443/TCP,80/TCP        19h
ibm-spectrum-scale-gui-callback   ClusterIP   None            <none>        47443/TCP,47080/TCP   19h
ibm-spectrum-scale-perf-query     ClusterIP   172.30.165.48   <none>        9084/TCP,9094/TCP     19h
ibm-spectrum-scale-pmcollector    ClusterIP   None            <none>        9085/TCP,4739/TCP     19h
```


3. Copy the content of the example_deployment_scripts directory to your favourite directory on the master node.
Additionally perform the following modifications in the files before you start with the deployment:
    - Open the example_deployment_scripts/bridge_deployment/bridge-service.yaml file with an editor and set the namespace name of your CNSA cluster project.
    - Edit the example_deployment_scripts/bridge_deployment/bridge-deployment.yaml and modify the image: field to point to the bridge image location, you created before.
    - In case you are pulling the image from a private Docker registry or repository you need to create a Secret based on existing Docker credentials and 
      put the secret name under imagePullSecrets settings in the example_deployment_scripts/bridge_deployment/bridge-deployment.yaml
      For more Information please refer to the Kubernetes documentation about [Pull an Image from a Private Registry](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/)


4. Create the TLS certificate and the private key

```
[root@mycluster-inf ~]# openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/bridge_ssl/certs/privkey.pem -out /etc/bridge_ssl/certs/cert.pem -subj "/CN=grafana-bridge/O=grafana-bridge"
Generating a 2048 bit RSA private key
........................+++
..............................................+++
writing new private key to '/etc/bridge_ssl/certs/privkey.pem'
-----
```

Check that the both .pem files are created in the /tmp directory

```
[root@mycluster-inf ~]# cd /etc/bridge_ssl/certs
[root@mycluster-inf certs]# cat privkey.pem
-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDZ7v0Oq9n9zx8T
v/VPln5K74udrUVPA/4xz/+MsUIThlt+RLcaVuBx2jTbxDlSdPiQc/rSfZRtBTBt
ZNXbH6/7gI8jc1rp3BOTt6XjIiHRIM4J+4tD3kCQjKWoeIVFXixunSwF1ZZV3mPM
Ckr9Kxwck8hydKOS4L2URMbqkYEiBcxwZRkqm60Xlc2iYI4ayfHuPTqrbjazjbDw
lg73JOCVCBThWFK5KWPhzspUcgk/+mvofX2LVhiQftubHqp/PnnV5+Jb7v2wSxZ5
SQ4FZwZaJDL930lfrdozzQyHducacvqV2PINTf5srRtLfzlPW3ay5jPi06Qzeehc
yqTvYWwpAgMBAAECggEAXcWGX1S0hJAlWBMlk2w2xTmTQnI2u0wFiRttYvU2cD5E
ie05N/0fr/1q9xDUdVVdSpKM3xsnzU0JTFix6AoXZ8kmTeOpv6xxRAMmPrgGAvzx
irwQbVBpSYkrEnVhKrrdtW6tbYk8mZAKMtZO8+Yjv2wbOJxVcbKAABcj2/RlsuQu
N03bAdxBWfPMj/Du1HHI3G+zJ9b8y0AV96tC6Yb4QOIIGXiX2q3aHUJYApn++/FC
dzyaKOIQ128v/WFQnHf6lCGdTEfGXUjMWY0RR7eqj8lNDtRg1gvpN964KI7BHvke
sRSIT+bSi9D1t4hOSxjDs4XCk6B3ykefhPPq0vk8gQKBgQD6kUcyssmY3T9hCL6X
UB4BmSa0XIXLyWydG0Vmlvjw8ca/waCRkIqv+NDeoq7PTCul2poHPMT7/aVEHo5t
UCf9hqIHYp7C0sOPl5y72WpsAYNi7hZjZvqYnLzNqi0UwmtWQZCrqOp9bPXixDnf
h/lfpjk9FOS48NXp26TTSBLJ2QKBgQDeqJUkMblyk7+uz5AEq0XujQ9WmxLmA7/W
Ylz0Hj7uEYlHSwPh63+HlrOhVZAefa/wnjlwgF5ZGnrkSxDJzzAhpwNjk5lb8j6j
5ty1xa72YykI2sNoshdZ/qEy+CJAigf4xisDDd70xOR/q70F3TdOQJTVPQGd17Gt
Uh40Smhy0QKBgQCNc1gTKdUe47+0wp/9ga/+zPuJlDW/7mzPYCbUnGPaeVLuy5se
sc9pOfiHxqUSx3hYf8i2TzsQ2obiprFWyopY2Bk+PBFOAHd/52IGtd0bLduDDM88
vFS5tLntDKW4c2zu28KU9Z2ywsEojAfzxaoksgzcC6B3OxY3l9Q7phNdOQKBgDKo
yp4cjiQKh78/THYzfcrD32yGBeu9iKU/ZgTI6OqDpOdKowyA51gzKpWXgR3e3Ovz
JAB7xHujcbiFd8Fi2YGenT/HskngOO5TtX3KB3/ZmdmA5JrqgjOgoo6VND3Y6e1p
MRoVyteIALEnou81oMK2IObPZZHDJJLZrzOYhmExAoGBAO3eEcGuNOJQ0C+7L6fM
ehAHRd4XxCH0p4/lAI+qQZxmkRfho1IXg/sAQoFXCF2dj+hMZ9nlV26m3n6iZxFY
bjRUDSzBGHtV+WhPLzrKrsRFn4USCQHDA9+0aL2jGnfwC3En4SeMfk/3usLPVSAX
B4MtCX8SrTMkQ7PutwU2/R+i
-----END PRIVATE KEY-----
[root@mycluster-inf certs]# cat cert.pem
-----BEGIN CERTIFICATE-----
MIIDNzCCAh+gAwIBAgIJAMlcr+FBcrAnMA0GCSqGSIb3DQEBCwUAMDIxFzAVBgNV
BAMMDmdyYWZhbmEtYnJpZGdlMRcwFQYDVQQKDA5ncmFmYW5hLWJyaWRnZTAeFw0y
MDEyMDcxNzA5NTlaFw0yMTEyMDcxNzA5NTlaMDIxFzAVBgNVBAMMDmdyYWZhbmEt
YnJpZGdlMRcwFQYDVQQKDA5ncmFmYW5hLWJyaWRnZTCCASIwDQYJKoZIhvcNAQEB
BQADggEPADCCAQoCggEBANnu/Q6r2f3PHxO/9U+Wfkrvi52tRU8D/jHP/4yxQhOG
W35EtxpW4HHaNNvEOVJ0+JBz+tJ9lG0FMG1k1dsfr/uAjyNzWuncE5O3peMiIdEg
zgn7i0PeQJCMpah4hUVeLG6dLAXVllXeY8wKSv0rHByTyHJ0o5LgvZRExuqRgSIF
zHBlGSqbrReVzaJgjhrJ8e49OqtuNrONsPCWDvck4JUIFOFYUrkpY+HOylRyCT/6
a+h9fYtWGJB+25seqn8+edXn4lvu/bBLFnlJDgVnBlokMv3fSV+t2jPNDId25xpy
+pXY8g1N/mytG0t/OU9bdrLmM+LTpDN56FzKpO9hbCkCAwEAAaNQME4wHQYDVR0O
BBYEFHycTF2dzsCbGtMNyOSkRVsPlcCSMB8GA1UdIwQYMBaAFHycTF2dzsCbGtMN
yOSkRVsPlcCSMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQELBQADggEBAGgpZvr1
LzsNOUz8gNl6ZoH2rNaMkdPxngRpjAeXpypXMA02KDSVkBl02pWp3KwdsKporhmR
0a0Fz0dPFZQYFNi/zNK/BUDh66rRtzecg0Zw8ne7+YVhYlZDsG1R7GFdIudHz12y
kIBylbrb56LG4ltBvfaS5iWmuqnXuC+rjzKNCMSoBDdp+L+7objrt4qdThFVUOQ3
HCBDNH5DPxm5Md2pVy4qfU7apxAndE+29PYaw02FMfGHN5wTS6wU5gI62o1FivMT
O+6FAarz5qVR/D09GhoohwQDT8m5N2hfS61JQ/f3iN3KUYK00ppwWzJeumabVY+Z
/tXxmBkn7N2CkrQ=
-----END CERTIFICATE-----
```


5. Create the 'grafana-bridge-secret' secret for the TLS keys

```
[root@mycluster-inf certs]# kubectl create secret tls grafana-bridge-secret --key="privkey.pem" --cert="cert.pem"
secret/grafana-bridge-secret created

[root@mycluster-inf tmp]# oc describe secret grafana-bridge-secret
Name:         grafana-bridge-secret
Namespace:    spectrum-scale-ns
Labels:       <none>
Annotations:  <none>

Type:  kubernetes.io/tls

Data
====
tls.crt:  1176 bytes
tls.key:  1704 bytes

```


6. Since the IBM Spectrum Scale version 5.1.1 any client querying the performance data from the IBM Spectrum Scale cluster needs the API key authentication. You need to create API key secret for the grafana-bridge application using key name 'scale_grafana'. First encode your plaintext API key name and value using base_64:

```
[root@mycluster-inf certs]# echo -n 'scale_grafana'| base64
c2NhbGVfZGVmYXVsdA==
[root@mycluster-inf certs]# echo -n 'b0fbc340-43e8-4039-9895-e07eb34d1153'| base64
YjBmYmMzNDAtNDNlOC00MDM5LTk4OTUtZTA3ZWIzNGQxMTUz
```


7. Change to the directory example_deployment_scripts/bridge_deployment/ and open the secret.yaml file in edit mode. 
Replace the <YOUR_BASE64_ENCODED_API_KEY_NAME> and the <YOUR_BASE64_ENCODED_API_KEY_VALUE> with the values you generated with base_64.


8. Create the 'scale-grafana-api' secret for the 'scale_grafana' API key authentication

```
[root@mycluster-inf certs]# oc create -f secret.yaml
secret/scale-grafana-api created

[root@mycluster-inf certs]# oc describe secret scale-grafana-api
Name:         scale-grafana-api
Namespace:    ibm-spectrum-scale-ns
Labels:       <none>
Annotations:  <none>

Type:  Opaque

Data
====
api-key-name:   13 bytes
api-key-value:  36 bytes
```


9. Apply the following .yaml files:

```
[root@mycluster-inf certs]# cd /opt/example_deployment_scripts/bridge_deployment

[root@mycluster-inf bridge_deployment]# oc create -f role.yaml
role.rbac.authorization.k8s.io/grafana-bridge created

[root@mycluster-inf bridge_deployment]# oc create -f role_binding.yaml
rolebinding.rbac.authorization.k8s.io/grafana-bridge created

[root@mycluster-inf bridge_deployment]# oc create -f bridge-service.yaml
service/grafana-bridge created

[root@mycluster-inf bridge_deployment]# oc create -f bridge-deployment.yaml
deployment.apps/grafana-bridge-deployment created
```


10. Verify the grafana-bridge pods are up and running

```
[root@mycluster-inf bridge_deployment]# oc get po -o wide
NAME                                           READY   STATUS    RESTARTS   AGE   IP             NODE                             NOMINATED NODE   READINESS GATES
grafana-bridge-deployment-686f577585-jcr6r     1/1     Running   8          89m   10.254.20.19   worker0.helene.os.fyre.ibm.com   <none>           <none>
grafana-bridge-deployment-686f577585-wdrcs     1/1     Running   8          89m   10.254.16.19   worker1.helene.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-core-bpdwp                  0/1     Running   0          14h   10.16.69.109   worker1.helene.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-core-dsnx7                  0/1     Running   0          14h   10.16.69.105   worker0.helene.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-core-rdf54                  0/1     Running   0          14h   10.16.69.110   worker2.helene.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-gui-0                       9/9     Running   0          14h   10.254.16.11   worker1.helene.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-operator-6877d5c9bb-6xtxj   1/1     Running   0          15h   10.254.16.9    worker1.helene.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-pmcollector-0               2/2     Running   9          8h    10.254.20.16   worker0.helene.os.fyre.ibm.com   <none>           <none>
ibm-spectrum-scale-pmcollector-1               2/2     Running   0          8h    10.254.16.14   worker1.helene.os.fyre.ibm.com   <none>           <none>

[root@mycluster-inf bridge_deployment]# oc logs grafana-bridge-deployment-686f577585-jcr6r
2021-04-08 21:12 - INFO     -  *** IBM Spectrum Scale bridge for Grafana - Version: 7.0 ***
2021-04-08 21:12 - INFO     - Successfully retrieved MetaData
2021-04-08 21:12 - INFO     - Received sensors:CPU, DiskFree, GPFSNodeAPI, GPFSRPCS, GPFSVFSX, GPFSWaiters, Load, Memory, Netstat, Network, TopProc
2021-04-08 21:12 - INFO     - Initial cherryPy server engine start have been invoked. Python version: 3.6.8 (default, Aug 18 2020, 08:33:21)
[GCC 8.3.1 20191121 (Red Hat 8.3.1-5)], cherryPy version: 18.6.0.
2021-04-08 21:12 - INFO     - server started

```
