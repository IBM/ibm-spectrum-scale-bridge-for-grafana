ARG BASE=registry.access.redhat.com/ubi8/ubi:8.5
FROM $BASE

LABEL com.ibm.name="IBM Spectrum Scale bridge for Grafana"
LABEL com.ibm.vendor="IBM"
LABEL com.ibm.version="7.0.8-dev"
LABEL com.ibm.url="https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana"
LABEL com.ibm.description="This tool translates the IBM Spectrum Scale performance data collected internally \
to the query requests acceptable by the Grafana integrated openTSDB plugin"
LABEL com.ibm.summary="It allows the IBM Spectrum Scale users to perform performance monitoring for IBM Spectrum Scale devices using Grafana"

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

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

ARG USERNAME=bridge
ENV USER=$USERNAME
ARG GROUPNAME=bridge
ENV GROUP=$GROUPNAME
ARG USERID=2001
ENV UID=$USERID
ARG GROUPID=0
ENV GID=$GROUPID

# Create a container user 
RUN if [ "$GID" -gt "0" ]; then groupadd -g $GID $GROUP; else echo "Since root GID specified skipping groupadd"; fi
RUN useradd -rm -d /home/$UID -s /bin/bash -g $GID -u $UID $USER

# Change group ownership
RUN chgrp -R $GID /opt/IBM/bridge
RUN chgrp -R $GID /opt/IBM/zimon
RUN chgrp -R $GID /var/mmfs/gen
RUN chgrp -R $GID /etc/ssl/certs
RUN chgrp -R $GID /var/mmfs/gen
RUN chgrp -R $GID /etc/perfmon-api-keys
RUN chgrp -R $GID $TLSKEYPATH
RUN chgrp -R $GID $LOGPATH

# Set group permissions 
RUN chmod -R g=u /opt/IBM/bridge
RUN chmod -R g=u /opt/IBM/zimon
RUN chmod -R g=u /var/mmfs/gen
RUN chmod -R g=u /etc/ssl/certs
RUN chmod -R g=u /var/mmfs/gen
RUN chmod -R g=u /etc/perfmon-api-keys
RUN chmod -R g=u $TLSKEYPATH
RUN chmod -R g=u $LOGPATH

# Chown all needed files 
RUN chown -R $UID:$GID /opt/IBM/bridge
RUN chown -R $UID:$GID /opt/IBM/zimon
RUN chown -R $UID:$GID /var/mmfs/gen
RUN chown -R $UID:$GID /etc/ssl/certs
RUN chown -R $UID:$GID /etc/perfmon-api-keys
RUN chown -R $UID:$GID $TLSKEYPATH
RUN chown -R $UID:$GID $LOGPATH

# Switch user
USER $GID


CMD ["sh", "-c", "python3 zimonGrafanaIntf.py -c 10 -s $SERVER -r $PROTOCOL -p $PORT -P $SERVERPORT -t $TLSKEYPATH -l $LOGPATH --tlsKeyFile $TLSKEYFILE --tlsCertFile $TLSCERTFILE --apiKeyName $APIKEYNAME --apiKeyValue $APIKEYVALUE"]

EXPOSE 4242 8443

#CMD ["tail", "-f", "/dev/null"]
