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
from utils import execution_time, synchronized
from messages import ERR, MSG
from metaclasses import Singleton
from time import time, sleep
from datetime import datetime
from threading import Lock


topoUpdateLock = Lock()


class MetadataHandler(metaclass=Singleton):
    exposed = True

    def __init__(self, **kwargs):
        self.__qh = None
        self.__sensorsConf = None
        self.__metaData = None
        self.__metricsDesc = {}
        self.__updateTime = None
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

    @property
    def getUpdateTime(self):
        return self.__updateTime

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
        elif sensor == 'GPFSFCM':
            sensor = 'GPFSFCMDA'
        elif sensor == 'GPFSEXPEL':
            sensor = 'GPFSEXPELNODE'
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
                    self.logger.details(MSG['DataWrongFormat'].format(line))
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
            topoStr = self.qh.getTopology()
            if not topoStr:
                if attempt > MAX_ATTEMPTS_COUNT:
                    break
                # if no data returned because of the REST HTTP server is still starting, sleep and retry (max 3 times)
                self.logger.warning(MSG['NoDataStartNextAttempt'].format(attempt, MAX_ATTEMPTS_COUNT))
                sleep(self.sleepTime)
            else:
                self.__metaData = Topo(topoStr)
                self.__updateTime = time()
                foundItems = len(self.metaData.allParents) - 1
                sensors = self.metaData.sensorsSpec.keys()
                self.logger.info(MSG['MetaSuccess'])
                self.logger.details(MSG['ReceivAttrValues'].format('parents totally', foundItems))
                self.logger.debug(MSG['ReceivAttrValues'].format('parents', ", ".join(self.metaData.allParents)))
                self.logger.info(MSG['ReceivAttrValues'].format('sensors', ", ".join(sensors)))
                return
        raise ValueError(MSG['NoData'])

    @cherrypy.tools.json_out()  # @UndefinedVariable
    def GET(self, **params):
        """ Forward GET REST HTTP/s API incoming requests to Metadata Handler
            available endpoints:
                            /metadata/update
                            /metadata/sensorsconfig
        """
        resp = []

        # /metadata/update
        if '/metadata/update' == cherrypy.request.script_name:
            # cherrypy.response.headers['Content-Type'] = 'application/json'
            resp = self.update()
            # resp = json.dumps(resp)

        # /metadata/time
        elif '/metadata/time' == cherrypy.request.script_name:
            # cherrypy.response.headers['Content-Type'] = 'application/json'
            ts = int(self.getUpdateTime)
            resp = [datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')]

        # /metadata/sensorsconfig
        elif '/metadata/sensorsconfig' == cherrypy.request.script_name:
            # cherrypy.response.headers['Content-Type'] = 'application/json'
            resp = self.SensorsConfig
            # resp = json.dumps(resp)

        # /metadata/sensorsconfig
        elif '/metadata/sensormetrics' == cherrypy.request.script_name:
            resp = {}
            sensors = []
            # cherrypy.response.headers['Content-Type'] = 'application/json'
            if params.get('sensor') is None:
                sensors = self.metaData.sensorsSpec.keys()
            else:
                sensor = params.get('sensor')
                self.logger.info(f"Received request for endpoint /metadata/sensormetrics: {sensor}")
                sensors.append(sensor)
            for sensor in sensors:
                metricsData = self.metaData.getSensorMetricTypes(sensor)
                resp[sensor] = metricsData
            # resp = json.dumps(resp)

        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        # cherrypy.response.headers['Content-Type'] = 'application/json'
        # resp = json.dumps(resp)
        return resp

    @execution_time()
    @synchronized(topoUpdateLock)
    def update(self, refresh_all=False):
        '''Read the topology from ZIMon and update
        the tables for metrics, keys, key elements (tag keys)
        and key values (tag values)'''

        if refresh_all:
            self.__sensorsConf = SensorConfig.readSensorsConfigFromMMSDRFS(self.logger)

        topoStr = self.qh.getTopology()
        if not topoStr:
            self.logger.error(MSG['NoData'])  # Please check the pmcollector is properly configured and running.
            raise cherrypy.HTTPError(404, ERR[404])
        self.__metaData = Topo(topoStr)
        self.__updateTime = time()
        self.logger.details(MSG['MetaSuccess'])
        self.logger.debug(MSG['ReceivAttrValues'].format('parents', ", ".join(self.metaData.allParents)))
        return ({'msg': MSG['MetaSuccess']})
