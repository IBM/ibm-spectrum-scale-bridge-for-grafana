ARG BASE=registry.access.redhat.com/ubi8/ubi:8.5
FROM $BASE

LABEL com.ibm.name="IBM Spectrum Scale bridge for Grafana"
LABEL com.ibm.vendor="IBM" 
LABEL com.ibm.description="This tool translates the IBM Spectrum Scale performance data collected internally \
to the query requests acceptable by the Grafana integrated openTSDB plugin"
LABEL com.ibm.summary="It allows the IBM Spectrum Scale users to perform performance monitoring for IBM Spectrum Scale devices using Grafana"

COPY ./requirements/requirements_ubi8.txt  /root/requirements_ubi8.txt

RUN yum install -y python36 python36-devel
RUN /usr/bin/pip3 install --upgrade pip

RUN /usr/bin/pip3 install -r /root/requirements_ubi8.txt
RUN echo "Installed python version: $(/usr/bin/python3 -V)"
RUN echo "Installed python packages: $(/usr/bin/pip3 list)"

USER root

RUN mkdir -p /opt/IBM/bridge
RUN mkdir -p /opt/IBM/zimon
RUN mkdir -p /var/mmfs/gen
RUN mkdir -p /etc/ssl/certs
RUN mkdir -p /etc/perfmon-api-keys

COPY LICENSE /licenses/

COPY ./source/ /opt/IBM/bridge
COPY ./source/gpfsConfig/mmsdrfs* /var/mmfs/gen/
COPY ./source/gpfsConfig/ZIMon* /opt/IBM/zimon/

ARG HTTPPROTOCOL=http
ENV PROTOCOL=$HTTPPROTOCOL
RUN echo "the HTTP/S protocol is set to $PROTOCOL"

ARG HTTPPORT=4242
ENV PORT=$HTTPPORT
RUN echo "the HTTP/S port is set to $PORT" 

ARG PERFMONPORT=9980
ENV SERVERPORT=$PERFMONPORT
RUN echo "the PERFMONPORT port is set to $SERVERPORT" 

ARG CERTPATH='/etc/bridge_ssl/certs'
ENV TLSKEYPATH=$CERTPATH
RUN mkdir -p $CERTPATH

ARG KEYFILE=None
ENV TLSKEYFILE=$KEYFILE

ARG CERTFILE=None
ENV TLSCERTFILE=$CERTFILE

ARG KEYNAME=None
ENV APIKEYNAME=$KEYNAME

ARG KEYVALUE=None
ENV APIKEYVALUE=$KEYVALUE
RUN if [ "${APIKEYVALUE:0:1}" = "/" ]; then ln -s $APIKEYVALUE /etc/perfmon-api-keys; echo "APIKEYVALUE is a PATH"; else echo "APIKEYVALUE not a PATH"; fi

RUN if [ -z "$TLSKEYPATH" ] || [ -z "$TLSCERTFILE" ] || [ -z "$TLSKEYFILE" ] && [ "$PROTOCOL" = "https" ]; then echo "TLSKEYPATH FOR SSL CONNECTION NOT SET - ERROR"; exit 1; else echo "PASS"; fi
RUN echo "the ssl certificates path is set to $TLSKEYPATH" 

ARG PMCOLLECTORIP=0.0.0.0
ENV SERVER=$PMCOLLECTORIP
RUN echo "the pmcollector server ip is set to $SERVER"

ARG DEFAULTLOGPATH='/var/log/ibm_bridge_for_grafana'
ENV LOGPATH=$DEFAULTLOGPATH
RUN mkdir -p $LOGPATH
RUN echo "the log will use $LOGPATH"

# Switch to the working directory
WORKDIR /opt/IBM/bridge
RUN echo "$(pwd)"

# Create a user 'bridge' under 'root' group
RUN groupadd -g 2099 bridge
RUN useradd -rm -d /home/2001 -s /bin/bash -g 2099 -u 2001 bridge

# Chown all the files to the grafanabridge 'bridge' user
RUN chown -R 2001:2099 /opt/IBM/bridge
RUN chown -R 2001:2099 /opt/IBM/zimon
RUN chown -R 2001:2099 /var/mmfs/gen
RUN chown -R 2001:2099 /etc/ssl/certs
RUN chown -R 2001:2099 /etc/perfmon-api-keys
RUN chown -R 2001:2099 $TLSKEYPATH
RUN chown -R 2001:2099 $LOGPATH

# Switch to user 'bridge'
USER 2001


CMD ["sh", "-c", "python3 zimonGrafanaIntf.py -c 10 -s $SERVER -r $PROTOCOL -p $PORT -P $SERVERPORT -t $TLSKEYPATH -l $LOGPATH --tlsKeyFile $TLSKEYFILE --tlsCertFile $TLSCERTFILE --apiKeyName $APIKEYNAME --apiKeyValue $APIKEYVALUE"]

EXPOSE 4242 8443

#CMD ["tail", "-f", "/dev/null"]
