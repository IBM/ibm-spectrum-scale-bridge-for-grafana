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

Created on Oct 30, 2023

@author: HWASSMAN
'''

import cherrypy
import copy
import json
from messages import MSG
from typing import Optional
from cherrypy.process.plugins import Monitor
from collector import SensorCollector, QueryPolicy
from utils import execution_time


class PrometheusExporter(object):
    exposed = True

    def __init__(self, logger, mdHandler, port):
        self.logger = logger
        self.__md = mdHandler
        self.port = port
        self.static_sensors_list = ['CPU', 'Memory', 'GPFSFileset']
        self.cache_strategy = False
        self.caching_collectors = []
        if self.cache_strategy:
            self.initialize_cache_collectors()

    @property
    def md(self):
        return self.__md

    @property
    def qh(self):
        return self.__md.qh

    @property
    def TOPO(self):
        return self.__md.metaData

    def format_response(self, data) -> [str]:
        resp = []
        for name, metric in data.items():
            header = metric.str_descfmt()
            resp.extend(header)
            for sts in metric.timeseries:
                for _key, _value in sts.dps.items():
                    sts_resp = SingleTimeSeriesResponse(name, _key, _value, sts.tags)
                    self.logger.trace(f'sts_resp.str_expfmt output: {sts_resp.str_expfmt()}')
                    resp.extend(sts_resp.str_expfmt())
        return resp

    @execution_time()
    def metrics(self, export_sensors: Optional[list] = None):
        export_sensors = export_sensors or []
        resp = []

        if self.cache_strategy and self.caching_collectors:
            for collector in self.caching_collectors:
                respList = self.format_response(collector.cached_metrics)
                resp.extend(respList)
        elif len(export_sensors) > 0:
            resp = self._metrics(export_sensors)
        else:
            resp = self._metrics(self.static_sensors_list)

        return resp

    def _metrics(self, export_sensors: list):
        resp = []
        collectors = []

        for sensor in export_sensors:
            collector = self.build_collector(sensor)
            collectors.append(collector)

        for collector in collectors:
            collector.start_collect()

        for collector in collectors:
            collector.thread.join()

        for collector in collectors:
            self.logger.trace('Finished custom thread %r.' % collector.thread.name)
            respList = self.format_response(collector.metrics)
            resp.extend(respList)
        return resp

    def initialize_cache_collectors(self):
        for sensor in self.static_sensors_list:
            collector = self.build_collector(sensor)
            self.caching_collectors.append(collector)
            thread_name = 'Monitor_' + sensor
            Monitor(cherrypy.engine,
                    collector.collect,
                    frequency=collector.period,
                    name=thread_name).subscribe()

    def build_collector(self, sensor) -> SensorCollector :

        period = self.md.getSensorPeriod(sensor)
        if period < 1:
            self.logger.error(MSG['SensorDisabled'].format(sensor))
            raise cherrypy.HTTPError(400, MSG['SensorDisabled'].format(sensor))

        attrs = {}

        # if self.cache_strategy:
        attrs = {'sensor': sensor, 'period': period, 'nsamples': 1}
        request = QueryPolicy(**attrs)
        collector = SensorCollector(sensor, period, self.logger, request)

        self.logger.trace(f'request instance {str(request.__dict__)}')
        self.logger.trace(f'Created Collector instance {str(collector.__dict__)}')
        return collector

    def GET(self, **params):
        '''Handle partial URLs such as /metrics_cpu
           TODO: add more explanation
        '''
        resp = []

        conn = cherrypy.request.headers.get('Host').split(':')
        if int(conn[1]) != int(self.port):
            raise cherrypy.HTTPError(400, MSG[400])

        # /update
        if 'update' in cherrypy.request.script_name:
            # cherrypy.response.headers['Content-Type'] = 'application/json'
            resp = self.md.update()

        # /metrics_cpu
        elif 'metrics_cpu' in cherrypy.request.script_name:
            resp = self.metrics(['CPU'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_load
        elif 'metrics_load' in cherrypy.request.script_name:
            resp = self.metrics(['Load'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_memory
        elif 'metrics_memory' in cherrypy.request.script_name:
            resp = self.metrics(['Memory'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_network
        elif 'metrics_network' in cherrypy.request.script_name:
            resp = self.metrics(['Network'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_netstat
        elif 'metrics_netstat' in cherrypy.request.script_name:
            resp = self.metrics(['Netstat'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_diskfree
        elif 'metrics_diskfree' in cherrypy.request.script_name:
            resp = self.metrics(['DiskFree'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_fileset
        elif 'metrics_gpfs_fileset' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSFileset'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_pool
        elif 'metrics_gpfs_pool' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSPool'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics
        elif 'metrics' in cherrypy.request.script_name:
            resp = self.metrics()
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        elif 'aggregators' in cherrypy.request.script_name:
            resp = ["noop", "sum", "avg", "max", "min", "rate"]

        elif 'config/filters' in cherrypy.request.script_name:
            supportedFilters = {}
            filterDesc = {}
            filterDesc['description'] = '''Accepts an exact value or a regular expressions and matches against
            values for the given tag. The value can be omitted if the filter is used to specify groupBy on the tag only.'''
            filterDesc['examples'] = '''node=pm_filter(machine1), node=pm_filter(machine[1-6]), node=pm_filter(m1|m2),
            node=pm_filter(mac.*), node=pm_filter((?!^z).*)'''
            supportedFilters['pm_filter'] = filterDesc
            resp = supportedFilters

        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Content-Type'] = 'application/json'
        resp = json.dumps(resp)
        return resp

    def OPTIONS(self):
        # print('options_post')
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, NEW, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Accept'
        cherrypy.response.headers['Access-Control-Max-Age'] = 604800


class SingleTimeSeriesResponse():

    def __init__(self, metricname, timestamp, value, tags):
        self.metric = metricname
        self.timestamp = timestamp * 1000
        self.value = value if value is not None else 0     # TODO check if we should return None or null
        self.tags = tags

    def str_expfmt(self) -> str:
        myset = []

        if self.tags:
            labels = ','.join('%s="%s"' % (k, v) for k, v in self.tags.items())
        else:
            labels = ''

        if labels:
            fmtstr = '{name}{{{labels}}} {value} {timestamp}'
        else:
            fmtstr = '{name} {value} {timestamp}'
        mstring = fmtstr.format(name=self.metric,
                                labels=labels,
                                value=repr(float(self.value)),
                                timestamp=int(self.timestamp)
                                )
        myset.append(mstring)
        return myset
