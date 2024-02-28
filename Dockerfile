ARG BASE=registry.access.redhat.com/ubi9/ubi:9.3-1552
FROM $BASE

LABEL com.ibm.name="IBM Storage Scale bridge for Grafana"
LABEL com.ibm.vendor="IBM"
LABEL com.ibm.version="7.1.2"
LABEL com.ibm.url="https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana"
LABEL com.ibm.description="This tool translates the IBM Storage Scale performance data collected internally \
to the query requests acceptable by the Grafana integrated openTSDB plugin"
LABEL com.ibm.summary="It allows the IBM Storage Scale users to perform performance monitoring for IBM Storage Scale devices using Grafana"

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ARG USERNAME=bridge
ENV USER=$USERNAME

ARG GROUPNAME=bridge
ENV GROUP=$GROUPNAME

ARG USERID=2001
ENV UID=$USERID

ARG GROUPID=0
ENV GID=$GROUPID

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

ARG KEYFILE=None
ENV TLSKEYFILE=$KEYFILE

ARG CERTFILE=None
ENV TLSCERTFILE=$CERTFILE

ARG KEYNAME=None
ENV APIKEYNAME=$KEYNAME

ARG KEYVALUE=None
ENV APIKEYVALUE=$KEYVALUE

ARG PMCOLLECTORIP=0.0.0.0
ENV SERVER=$PMCOLLECTORIP
RUN echo "the pmcollector server ip is set to $SERVER"

ARG DEFAULTLOGPATH='/var/log/ibm_bridge_for_grafana'
ENV LOGPATH=$DEFAULTLOGPATH
RUN echo "the log will use $LOGPATH"

COPY ./requirements/requirements_ubi9.txt  /root/requirements_ubi9.txt
# COPY ./requirements/requirements_ubi.in  /root/requirements_ubi.in

RUN yum install -y python39 python3-pip

# RUN /usr/bin/python3 -m pip install pip-tools && \
#     /usr/bin/python3 -m piptools compile /root/requirements_ubi.in  --output-file /root/requirements_ubi9.txt && \
#     echo "Compiled python packages: $(cat /root/requirements_ubi9.txt)"

RUN /usr/bin/python3 -m pip install -r /root/requirements_ubi9.txt && \
    echo "Installed python version: $(/usr/bin/python3 -V)" && \
    echo "Installed python packages: $(/usr/bin/python3 -m pip list)"

USER root

RUN mkdir -p /opt/IBM/bridge /opt/IBM/zimon /var/mmfs/gen && \
    mkdir -p /etc/ssl/certs /etc/perfmon-api-keys $CERTPATH $LOGPATH

COPY LICENSE /licenses/

COPY ./source/ /opt/IBM/bridge
COPY ./source/gpfsConfig/mmsdrfs* /var/mmfs/gen/
COPY ./source/gpfsConfig/ZIMon* /opt/IBM/zimon/

RUN if [ "${APIKEYVALUE:0:1}" = "/" ]; then ln -s $APIKEYVALUE /etc/perfmon-api-keys; echo "APIKEYVALUE is a PATH"; else echo "APIKEYVALUE not a PATH"; fi && \
    if [ -z "$TLSKEYPATH" ] || [ -z "$TLSCERTFILE" ] || [ -z "$TLSKEYFILE" ] && [ "$PROTOCOL" = "https" ]; then echo "TLSKEYPATH FOR SSL CONNECTION NOT SET - ERROR"; exit 1; else echo "PASS"; fi
RUN echo "the ssl certificates path is set to $TLSKEYPATH" 

# Switch to the working directory
WORKDIR /opt/IBM/bridge
RUN echo "$(pwd)"

# Create a container user 
RUN if [ "$GID" -gt "0" ]; then groupadd -g $GID $GROUP; else echo "Since root GID specified skipping groupadd"; fi && \
    useradd -rm -d /home/$UID -s /bin/bash -g $GID -u $UID $USER

# Change group ownership
RUN chgrp -R $GID /opt/IBM/bridge && \
    chgrp -R $GID /opt/IBM/zimon && \
    chgrp -R $GID /var/mmfs/gen && \
    chgrp -R $GID /etc/ssl/certs && \
    chgrp -R $GID /etc/perfmon-api-keys && \
    chgrp -R $GID $TLSKEYPATH && \
    chgrp -R $GID $LOGPATH

# Set group permissions 
RUN chmod -R g=u /opt/IBM/bridge && \
    chmod -R g=u /opt/IBM/zimon && \
    chmod -R g=u /var/mmfs/gen && \
    chmod -R g=u /etc/ssl/certs && \
    chmod -R g=u /etc/perfmon-api-keys && \
    chmod -R g=u $TLSKEYPATH && \
    chmod -R g=u $LOGPATH

# Chown all needed files 
RUN chown -R $UID:$GID /opt/IBM/bridge && \
    chown -R $UID:$GID /opt/IBM/zimon && \
    chown -R $UID:$GID /var/mmfs/gen && \
    chown -R $UID:$GID /etc/ssl/certs && \
    chown -R $UID:$GID /etc/perfmon-api-keys && \
    chown -R $UID:$GID $TLSKEYPATH && \
    chown -R $UID:$GID $LOGPATH

# Switch user
USER $GID

CMD ["sh", "-c", "python3 zimonGrafanaIntf.py -c 10 -s $SERVER -r $PROTOCOL -p $PORT -P $SERVERPORT -t $TLSKEYPATH -l $LOGPATH --tlsKeyFile $TLSKEYFILE --tlsCertFile $TLSCERTFILE --apiKeyName $APIKEYNAME --apiKeyValue $APIKEYVALUE"]

EXPOSE 4242 8443

#CMD ["tail", "-f", "/dev/null"]
