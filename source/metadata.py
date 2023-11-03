'''
##############################################################################
# Copyright 2023 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##############################################################################

Created on Oct 25, 2023

@author: HWASSMAN
'''

import cherrypy

from queryHandler.QueryHandler import QueryHandler2 as QueryHandler
from queryHandler.Topo import Topo
from queryHandler import SensorConfig
from utils import execution_time
from messages import MSG
from metaclasses import Singleton
from time import sleep


local_cache = []


class MetadataHandler(metaclass=Singleton):

    def __init__(self, **kwargs):
        self.__qh = None
        self.__sensorsConf = None
        self.__metaData = None
        self.__metricsDesc = {}
        self.logger = kwargs['logger']
        self.server = kwargs['server']
        self.port = kwargs['port']
        self.apiKeyName = kwargs['apiKeyName']
        self.apiKeyValue = kwargs['apiKeyValue']
        self.caCertPath = kwargs.get('caCertPath', False)
        self.includeDiskData = kwargs.get('includeDiskData', False)
        self.sleepTime = kwargs.get('sleepTime', 60)

        self.__initializeTables()
        self.__getSupportedMetrics()

    @property
    def qh(self):
        if not self.__qh:
            self.__qh = QueryHandler(self.server, self.port, self.logger, self.apiKeyName, self.apiKeyValue, self.caCertPath)
        return self.__qh

    @property
    def SensorsConfig(self):
        if not self.__sensorsConf or len(self.__sensorsConf) == 0:
            self.__sensorsConf = SensorConfig.readSensorsConfigFromMMSDRFS(self.logger)
            if not self.__sensorsConf:
                raise ValueError(MSG['NoSensorConfigData'])
        return self.__sensorsConf

    @property
    def metaData(self):
        return self.__metaData

    @property
    def metricsDesc(self):
        return self.__metricsDesc

    def getSensorPeriodForMetric(self, metric):
        sensor = self.metaData.getSensorForMetric(metric)
        if not sensor:
            self.logger.error(MSG['MetricErr'].format(metric))
            raise cherrypy.HTTPError(404, MSG['MetricErr'].format(metric))
        return self.getSensorPeriod(sensor)

    def getSensorPeriod(self, sensor):
        bucketSize = 0
        if sensor in ('GPFSPoolCap', 'GPFSInodeCap'):
            sensor = 'GPFSDiskCap'
        elif sensor in ('GPFSNSDFS', 'GPFSNSDPool'):
            sensor = 'GPFSNSDDisk'
        elif sensor == 'DomainStore':
            return 1

        for sensorAttr in self.SensorsConfig:
            if sensorAttr['name'] == str('\"%s\"' % sensor):
                bucketSize = int(sensorAttr['period'])
        return bucketSize

    def __getSupportedMetrics(self) -> dict:
        """ Retrieves all defined (enabled and disabled) metrics by querying topo -m """

        metricSpec = {}

        outp = self.qh.getAvailableMetrics()

        if not outp or outp == "" or outp.startswith("Error:"):
            self.logger.warning(MSG['NoData'])
            return

        for line in outp.split("\n"):
            if len(line) > 0:
                tokens = line.split(";")
                if tokens and len(tokens) > 2:
                    name = tokens[0]
                    desc = tokens[2] or "No description provided"
                    metricSpec[name] = desc
                else:
                    self.logger.moreinfo(MSG['DataWrongFormat'].format(line))
        self.__metricsDesc = metricSpec

    def __initializeTables(self):
        '''Read the topology from ZIMon and (re-)construct
        the tables for metrics, keys, key elements (tag keys)
        and key values (tag values)'''

        self.__qh = QueryHandler(self.server, self.port, self.logger, self.apiKeyName, self.apiKeyValue)
        self.__sensorsConf = SensorConfig.readSensorsConfigFromMMSDRFS(self.logger)
        if not self.__sensorsConf:
            raise ValueError(MSG['NoSensorConfigData'])
        MAX_ATTEMPTS_COUNT = 3
        for attempt in range(1, MAX_ATTEMPTS_COUNT + 1):
            self.__metaData = Topo(self.qh.getTopology())
            if not (self.metaData and self.metaData.topo):
                if attempt > MAX_ATTEMPTS_COUNT:
                    break
                # if no data returned because of the REST HTTP server is still starting, sleep and retry (max 3 times)
                self.logger.warning(MSG['NoDataStartNextAttempt'].format(attempt, MAX_ATTEMPTS_COUNT))
                sleep(self.sleepTime)
            else:
                foundItems = len(self.metaData.allParents) - 1
                sensors = self.metaData.sensorsSpec.keys()
                self.logger.info(MSG['MetaSuccess'])
                self.logger.details(MSG['ReceivAttrValues'].format('parents totally', foundItems))
                self.logger.debug(MSG['ReceivAttrValues'].format('parents', ", ".join(self.metaData.allParents)))
                self.logger.info(MSG['ReceivAttrValues'].format('sensors', ", ".join(sensors)))
                return
        raise ValueError(MSG['NoData'])

    @execution_time()
    def update(self, refresh_all=False):
        '''Read the topology from ZIMon and update
        the tables for metrics, keys, key elements (tag keys)
        and key values (tag values)'''

        if refresh_all:
            self.__sensorsConf = SensorConfig.readSensorsConfigFromMMSDRFS(self.logger)

        self.__metaData = Topo(self.qh.getTopology())
        if not (self.metaData and self.metaData.topo):
            self.logger.error(MSG['NoData'])  # Please check the pmcollector is properly configured and running.
            raise cherrypy.HTTPError(404, MSG[404])
        self.logger.details(MSG['MetaSuccess'])
        self.logger.debug(MSG['ReceivAttrValues'].format('parents', ", ".join(self.metaData.allParents)))
        return ({'msg': MSG['MetaSuccess']})
