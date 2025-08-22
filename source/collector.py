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

Created on Okt 27, 2023

@author: HWASSMAN
'''

import cherrypy
import copy
import analytics
from queryHandler.Query import Query
from messages import MSG
from collections import defaultdict
from typing import Optional, Any, List
from threading import Thread
from metadata import MetadataHandler
from bridgeLogger import getBridgeLogger
from refresher import TopoRefreshManager
from utils import classattributes, cond_execution_time, get_runtime_statistics


local_cache = set()


class TimeSeries(object):

    def __init__(self, columnInfo, dps, filtersMap, defaultLabels):
        self.metricname = columnInfo.keys[0].metric
        self.columnInfo = columnInfo
        self.dps = dps
        self.tags = defaultdict(list)
        self.aggregatedTags = []

        self.parse_tags(filtersMap, defaultLabels)

    @cond_execution_time(enabled=analytics.inspect_special)
    def parse_tags(self, filtersMap, defaultLabels):
        logger = getBridgeLogger()
        if not (filtersMap and defaultLabels):
            logger.trace(f'No labels, no filters in local cache for {self.columnInfo.keys[0].__str__()}')
            return
        tagsDict = defaultdict(set)
        for key in self.columnInfo.keys:
            ident = [key.parent]
            ident.extend(key.identifier)
            logger.trace(MSG['ReceivAttrValues'].format(
                'Single ts identifiers', '|'.join(ident)))
            found = False
            for filtersDict in filtersMap:
                if set(filtersDict.values()) == set(ident):
                    # logger.trace(MSG['ReceivAttrValues'].format(
                    #    'filtersKeys', ', '.join(filtersDict.keys())))
                    if len(self.columnInfo.keys) == 1:
                        self.tags = filtersDict
                    else:
                        for _key, _value in filtersDict.items():
                            tagsDict[_key].add(_value)
                    found = True
                    break
            # detected zimon key, do we need refresh local TOPO?
            if not found:
                topoRefresher = TopoRefreshManager()
                topoRefresher.update_local_cache(ident)

                constructedTags = dict(zip(defaultLabels, ident))
                if len(self.columnInfo.keys) == 1:
                    self.tags = constructedTags
                else:
                    for _key, _value in constructedTags.items():
                        tagsDict[_key].add(_value)

        for _key, _values in tagsDict.items():
            if len(_values) > 1:
                self.aggregatedTags.append(_key)
            else:
                self.tags[_key] = _values.pop()

    @get_runtime_statistics(enabled=analytics.runtime_profiling)
    def reduce_dps_to_first_not_none(self, reverse_order=False):
        """Reduce multiple data points(dps) of a single
           TimeSeries to the first non null value in a sorted order.
           Optionally the order of timestamps can be reversed.
        """
        if len(self.dps) > 1:
            logger = getBridgeLogger()
            timestamps = sorted(self.dps.keys(), reverse=reverse_order)
            self.dps = next((
                {timestmp: self.dps[timestmp]} for timestmp in timestamps if
                self.dps[timestmp] is not None), {})
            if len(self.dps) == 0:
                logger.warning(f'Received null values in all data points for {self.metricname}')


class MetricTimeSeries(object):

    def __init__(self, name: str, desc: str, type: Optional[str] = None):
        self.mtype = type or 'gauge'
        self.mname = name
        self.desc = desc
        self.timeseries: list[TimeSeries] = []

    def __format__(self, spec):
        return f'{self.mname}_mTS'

    def str_descfmt(self, original_counters=False) -> [str]:
        """Format MetricTimeSeries description rows
            Output format:
                '''# HELP {name} {desc}'''
                '''# TYPE {name} {mtype}'''
        """

        myset = []

        expfmt = '''# HELP {name} {desc}'''.format(
            name=self.mname,
            desc=self.desc,
        )
        myset.append(expfmt)
        expfmt1 = '''# TYPE {name} {mtype}'''.format(
            name=self.mname,
            mtype=self.mtype,
        )
        myset.append(expfmt1)

        return myset


class SensorTimeSeries(object):

    def __init__(self, sensor: str, period: str):
        self.sensor = sensor
        self.period = period
        self.metrics = {}
        self.filtersMap = self._get_all_filters()
        self.labels = self._get_sensor_labels()

    @property
    def md(self):
        return MetadataHandler()

    def cleanup_metrics_values(self) -> None:
        for name in self.metrics.keys():
            self.metrics[name].timeseries = []

    def setup_static_metrics_data(self, include_metrics: Optional[list] = None,
                                  exclude_metrics: Optional[list] = None):

        include_metrics = include_metrics or []
        exclude_metrics = exclude_metrics or []

        metrics = self.md.metaData.getSensorMetricNames(self.sensor)
        if len(metrics) < 1:
            return                       # this should not happen

        for exclude_metric in exclude_metrics:
            metrics.remove(exclude_metric)

        if len(include_metrics) > 0 and (set(include_metrics).
                                         issubset(set(metrics))):
            self._setup_static_metrics_data(include_metrics)
        else:
            self._setup_static_metrics_data(metrics)

    def _setup_static_metrics_data(self, metric_names: List[str]):
        mDict = {}
        spec = self.md.metricsDesc
        metricsTypes = self.md.metaData.metricsType

        for name in metric_names:
            mtype = 'gauge'
            if self.sensor == 'GPFSWaiters':
                mtype = 'histogram'
            elif metricsTypes.get(name, None) == "counter":
                mtype = 'counter'
            ts = MetricTimeSeries(name,
                                  spec.get(name, "Desc not found"),
                                  mtype)
            mDict[name] = ts
        self.metrics = mDict

    def _get_all_filters(self):
        return self.md.metaData.getAllFilterMapsForSensor(self.sensor)

    def _get_sensor_labels(self):
        return self.md.metaData.getSensorLabels(self.sensor)


@classattributes(dict(metricsaggr=None, filters=None, grouptags=None,
                      start='', end='', nsamples=0, duration=0,
                      dsBucketSize=0, dsOp='', rawData=False, dpsArrays=False),
                 ['sensor', 'period'])
class QueryPolicy(object):

    def __init__(self, **kwargs):
        pass

    @property
    def md(self):
        return MetadataHandler()

    def get_zimon_query(self):
        '''Returns zimon query string '''
        query = Query(includeDiskData=self.md.includeDiskData)
        query.normalize_rates = False
        query.rawData = self.rawData

        if not self.metricsaggr and not self.sensor:
            raise ValueError('Missing metric or sensor name')

        if self.metricsaggr:
            for key, value in self.metricsaggr.items():
                query.addMetric(key, value)
        else:
            query.addMetricsGroup(self.sensor)

        query.setTime(tstart=self.start, tend=self.end,
                      num_buckets=self.nsamples, duration=self.duration)

        if self.grouptags:
            for tag in self.grouptags:
                query.addGroupByMetric(tag)

        if self.filters:
            for key, value in self.filters.items():
                query.addFilter(key, value)

        query.setBucketSize(self._calc_zimon_query_bucketsize())

        return query

    def _calc_zimon_query_bucketsize(self):

        logger = getBridgeLogger()

        bucketSize = self.period

        if self.dsBucketSize and self.dsBucketSize > bucketSize:
            if not self.dsOp:
                bucketSize = self.dsBucketSize
                logger.trace(MSG['BucketsizeChange'].format(
                    self.dsBucketSize, bucketSize))
        else:
            logger.details(MSG['BucketsizeToPeriod'].format(bucketSize))

        return bucketSize


class SensorCollector(SensorTimeSeries):
    running = False
    thread = None

    def __init__(self, sensor: str, period: str, logger, request: QueryPolicy,
                 *args: Any, **kwargs: Any) -> None:
        super().__init__(sensor, period)
        self.__query = None
        self.__ds_interval = None
        self.request = request
        self.logger = logger
        self.removeNoData = False
        self.cache = False
        self.cached_metrics = {}

        self.prepare_static_metrics_data()

    def __format__(self, spec):
        return f'{self.sensor}_Collector'

    @property
    def md(self):
        return MetadataHandler()

    @property
    def query(self):
        if not self.__query:
            self.__query = self.request.get_zimon_query()
        return self.__query

    @property
    def dsInterval(self):
        if self.__ds_interval is None:
            self.__ds_interval = self._calc_ds_interval()
        return self.__ds_interval

    def start_collect(self):
        """ Function to start collect in a thread"""
        self.running = True
        if not self.thread:
            thread_name = list(
                self.request.metricsaggr.keys())[0] +\
                '_Collector' if self.request.metricsaggr else self.sensor +\
                '_Collector'
            self.thread = Thread(name=thread_name, target=self.collect)
            self.thread.start()
            self.thread.name += '_' + str(self.thread.ident)
            self.logger.trace(
                MSG['StartCustomThread'].format(self.thread.name))

    def collect(self) -> None:
        self._collect()
        if self.cache:
            self.cached_metrics = copy.deepcopy(self.metrics)
            self.cleanup_metrics_values()

    def stop_collect(self):
        """ Function to break collecting """
        try:
            self.running = False
            if self.thread:
                self.thread.join()
                cherrypy.engine.log(
                    MSG['StopCustomThread'].format(self.thread.name))
                self.logger.trace(
                    MSG['StopCustomThread'].format(self.thread.name))
                self.thread = None
        except KeyboardInterrupt:
            print(f"Received KeyboardInterrupt during \
            stopping the thread {self.thread.name}")

    def _calc_ds_interval(self) -> int:

        dsInterval = 0

        if self.query and self.request:
            if self.request.dsOp and self.request.dsBucketSize > int(
                    self.query.bucket_size):
                dsInterval = int(
                    self.request.dsBucketSize / int(self.query.bucket_size))
        return dsInterval

    def _collect(self):
        '''Executes zimon query and returns results'''

        try:
            res = self.md.qh.runQuery(self.query)
        except Exception as e:
            self.logger.error(MSG['QueryError'].format(e))
            return

        if res is None:
            self.logger.error(MSG['NoData'])
            # self.stop_collect()
            # raise cherrypy.HTTPError(400, MSG['NoData'])
            return
        self.logger.details("res.rows length: {}".format(len(res.rows)))
        if self.removeNoData:
            res.remove_rows_with_no_data()

        if len(res.rows) < 1:
            return
        rows = res.rows
        if self.request.dsOp and self.dsInterval and len(res.rows) > 1:
            self.logger.trace(MSG['DownsampleAggregation'].format(
                str(self.request.dsOp) + '-' + str(self.dsInterval),
                list(self.request.metricsaggr.keys())[0]))
            rows = res.downsampleResults(self.dsInterval, self.request.dsOp)

        if self.request.dpsArrays:
            columnValues = defaultdict(list)
            for row in rows:
                for value, columnInfo in zip(row.values, res.columnInfos):
                    columnValues[columnInfo].append([row.tstamp, value])
        else:
            columnValues = defaultdict(dict)
            for row in rows:
                for value, columnInfo in zip(row.values, res.columnInfos):
                    columnValues[columnInfo][row.tstamp] = value

        for columnInfo, dps in columnValues.items():
            ts = TimeSeries(columnInfo, dps, self.filtersMap, self.labels)
            if self.metrics.get(columnInfo.keys[0].metric) is not None:
                self.logger.trace(MSG['MetricInResults'].format(
                    columnInfo.keys[0].metric))
                self.metrics[columnInfo.keys[0].metric].timeseries.append(ts)
            else:
                # metric not in Collector.metrcs
                self.logger.warning(MSG['MetricNotInResults'].format(
                    columnInfo.keys[0].metric))
                mt = MetricTimeSeries(columnInfo.keys[0].metric, '')
                mt.timeseries.append(ts)
                self.metrics[columnInfo.keys[0].metric] = mt
        # self.logger.info(f'rows data {str(columnValues)}')

    @cond_execution_time(enabled=analytics.inspect_special)
    def prepare_static_metrics_data(self):
        incl_metrics = list(self.request.metricsaggr.keys()
                            ) if self.request.metricsaggr else None
        self.setup_static_metrics_data(incl_metrics)

    @cond_execution_time(enabled=analytics.inspect_special)
    def validate_query_filters(self):
        # check filterBy settings
        if self.request.filters:

            if not self.filtersMap:
                self.logger.error(MSG['FilterByErr'])
                raise cherrypy.HTTPError(
                    400, MSG['AttrNotValid'].format('filter'))

            filtersMap = self.filtersMap[:]

            groupFilter = {}
            conditionalFilter = {}
            singleFilter = {}
            for key, value in self.request.filters.items():
                if str(key).find('*') != -1:
                    foundKeys = self.md.metaData.getAllKeysForTagValue(value)
                    for foundKey in foundKeys:
                        singleFilter[foundKey] = value
                elif str(value).find('*') != -1:
                    groupFilter[key] = self.md.metaData.getAllValuesForTagName(key)
                elif str(value).find('|') != -1:
                    conditionalFilter[key] = value.split('|')
                else:
                    singleFilter[key] = value

            iteritems = lambda d: (getattr(d, 'iteritems', None) or d.items)()
            if singleFilter:
                for filtersDict in reversed(filtersMap):
                    if not all((k in filtersDict and filtersDict[k] == v) for
                               k, v in iteritems(singleFilter)):
                        filtersMap.remove(filtersDict)
            if conditionalFilter:
                for filtersDict in reversed(filtersMap):
                    if not all((k in filtersDict and filtersDict[k] in v) for
                               k, v in iteritems(conditionalFilter)):
                        filtersMap.remove(filtersDict)
            if groupFilter:
                for filtersDict in reversed(filtersMap):
                    if not all((k in filtersDict and filtersDict[k] in v) for
                               k, v in iteritems(groupFilter)):
                        filtersMap.remove(filtersDict)

            if not filtersMap:
                self.logger.error(MSG['FilterByErr'])
                raise cherrypy.HTTPError(
                    400, MSG['AttrNotValid'].format('filter'))

    @cond_execution_time(enabled=analytics.inspect_special)
    def validate_group_tags(self):
        # check groupBy settings
        if self.request.grouptags:
            filter_keys = set()
            for filter in self.filtersMap:
                filter_keys.update(filter.keys())
            if not filter_keys:
                self.logger.error(MSG['GroupByErr'])
                raise cherrypy.HTTPError(
                    400, MSG['AttrNotValid'].format('groupBy key'))
            if not (set(self.request.grouptags)).issubset(filter_keys):
                self.logger.error(MSG['AttrNotValid'].format('groupBy key'))
                self.logger.error(MSG['ReceivAttrValues'].format(
                    'groupBy keys', ", ".join(filter_keys)))
                raise cherrypy.HTTPError(
                    400, MSG['AttrNotValid'].format('groupBy key'))
