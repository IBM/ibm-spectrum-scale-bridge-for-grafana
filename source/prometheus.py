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
import json
import analytics
from messages import ERR, MSG
from typing import Optional
from cherrypy.process.plugins import Monitor
from collector import SensorCollector, QueryPolicy
from utils import execution_time, cond_execution_time


class PrometheusExporter(object):
    exposed = True

    def __init__(self, logger, mdHandler, port, raw_data=False):
        self.logger = logger
        self.__md = mdHandler
        self.port = port
        self.raw_data = raw_data
        self.static_sensors_list = ['CPU', 'Memory']
        self.cache_strategy = False
        self.endpoints = {}
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

    @cond_execution_time(enabled=analytics.inspect_special)
    def format_response(self, data) -> [str]:
        resp = []
        for name, metric in data.items():
            header = metric.str_descfmt()
            resp.extend(header)
            for sts in metric.timeseries:
                if len(sts.dps) == 0:
                    self.logger.warning(f"Received no data for : {name} {'|'.join(sts.tags.values())}")
                elif len(sts.dps) > 1:
                    sts.reduce_dps_to_first_not_none(reverse_order=True)
                for _key, _value in sts.dps.items():
                    # Null values are not recognized by Prometheus
                    if _value is not None:
                        sts_resp = SingleTimeSeriesResponse(name, _key,
                                                            _value, sts.tags,
                                                            metric.mtype)
                        formatted_str = sts_resp.str_expfmt()
                        resp.extend(formatted_str)
                    elif metric.mtype == "counter":
                        self.logger.warning(f"Received null value for a counter: {name} {_key} {'|'.join(sts.tags.values())}")
        return resp

    @execution_time()
    def metrics(self, export_sensors: Optional[list] = None, filters: Optional[dict] = None):
        export_sensors = export_sensors or []
        resp = []

        if self.cache_strategy and self.caching_collectors:
            for collector in self.caching_collectors:
                respList = self.format_response(collector.cached_metrics)
                resp.extend(respList)
        elif len(export_sensors) > 0:
            resp = self._metrics(export_sensors, filters)
        else:
            resp = self._metrics(self.static_sensors_list)

        return resp

    def _metrics(self, export_sensors: list, filters: Optional[dict] = None):
        resp = []
        collectors = []

        for sensor in export_sensors:
            collector = self.build_collector(sensor, filters)
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

    @cond_execution_time(enabled=analytics.inspect)
    def build_collector(self, sensor: str, filters: Optional[dict] = None) -> SensorCollector:

        period = self.md.getSensorPeriod(sensor)
        if period < 1:
            self.logger.error(MSG['SensorDisabled'].format(sensor))
            raise cherrypy.HTTPError(400, MSG['SensorDisabled'].format(sensor))

        attrs = {'sensor': sensor, 'period': period}

        if self.raw_data or "counter" in self.TOPO.getSensorMetricTypes(sensor).values():
            attrs.update({'nsamples': period, 'rawData': True})
            self.logger.debug(MSG['SensorForceRawData'].format(sensor))
        else:
            attrs.update({'nsamples': 1})
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    filters[key] = "|".join(value)
            self.logger.debug(f"Collector filters: {filters}")
            attrs['filters'] = filters

        request = QueryPolicy(**attrs)
        collector = SensorCollector(sensor, period, self.logger, request)
        collector.validate_query_filters()

        # self.logger.trace(f'request instance {str(request.__dict__)}')
        # self.logger.trace(f'Created Collector instance {str(collector.__dict__)}')
        return collector

    def GET(self, **params):
        '''Handle partial URLs such as /metrics_cpu
           TODO: add more explanation
        '''
        resp = []

        self.logger.trace(f"Request headers:{str(cherrypy.request.headers)}")
        self.logger.trace(f"Request params:{str(params)}")
        conn = cherrypy.request.headers.get('Host').split(':')
        if len(conn) == 2 and int(conn[1]) != int(self.port):
            self.logger.error(MSG['EndpointNotSupportedForPort'].
                              format(cherrypy.request.script_name, str(conn[1])))
            raise cherrypy.HTTPError(400, ERR[400])

        if self.endpoints and self.endpoints.get(cherrypy.request.script_name,
                                                 None):
            sensor = self.endpoints[cherrypy.request.script_name]
            resp = self.metrics([sensor], params)
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics
        elif '/metrics' == cherrypy.request.script_name:
            # resp = self.metrics()
            self.logger.error(MSG['EndpointNotSupported'].
                              format(cherrypy.request.script_name))
            raise cherrypy.HTTPError(400, ERR[400])

        # /endpoints
        elif '/exporter_metrics_endpoints' == cherrypy.request.script_name:
            resp = self.endpoints.keys()
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /labels
        elif '/labels' == cherrypy.request.script_name:
            resp = {}
            for k, v in self.endpoints.items():
                labels = self.TOPO.getSensorLabels(v)
                if labels:
                    resp[k] = labels
            cherrypy.response.headers['Content-Type'] = 'application/json'
            resp = json.dumps(resp)
            return resp

        # /filters
        elif '/filters' == cherrypy.request.script_name:
            resp = {}
            all_filters = self.TOPO.allFiltersMaps
            for k, v in self.endpoints.items():
                if v in all_filters:
                    resp[k] = all_filters[v]
            cherrypy.response.headers['Content-Type'] = 'application/json'
            resp = json.dumps(resp)
            return resp

        else:
            self.logger.error(MSG['EndpointNotSupported'].
                              format(cherrypy.request.script_name))
            raise cherrypy.HTTPError(400, ERR[400])

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

    def __init__(self, metricname, timestamp, value, tags, type):
        self.metric = metricname
        self.timestamp = timestamp * 1000
        self.value = value
        self.tags = tags
        self.type = type

    def str_expfmt(self) -> [str]:
        myset = []
        mstring = ''

        if self.type == 'histogram':
            mstring = self._str_expfmt_histogram()
        else:
            mstring = self._str_expfmt_gauge()

        myset.append(mstring)
        return myset

    def _str_expfmt_gauge(self) -> str:

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
        return mstring

    def _str_expfmt_histogram(self) -> str:

        labels = ''

        if self.tags:
            for k, v in self.tags.items():
                if k == 'waiters_time_threshold':
                    k = 'le'
                elif v == 'all':
                    v = '+Inf'
                if labels == '':
                    labels = labels + '%s="%s"' % (k, v)
                else:
                    labels = labels + ',%s="%s"' % (k, v)

        if labels:
            fmtstr = '{name}{{{labels}}} {value} {timestamp}'
        else:
            fmtstr = '{name} {value} {timestamp}'
        mstring = fmtstr.format(name=self.metric + '_bucket',
                                labels=labels,
                                value=repr(float(self.value)),
                                timestamp=int(self.timestamp)
                                )
        return mstring
