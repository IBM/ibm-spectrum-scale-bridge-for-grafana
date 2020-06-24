FROM registry.access.redhat.com/ubi8/ubi:latest

MAINTAINER "Jan-Frode Myklebust <janfrode@tanso.net>"

RUN yum -y install python38
RUN yum clean all
RUN pip3 install cherrypy
RUN mkdir /opt/grafanabridge
COPY zimonGrafanaIntf.py /opt/grafanabridge/zimonGrafanaIntf.py
COPY queryHandler /opt/grafanabridge/queryHandler

ARG ZSERVER
ENV ZSERVER=$zserver

EXPOSE 4242/tcp

CMD ["sh", "-c", "/usr/bin/python3 /opt/grafanabridge/zimonGrafanaIntf.py -s $ZSERVER"]
