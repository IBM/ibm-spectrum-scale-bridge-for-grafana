ARG BUILD_ENV=prod
ARG BASE=registry.access.redhat.com/ubi10/ubi:10.0-1762765098

FROM $BASE AS build_prod
ONBUILD COPY ./requirements/requirements_ubi10.txt /root/requirements_ubi10.txt

FROM $BASE AS build_test
ONBUILD COPY ./requirements/requirements_ubi.in  /root/requirements_ubi.in

FROM $BASE AS build_custom
ONBUILD COPY ./requirements/requirements.in  /root/requirements.in

FROM build_${BUILD_ENV}

ARG BUILD_ENV
ARG BASE

LABEL com.ibm.name="IBM Storage Scale bridge for Grafana"
LABEL com.ibm.vendor="IBM"
LABEL com.ibm.version="9.0.2-dev"
LABEL com.ibm.url="https://github.com/IBM/ibm-spectrum-scale-bridge-for-grafana"
LABEL com.ibm.description="This tool translates the IBM Storage Scale performance data collected internally \
to the query requests acceptable by the Grafana integrated openTSDB plugin"
LABEL com.ibm.summary="It allows the IBM Storage Scale users to perform performance monitoring for IBM Storage Scale devices using Grafana"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG USER=bridge
ARG GROUP=bridge
ARG UID=2001
ARG GID=2099

ARG HTTPPROTOCOL=http
ENV PROTOCOL=$HTTPPROTOCOL

ARG HTTPBASICAUTH=True
ENV BASICAUTH=$HTTPBASICAUTH

ARG AUTHUSER=None
ENV BASICU=$AUTHUSER

ARG AUTHPASSW=NotSet
ENV BASICP=$AUTHPASSW

ARG HTTPPORT=None
ENV PORT=$HTTPPORT

ARG PROMPORT=None
ENV PROMETHEUS=$PROMPORT 

ARG PERFMONPORT=9980
ENV SERVERPORT=$PERFMONPORT

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

ARG DEFAULTLOGPATH='/var/log/ibm_bridge_for_grafana'
ENV LOGPATH=$DEFAULTLOGPATH

ARG DEFAULTLOGLEVEL=15
ENV LOGLEVEL=$DEFAULTLOGLEVEL

ARG RAWDATA=True
ENV RAWCOUNTERS=$RAWDATA

RUN echo "the HTTP/S protocol is set to $PROTOCOL"  && \
    echo "the HTTP/S basic authentication is set to $BASICAUTH"  && \
    echo "the OpentTSDB API HTTP/S port is set to $PORT"  && \
    echo "the Prometheus API HTTPS port is set to $PROMETHEUS"  && \
    echo "the PERFMONPORT port is set to $SERVERPORT" && \
    echo "the pmcollector server ip is set to $SERVER" && \
    echo "the log will use $LOGPATH" 

RUN if [ $(expr "$BASE" : '.*python.*') -eq 0 ]; then \
    yum install -y python3.12 python3.12-pip; \
    if [ "$BUILD_ENV" = "test" ]; then \
    python3 -m pip install pip-tools && \
    python3 -m piptools compile /root/requirements_ubi.in  --output-file /root/requirements_ubi10.txt && \
    echo "Compiled python packages: $(cat /root/requirements_ubi10.txt)"; fi && \
    python3 -m pip install -r /root/requirements_ubi10.txt && \
    echo "Installed python version: $(python3 -V)" && \
    echo "Installed python packages: $(python3 -m pip list)" && \
    yum clean all -y && rm -rf /usr/bin/pip* && rm -rf /usr/lib/python3.12/site-packages/pip* && \
    rm -rf /usr/local/lib/python3.12/site-packages/cherrypy/test; else \
    echo "Already using python container as base image. No need to install it." && \ 
    python3 -m pip install  -r /root/requirements.in && \
    echo "Installed python packages: $(python3 -m pip list)"; fi

#USER root

RUN mkdir -p /opt/IBM/bridge /opt/IBM/zimon /var/mmfs/gen && \
    mkdir -p /etc/ssl/certs /etc/perfmon-api-keys $CERTPATH $LOGPATH

COPY LICENSE /licenses/

COPY ./source/ /opt/IBM/bridge
COPY ./source/gpfsConfig/mmsdrfs* /var/mmfs/gen/
COPY ./source/gpfsConfig/ZIMon* /opt/IBM/zimon/

RUN if [ "${APIKEYVALUE:0:1}" = "/" ]; then ln -s $APIKEYVALUE /etc/perfmon-api-keys; echo "APIKEYVALUE is a PATH"; else echo "APIKEYVALUE not a PATH"; fi && \
    if [ -z "$TLSKEYPATH" ] || [ -z "$TLSCERTFILE" ] || [ -z "$TLSKEYFILE" ] && [ "$PROTOCOL" = "https" ]; then echo "TLSKEYPATH FOR SSL CONNECTION NOT SET - ERROR"; exit 1; else echo "PASS"; fi && \
    echo "the ssl certificates path is set to $TLSKEYPATH" 

# Switch to the working directory
WORKDIR /opt/IBM/bridge
RUN echo "$(pwd)"

# Create a container user 
RUN if [ "$GID" -gt "0" ]; then groupadd -g $GID $GROUP; else echo "Since root GID specified skipping groupadd"; fi && \
    if [ "$UID" -gt "0" ]; then useradd -rm -d /home/$UID -s /bin/bash -g $GID -u $UID $USER; else echo "Since root UID specified skipping useradd"; fi

RUN chmod -R a+w $LOGPATH

# Chown all needed files 
RUN chown -R $UID:$GID /opt/IBM/bridge && \
    chown -R $UID:$GID /opt/IBM/zimon && \
    chown -R $UID:$GID /var/mmfs/gen && \
    chown -R $UID:$GID /etc/ssl/certs && \
    chown -R $UID:$GID /etc/perfmon-api-keys && \
    chown -R $UID:$GID $TLSKEYPATH && \
    chown -R $UID:$GID $LOGPATH

# Switch user
USER $UID

CMD ["sh", "-c", "python3 zimonGrafanaIntf.py -c $LOGLEVEL -s $SERVER -r $PROTOCOL -b $BASICAUTH -u $BASICU -a $BASICP -p $PORT -e $PROMETHEUS -P $SERVERPORT -t $TLSKEYPATH -l $LOGPATH -k $TLSKEYFILE -m $TLSCERTFILE -n $APIKEYNAME -v $APIKEYVALUE -w $RAWCOUNTERS"]

EXPOSE 4242 8443 9250

#CMD ["tail", "-f", "/dev/null"]
