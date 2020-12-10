# Connecting the grafana-bridge datasource to the Grafana for CNSS instance


![](/docs/bridge_connect_grafana_ocp.png)

The grafana-serviceaccount serviceAccount, created during [Grafana instance deployment](/docs/grafana_deployment_ocp.md), was created alongside the Grafana instance.
You need grant the grafana-serviceaccount access rights to the ibm-spectrum-scale-operator clusterRole.

```
[root@mycluster-inf grafana_deployment]# oc get sa
NAME                     SECRETS   AGE
builder                  2         10m
default                  2         10m
deployer                 2         10m
grafana-operator         2         5m12s
grafana-serviceaccount   2         78s

[root@mycluster-inf grafana_deployment]# oc describe serviceAccount grafana-serviceaccount
Name:                grafana-serviceaccount
Namespace:           my-grafana
Labels:              <none>
Annotations:         <none>
Image pull secrets:  grafana-serviceaccount-dockercfg-jc27p
Mountable secrets:   grafana-serviceaccount-token-5qvz4
                     grafana-serviceaccount-dockercfg-jc27p
Tokens:              grafana-serviceaccount-token-5pgt5
                     grafana-serviceaccount-token-5qvz4
Events:              <none>

[root@mycluster-inf grafana_deployment]# oc adm policy add-cluster-role-to-user ibm-spectrum-scale-operator -z grafana-serviceaccount
clusterrole.rbac.authorization.k8s.io/ibm-spectrum-scale-operator added: "grafana-serviceaccount"

```


The bearer token for this serviceAccount is used to authenticate the access to grafana-bridge dataSource in the my-grafana namespace. The following command will display this token.

```
[root@mycluster-inf grafana_deployment]# oc serviceaccounts get-token grafana-serviceaccount -n my-grafana
eyJhbGciOiJSUzI1NiIsImtpZCI6IlFIV0dLT1ZITlpqQ1lXc05TNUNkVjZ2MDFJVUp2SjFnR3lkR2IzWU9HSmsifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJteS1ncmFmYW5hIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImdyYWZhbmEtc2VydmljZWFjY291bnQtdG9rZW4tNXF2ejQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZ3JhZmFuYS1zZXJ2aWNlYWNjb3VudCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjY3MjY0ZmU0LWFlYTMtNDQxNC05NDU5LTE2NTg2NzU2NTRiMyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpteS1ncmFmYW5hOmdyYWZhbmEtc2VydmljZWFjY291bnQifQ.hd0nRch8LksC8yDCCoNtCgvqnicZiDPX7nez_EcbSp41qteKGx5mrMoif15XeWSl-sJQPhEu92ACaJYdXCUazl-5rTzB8aa0AYjn0tom8Y_5fISxyeGBraj7Otfrc1LVFXtnc9GpzwfY8R_jPYAfEu10ToRe-TvgXWTBnFp-qPMrlZhN4psdfmvFFVw_228Q1jXp16A1a1O5J9ZfNWSXsKrjDqnRYHa2O0JyHh8kp5QVlCnpNjk7DoXnawkhuOypAn257cudnlPYVdSj_lQ2jm4nIXC5eZ5lxFk6JXe5oLGxSKm92ls2LbZoUF48qpEwmGGCfRZPifsR1DzA0xwWFQ
```

Substituite ${BEARER_TOKEN} with the output of the command above in the grafana-bridge-datasource.yaml
Also 'TLS cert ${TLS_CERT}', 'TLS key ${TLS_KEY}' need to be replaced with TLS key and certificate, we have generated for the grafana-bridge.

The GrafanaDataSource deployment script for the grafana-bridge datasource will look as below:

```
apiVersion: integreatly.org/v1alpha1
kind: GrafanaDataSource
metadata:
  name: bridge-grafanadatasource
  namespace: my-grafana
spec:
  datasources:
    - access: proxy
      editable: true
      isDefault: true
      jsonData:
        httpHeaderName1: 'Authorization'
        timeInterval: 5s
        tlsSkipVerify: true
        tlsAuth: true
      name: grafana-bridge
      type: opentsdb
      secureJsonData:
        tlsClientCert: |
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
        tlsClientKey: |
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
        httpHeaderValue1: 'eyJhbGciOiJSUzI1NiIsImtpZCI6IlFIV0dLT1ZITlpqQ1lXc05TNUNkVjZ2MDFJVUp2SjFnR3lkR2IzWU9HSmsifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJteS1ncmFmYW5hIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImdyYWZhbmEtc2VydmljZWFjY291bnQtdG9rZW4tNXF2ejQiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZ3JhZmFuYS1zZXJ2aWNlYWNjb3VudCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjY3MjY0ZmU0LWFlYTMtNDQxNC05NDU5LTE2NTg2NzU2NTRiMyIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpteS1ncmFmYW5hOmdyYWZhbmEtc2VydmljZWFjY291bnQifQ.hd0nRch8LksC8yDCCoNtCgvqnicZiDPX7nez_EcbSp41qteKGx5mrMoif15XeWSl-sJQPhEu92ACaJYdXCUazl-5rTzB8aa0AYjn0tom8Y_5fISxyeGBraj7Otfrc1LVFXtnc9GpzwfY8R_jPYAfEu10ToRe-TvgXWTBnFp-qPMrlZhN4psdfmvFFVw_228Q1jXp16A1a1O5J9ZfNWSXsKrjDqnRYHa2O0JyHh8kp5QVlCnpNjk7DoXnawkhuOypAn257cudnlPYVdSj_lQ2jm4nIXC5eZ5lxFk6JXe5oLGxSKm92ls2LbZoUF48qpEwmGGCfRZPifsR1DzA0xwWFQ'
      url: 'https://grafana-bridge.spectrum-scale-ns.svc.cluster.local:8443'
      version: 1
  name: grafana-bridge-datasource.yaml

```


create the grafana-bridge GrafanaDataSource from the yaml file

```
[root@mycluster-inf grafana_deployment]# oc create -f grafana-bridge-datasource.yaml
grafanadatasource.integreatly.org/bridge-grafanadatasource created

[root@mycluster-inf grafana_deployment]# oc get GrafanaDataSource -n my-grafana
NAME                       AGE
bridge-grafanadatasource   25s

[root@mycluster-inf grafana_deployment]# oc get configmap -n my-grafana
NAME                    DATA   AGE
grafana-config          1      12h
grafana-datasources     1      12h
grafana-operator-lock   0      12h

```
