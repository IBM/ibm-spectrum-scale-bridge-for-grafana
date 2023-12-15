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
                    sts_resp = SingleTimeSeriesResponse(name, _key, _value, sts.tags, metric.mtype)
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

    def build_collector(self, sensor) -> SensorCollector:

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

        # /metrics_gpfs_disk
        elif 'metrics_gpfs_disk' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSDisk'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_filesystem
        elif 'metrics_gpfs_filesystem' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSFilesystem'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfsnsddisk
        elif 'metrics_gpfs_nsddisk' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSNSDDisk'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_poolio
        elif 'metrics_gpfs_poolio' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSPoolIO'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_vfsx
        elif 'metrics_gpfs_vfsx' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSVFSX'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfsioc
        elif 'metrics_gpfsioc' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSIOC'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_vio64
        elif 'metrics_gpfs_vio64' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSVIO64'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_pddisk
        elif 'metrics_gpfs_pddisk' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSPDDisk'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_vflush
        elif 'metrics_gpfs_vflush' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSvFLUSH'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_node
        elif 'metrics_gpfs_node' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSNode'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_nodeapi
        elif 'metrics_gpfs_nodeapi' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSNodeAPI'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_filesystemapi
        elif 'metrics_gpfs_filesystemapi' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSFilesystemAPI'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_lroc
        elif 'metrics_gpfs_lroc' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSLROC'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_chms
        elif 'metrics_gpfs_chms' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSCHMS'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_afm
        elif 'metrics_gpfs_afm' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSAFM'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_afmfs
        elif 'metrics_gpfs_afmfs' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSAFMFS'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_afmfset
        elif 'metrics_gpfs_afmfset' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSAFMFSET'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_rpcs
        elif 'metrics_gpfs_rpcs' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSRPCS'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_filesetquota
        elif 'metrics_gpfs_filesetquota' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSFilesetQuota'])
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

        # /metrics_gpfs_diskcap
        elif 'metrics_gpfs_diskcap' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSDiskCap'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_waiters
        elif 'metrics_gpfs_waiters' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSWaiters'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_event_producer
        elif 'metrics_gpfs_event_producer' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSEventProducer'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_mutex
        elif 'metrics_gpfs_mutex' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSMutex'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_condvar
        elif 'metrics_gpfs_condvar' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSCondvar'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_qos
        elif 'metrics_gpfs_qos' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSQoS'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_gpfs_fcm
        elif 'metrics_gpfs_fcm' in cherrypy.request.script_name:
            resp = self.metrics(['GPFSFCM'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_nfsio
        elif 'metrics_nfsio' in cherrypy.request.script_name:
            resp = self.metrics(['NFSIO'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_smb_stats
        elif 'metrics_smb_stats' in cherrypy.request.script_name:
            resp = self.metrics(['SMBStats'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_smb_globalstats
        elif 'metrics_smb_globalstats' in cherrypy.request.script_name:
            resp = self.metrics(['SMBGlobalStats'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_ctdb_stats
        elif 'metrics_ctdb_stats' in cherrypy.request.script_name:
            resp = self.metrics(['CTDBStats'])
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            return resString

        # /metrics_ctdb_dbstats
        elif 'metrics_ctdb_dbstats' in cherrypy.request.script_name:
            resp = self.metrics(['CTDBDBStats'])
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

    def __init__(self, metricname, timestamp, value, tags, type):
        self.metric = metricname
        self.timestamp = timestamp * 1000
        self.value = value if value is not None else 0     # TODO check if we should return None or null
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
