FROM registry.access.redhat.com/ubi8/ubi:latest

MAINTAINER "Jan-Frode Myklebust <janfrode@tanso.net>"

RUN yum -y install python38
RUN yum clean all
RUN pip3 install cherrypy
RUN mkdir /opt/grafanabridge
COPY zimonGrafanaIntf.py /opt/grafanabridge/zimonGrafanaIntf.py
COPY queryHandler /opt/grafanabridge/queryHandler

ENV SERVER=127.0.0.1
ENV SERVERPORT=9084
ENV LOGFILE=/tmp/zserver.log
ENV LOGLEVEL=20
ENV PORT=4242

EXPOSE 4242/tcp

RUN groupadd -g 63719 grafanabridge
RUN useradd -g 63719 -l -M -s /bin/false -u 63719 grafanabridge
USER grafanabridge

WORKDIR /tmp

CMD ["sh", "-c", "/usr/bin/python3 /opt/grafanabridge/zimonGrafanaIntf.py -s $SERVER -l $LOGFILE -c $LOGLEVEL -p $PORT"]
