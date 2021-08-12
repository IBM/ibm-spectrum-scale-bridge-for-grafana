FROM registry.access.redhat.com/ubi8/ubi:8.4-206

COPY ./requirements/requirements_ubi8.txt  /root/requirements_ubi8.txt

RUN yum install -y python36 python36-devel
RUN /usr/bin/pip3 install --upgrade pip

RUN /usr/bin/pip3 install -r /root/requirements_ubi8.txt
RUN echo "Installed python version: $(/usr/bin/python3 -V)"
RUN echo "Installed python packages: $(/usr/bin/pip3 list)"

USER root

RUN mkdir -p /opt/IBM/bridge
COPY ./source/ /opt/IBM/bridge
COPY LICENSE /opt/IBM/bridge

RUN mkdir -p /var/mmfs/gen
RUN mkdir -p /opt/IBM/zimon
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

ARG CERTPATH=None
ENV TLSKEYPATH=$CERTPATH

ARG KEYFILE=None
ENV TLSKEYFILE=$KEYFILE

ARG CERTFILE=None
ENV TLSCERTFILE=$CERTFILE

ARG KEYNAME=None
ENV APIKEYNAME=$KEYNAME

ARG KEYVALUE=None
ENV APIKEYVALUE=$KEYVALUE

RUN if [ -z "$TLSKEYPATH" ] || [ -z "$TLSCERTFILE" ] || [ -z "$TLSKEYFILE" ] && [ "$PROTOCOL" = "https" ]; then echo "TLSKEYPATH FOR SSL CONNECTION NOT SET - ERROR"; exit 1; else echo "PASS"; fi
RUN echo "the ssl certificates path is set to $TLSKEYPATH" 

ARG PMCOLLECTORIP=0.0.0.0
ENV SERVER=$PMCOLLECTORIP
RUN echo "the pmcollector server ip is set to $SERVER"


WORKDIR /opt/IBM/bridge

ARG DEFAULTLOGPATH='/var/log/ibm_bridge_for_grafana/install.log'
ENV LOGPATH=$DEFAULTLOGPATH
RUN mkdir -p $(dirname $LOGPATH)
RUN echo "the log will use $(dirname $LOGPATH)"
RUN echo "$(pwd)"

RUN touch $LOGPATH
RUN echo "log path: $(dirname $LOGPATH)" >> $LOGPATH
RUN echo "pmcollector_server: $SERVER" >> $LOGPATH
RUN echo "ssl certificates location: $TLSKEYPATH" >> $LOGPATH
RUN echo "HTTP/S port: $PORT" >> $LOGPATH


CMD ["sh", "-c", "python3 zimonGrafanaIntf.py -c 10 -s $SERVER -r $PROTOCOL -p $PORT -P $SERVERPORT -t $TLSKEYPATH --tlsKeyFile $TLSKEYFILE --tlsCertFile $TLSCERTFILE --apiKeyName $APIKEYNAME --apiKeyValue $APIKEYVALUE"]

EXPOSE 4242 8443

#CMD ["tail", "-f", "/dev/null"]
