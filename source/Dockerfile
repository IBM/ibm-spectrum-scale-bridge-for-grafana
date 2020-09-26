FROM registry.access.redhat.com/ubi8/python-36

RUN pip3 install --upgrade pip
RUN pip3 install setuptools
RUN pip3 install cherrypy

CMD python3 -V
CMD pip3 list

USER root

RUN mkdir -p /opt/IBM/bridge
ADD . /opt/IBM/bridge


RUN mkdir -p /var/mmfs/gen
RUN mkdir -p /opt/IBM/zimon
COPY ./gpfsConfig/mmsdrfs* /var/mmfs/gen/
COPY ./gpfsConfig/ZIMon* /opt/IBM/zimon/



ARG PMCOLLECTORIP=0.0.0.0
ENV SERVER=$PMCOLLECTORIP
RUN echo "the pmcollector server ip is set to $SERVER"


WORKDIR /opt/IBM/bridge

ARG DEFAULTLOGPATH='./logs/zserver.log'
ENV LOGPATH=$DEFAULTLOGPATH
RUN mkdir -p $(dirname $LOGPATH)
RUN echo "the log will use $(dirname $LOGPATH)"
RUN echo "$(pwd)"

RUN touch $LOGPATH
RUN echo "log path: $(dirname $LOGPATH)" >> $LOGPATH
RUN echo "pmcollector_server: $SERVER" >> $LOGPATH

CMD ["sh", "-c", "python3 zimonGrafanaIntf.py -c 10 -s $SERVER"]

EXPOSE 4242

#CMD ["tail", "-f", "/dev/null"]
