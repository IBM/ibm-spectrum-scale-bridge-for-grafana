FROM registry.access.redhat.com/ubi8/ubi as pmcollector


#
# Installing tools required by pmcollector.
#

RUN yum install -y libicu gdbm-devel boost-devel python27

#RUN yum install -y libicu

#RUN yum install -y boost-regex 

#RUN yum list all

#
# Installing few tools in the image that help to debug it easier.
#
RUN yum install -y gcc gcc-c++ make net-tools m4 libaio ksh which iproute procps-ng util-linux openssh-clients openssh-server setup elfutils-libelf-devel hostname kmod pciutils iputils bind-utils

#RUN yum list all



#
# Installing Spectrum Scale pmcollector
#
ARG ARTIKEY
RUN curl --fail -H "X-Jfrog-Art-Api: $ARTIKEY" -O https://na.artifactory.swg-devops.com/artifactory/res-fsaas-generic-local/ScaleRPMs/gpfs.gss.pmcollector-5.0.4-2.el8.x86_64.rpm
RUN mkdir -p /opt/IBM/zimon/config
RUN mkdir -p /opt/IBM/zimon/zdata
RUN rpm -ivh gpfs.gss.pmcollector-5.0.4-2.el8.x86_64.rpm


COPY ZIMonCollector.cfg /opt/IBM/zimon/config/ZIMonCollector.cfg

#
# Create a user 'scalepm' under 'root' group
#
RUN groupadd -g 1099 scalepm
RUN useradd -rm -d /home/1001 -s /bin/bash -g 1099 -u 1001 scalepm

#
# Chown all the files to the zimon 'scalepm' user.
#
RUN chown -R 1001:1099 /opt/IBM/zimon
RUN chown -R 1001:1099 /var/log/zimon
RUN chown -R 1001:1099 /var/run/perfmon

#
# Switch to user 'scalepm'
#
USER 1001

CMD ["/opt/IBM/zimon/sbin/pmcollector", "-C", "/opt/IBM/zimon/config/ZIMonCollector.cfg", "-R", "/var/run/perfmon"]

# helpful for debugging
#CMD ["tail", "-f", "/dev/null"]


EXPOSE 4739 9085 9084 9094
