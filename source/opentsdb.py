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

Created on Oct 24, 2023

@author: HWASSMAN
'''

import cherrypy
import re
from messages import ERR, MSG
from collections import defaultdict
from collector import SensorCollector, QueryPolicy
from utils import getTimeMultiplier
from typing import List


class OpenTsdbApi(object):
    exposed = True

    def __init__(self, logger, mdHandler, port):
        self.logger = logger
        self.__md = mdHandler
        self.port = port

    @property
    def md(self):
        return self.__md

    @property
    def qh(self):
        return self.__md.qh

    @property
    def TOPO(self):
        return self.__md.metaData

    def format_response(self, data: dict, jreq: dict) -> List[dict]:
        respList = []
        for name, metric in data.items():
            for st in metric.timeseries:
                res = SingleTimeSeriesResponse(jreq.get('inputQuery'), st.dps,
                                               jreq.get('showQuery'),
                                               jreq.get('globalAnnotations'),
                                               st.tags, st.aggregatedTags)
                cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
                self.logger.trace(f'OpenTSDB queryResponse: {str(res.__dict__)}')
                respList.append(res.__dict__)
        return respList

    def query(self, jreq: dict) -> List[dict]:
        resp = []
        collectors = []

        # A request query can include more than one sub query
        # For more details please check openTSDB API
        # /api/query
        for i, q in enumerate(jreq.get('queries')):

            q['index'] = i

            inMetric = q.get('metric')
            if inMetric not in self.TOPO.getAllEnabledMetricsNames:
                self.logger.error(MSG['MetricErr'].format(inMetric))
                raise cherrypy.HTTPError(404, MSG['MetricErr'].format(inMetric))
            else:
                self.logger.details(
                    MSG['ReceivedQuery'].format(
                        str(q), str(jreq.get('start')), str(jreq.get('end'))))

            request_data = jreq.copy()
            request_data.pop('queries')
            request_data['inputQuery'] = q

            collector = self.build_collector(request_data)
            collectors.append((collector, request_data))

        for collector, _ in collectors:
            collector.start_collect()

        for collector, _ in collectors:
            collector.thread.join()

        for collector, request_data in collectors:
            # cherrypy.engine.log('Finished custom thread %r.' % collector.thread.name)
            # self.logger.debug(MSG['StartWatchingFiles'].format(self.paths))
            self.logger.trace('Finished custom thread %r.' % collector.thread.name)

            coll_resp = self.format_response(collector.metrics, request_data)
            cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
            resp.extend(coll_resp)

        return resp

    def build_collector(self, jreq: dict) -> SensorCollector:

        q = jreq.get('inputQuery')

        period = self.md.getSensorPeriodForMetric(q.get('metric'))
        if period < 1:
            self.logger.error(MSG['SensorDisabled'].format(q.get('metric')))
            raise cherrypy.HTTPError(
                400, MSG['SensorDisabled'].format(q.get('metric')))

        sensor = self.TOPO.getSensorForMetric(q.get('metric'))

        args = {}
        args['metricsaggr'] = {q.get('metric'): q.get('aggregator')}
        args['start'] = str(int(int(str(jreq.get('start'))) / 1000))
        if jreq.get('end') is not None:
            args['end'] = str(int(int(str(jreq.get('end'))) / 1000))

        if q.get('downsample'):
            args['dsOp'] = self._get_downsmpl_op(q.get('downsample'))
            args['dsBucketSize'] = self._calc_bucket_size(q.get('downsample'))

        if q.get('filters'):
            filters, grouptags = self._parse_input_query_filters(
                q.get('filters'))
            args['filters'] = filters
            args['grouptags'] = grouptags

        args['rawData'] = q.get('explicitTags', False)

        args['sensor'] = sensor
        args['period'] = period

        request = QueryPolicy(**args)
        self.logger.trace(f'request instance {str(request.__dict__)}')

        collector = SensorCollector(sensor, period, self.logger, request)
        self.logger.trace(f'Collector instance {str(collector.__dict__)}')

        collector.validate_query_filters()
        collector.validate_group_tags()

        return collector

    def suggest(self, params: dict) -> list:
        resp = []

        if params.get('q'):
            searchStr = params['q'].strip()
            self.logger.trace(f'Suggest for {searchStr} called')
            # if '*' and tagv, then
            # it denotes a grouping key value: do not process
            if not (searchStr == '*' and params['type'] == 'tagv'):
                # Since grafana sends the candidate string quickly,
                # one character at a time, it
                # is likely that the reg exp compilation will fail.
                try:
                    regex = re.compile("^" + searchStr + ".*")
                except re.error:
                    self.logger.debug(MSG['SearchErr'].format(
                        searchStr, str(re.error)))
                    regex = None  # failed to compile, return empty response
                if regex:
                    try:
                        if params['type'] == 'metrics':
                            resp = sorted([m.group(0) for
                                           item in self.TOPO.getAllEnabledMetricsNames
                                           for m in [regex.search(item)] if m])
                        elif params['type'] == 'tagk':
                            resp = sorted([m.group(0) for
                                          item in self.TOPO.getAllAvailableTagNames
                                          for m in [regex.search(item)] if m])
                        elif params['type'] == 'tagv':
                            resp = sorted([m.group(0) for
                                          item in self.TOPO.getAllAvailableTagValues
                                          for m in [regex.search(item)] if m])
                    except Exception as e:
                        self.logger.exception(MSG['IntError'].format(str(e)))
                        raise cherrypy.HTTPError(500, ERR[500])
        return resp

    def lookup(self, params):
        self.logger.debug(f'Lookup for {params} called')

        if params.get('m'):
            try:
                params_list = re.split(r'\{(.*)\}', params['m'].strip())
                searchMetric = params_list[0]
                if searchMetric and str(
                   searchMetric).strip() not in self.TOPO.getAllEnabledMetricsNames:
                    self.logger.debug(MSG['LookupErr'].format(searchMetric))
                    return {}
                else:
                    filterBy = None
                    if len(params_list) > 1:
                        attr = params_list[1]
                        filterBy = dict(x.split('=') for x in attr.split(','))
                    identifiersMap = self.TOPO.getIdentifiersMapForQueryAttr(
                        'metric', searchMetric, filterBy)
                    res = LookupResponse(searchMetric)
                    res.parse_result_tags(identifiersMap)
                    res.parse_request_tags(filterBy)
                    resp = res.__dict__

            except Exception as e:
                self.logger.exception(MSG['IntError'].format(str(e)))
                raise cherrypy.HTTPError(500, MSG[500])

        return resp

    def _parse_input_query_filters(self, input_filters: dict) -> (dict, list):

        groupby = []
        filters = {}
        try:
            for f in input_filters:
                tagk = f.get('tagk')
                if tagk:
                    if f.get('groupBy'):
                        groupby.append(tagk)
                    if f.get('filter'):
                        filters[tagk] = f.get('filter')

        except ValueError as e:
            self.logger.error(MSG['QueryError'].format(str(e)))
            raise cherrypy.HTTPError(400, MSG['QueryError'].format(str(e)))

        return (filters, groupby)

    def _get_downsmpl_op(self, downsample):
        bstr = downsample
        if '-' in bstr:
            x = bstr.split('-')
            if x[1] in ['avg', 'sum', 'max', 'min']:
                return x[1]
        return None

    def _calc_bucket_size(self, downsample: str) -> int:
        bucketSize = 1  # default
        bstr = downsample

        if '-' in bstr:
            x = re.split(r'(\d+)', bstr[:bstr.find('-')])
            if len(x) == 3:  # if not 3, then split failed
                if x[1]:  # there is a time value
                    if x[1].isdigit():
                        timeMultiplier = -1
                        if x[2]:  # there is a unit
                            timeMultiplier = getTimeMultiplier(x[2])
                            if timeMultiplier == -1:
                                bucketSize = int(x[1])
                            else:
                                bucketSize = int(x[1]) * timeMultiplier
                        else:  # no units
                            bucketSize = int(x[1])
        return bucketSize

    @cherrypy.tools.json_out()  # @UndefinedVariable
    def GET(self, **params):
        """ Handle partial URLs such as /api/suggest?q=cpu_&type=metrics
            where type is one of metrics, tagk or tagv
            or
            Handle /api/search/lookup/m=cpu_idle{node=*} where m is the metric
            and optional term { tagk = tagv } qualifies the lookup.
            For more details please check openTSDB API documentation for
            /api/lookup
            /api/search/lookup
        """
        resp = []

        conn = cherrypy.request.headers.get('Host').split(':')
        if int(conn[1]) != int(self.port):
            raise cherrypy.HTTPError(400, MSG[400])

        # /api/suggest
        if 'suggest' in cherrypy.request.script_name:
            resp = self.suggest(params)

        # /api/search/lookup
        elif 'lookup' in cherrypy.request.script_name:
            resp = self.lookup(params)

        # /api/update
        elif 'update' in cherrypy.request.script_name:
            # cherrypy.response.headers['Content-Type'] = 'application/json'
            resp = self.md.update()
            # resp = json.dumps(resp)

        # /sensorsconfig
        elif '/sensorsconfig' == cherrypy.request.script_name:
            # cherrypy.response.headers['Content-Type'] = 'application/json'
            resp = self.md.SensorsConfig
            # resp = json.dumps(resp)

        elif 'aggregators' in cherrypy.request.script_name:
            resp = ["noop", "sum", "avg", "max", "min", "rate"]

        elif 'config/filters' in cherrypy.request.script_name:
            supportedFilters = {}
            filterDesc = {}
            filterDesc['description'] = '''Accepts an exact value or a regular expressions and
            matches against values for the given tag. The value can be omitted
            if the filter is used to specify groupBy on the tag only.'''
            filterDesc['examples'] = '''node=pm_filter(machine1), node=pm_filter(machine[1-6]),
            node=pm_filter(m1|m2), node=pm_filter(mac.*), node=pm_filter((?!^z).*)'''
            supportedFilters['pm_filter'] = filterDesc
            resp = supportedFilters

        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        # cherrypy.response.headers['Content-Type'] = 'application/json'
        # resp = json.dumps(resp)
        return resp

    @cherrypy.config(**{'tools.json_in.force': False})
    @cherrypy.tools.json_in()  # @UndefinedVariable
    @cherrypy.tools.json_out()  # @UndefinedVariable
    def POST(self):
        ''' Process POST. tools.json_in.force is set to False for
        compatability between versions of grafana < 3 and version 3.'''

        # /api/query
        if 'query' in cherrypy.request.script_name:

            # read query request parameters
            jreq = cherrypy.request.json
            if jreq.get('queries') is None:
                self.logger.error(MSG['QueryError'].format('empty'))
                raise cherrypy.HTTPError(400, MSG[400])

            return self.query(jreq)

    def OPTIONS(self):
        # print('options_post')
        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Methods'] = 'GET, POST, NEW, OPTIONS'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        cherrypy.response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Accept'
        cherrypy.response.headers['Access-Control-Max-Age'] = 604800


class LookupResponse():

    def __init__(self, metric):
        self.type = "LOOKUP"
        self.metric = metric
        self.tags = []
        self.results = []

    def parse_request_tags(self, filtersDict):
        if filtersDict:
            for key, value in filtersDict.items():
                tmp = {'key': key, 'value': value}
                self.tags.append(tmp)

    def parse_result_tags(self, identifiersMap):
        if identifiersMap:
            for identifiers in identifiersMap:
                d = defaultdict(dict)
                for key in identifiers.keys():
                    d['tags'][key] = identifiers[key]
                    if d not in self.results:
                        self.results.append(d)


class SingleTimeSeriesResponse():

    def __init__(self, inputQuery, dps, showQuery=False,
                 globalAnnotations=False, tags: dict = None,
                 aggrTags: list = None):
        self.metric = inputQuery.get('metric')
        self.dps = dps
        if showQuery:
            self.query = inputQuery
        if globalAnnotations:
            self.globalAnnotations = []
        self.tags = tags or defaultdict(list)
        self.aggregatedTags = aggrTags or []
