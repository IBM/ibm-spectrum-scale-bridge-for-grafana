FROM registry.access.redhat.com/ubi8/python-36

RUN pip3 install --upgrade pip
RUN pip3 install setuptools
RUN pip3 install cherrypy
RUN pip3 install urllib3
RUN pip3 install requests

CMD python3 -V
CMD pip3 list

USER root

RUN mkdir -p /opt/IBM/bridge
ADD . /opt/IBM/bridge


RUN mkdir -p /var/mmfs/gen
RUN mkdir -p /opt/IBM/zimon
COPY ./gpfsConfig/mmsdrfs* /var/mmfs/gen/
COPY ./gpfsConfig/ZIMon* /opt/IBM/zimon/


ARG HTTPPORT=4242
ENV PORT=$HTTPPORT
RUN echo "the HTTP/S port is set to $PORT" 

ARG PERFMONPORT=9981
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

RUN if [ -z "$TLSKEYPATH" ] || [ -z "$TLSCERTFILE" ] || [ -z "$TLSKEYFILE" ] && [ "$PORT" -eq 8443 ]; then echo "TLSKEYPATH FOR SSL CONNECTION NOT SET - ERROR"; exit 1; else echo "PASS"; fi
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

CMD ["sh", "-c", "python3 zimonGrafanaIntf.py -c 10 -s $SERVER -p $PORT -P $SERVERPORT -t $TLSKEYPATH --tlsKeyFile $TLSKEYFILE --tlsCertFile $TLSCERTFILE --apiKeyName $APIKEYNAME --apiKeyValue $APIKEYVALUE"]

EXPOSE 4242 8443

#CMD ["tail", "-f", "/dev/null"]
