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
import json
import sys
import analytics
from functools import lru_cache
from messages import ERR, MSG
from collections import defaultdict, OrderedDict
from threading import Lock
from collector import SensorCollector, QueryPolicy
from utils import getTimeMultiplier, execution_time, cond_execution_time, get_request_host
from typing import List, TypeVar, Tuple, Optional, Union, Dict, Any

T = TypeVar('T', dict, list)


# ============================================================================
# Bundle ID Generation with Caching and Registry
# ============================================================================

# Bundle ID registry for debugging/logging (limited size, thread-safe)
_opentsdb_bundle_registry: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_registry_lock = Lock()
_MAX_REGISTRY_SIZE = 100  # Keep last 100 bundle_ids for debugging


def _normalize_query(query: dict) -> dict:
    """Extract and normalize query parameters for consistent hashing."""
    return {
        'metric': query.get('metric'),
        'aggregator': query.get('aggregator'),
        'tags': query.get('tags', {}),
        'filters': query.get('filters', []),
        'downsample': query.get('downsample'),
        'explicitTags': query.get('explicitTags', False),
        'isCounter': query.get('isCounter', False),
        'datasource_uid': query.get('datasource', {}).get('uid') if isinstance(query.get('datasource'), dict) else None
    }


def _queries_to_hashable(queries: List[dict]) -> Tuple[str, ...]:
    """Convert list of queries to a hashable tuple for caching."""
    normalized = []
    for q in queries:
        norm_query = _normalize_query(q)
        query_str = json.dumps(norm_query, sort_keys=True)
        normalized.append(query_str)
    return tuple(sorted(normalized))


@lru_cache(maxsize=1000)
def _generate_bundle_id_from_tuple(queries_tuple: Tuple[str, ...], host: str) -> str:
    """
    Cached function that generates bundle_id using Python's built-in hash.
    Args:
        queries_tuple: Tuple of JSON-serialized query strings
        host: Request host (without port)
    Returns:
        16-character hexadecimal bundle identifier
    """
    # Combine queries tuple and host for hashing
    combined = (queries_tuple, host)
    hash_value = hash(combined)
    return f"{abs(hash_value):016x}"


def generate_query_bundle_id_cached(jreq: dict) -> str:
    """
    Generate a deterministic, cached identifier for a bundle of queries.
    Includes host and datasource UID in the hash.
    Also stores the mapping in a registry for debugging/logging purposes.
    Args:
        jreq: Request dictionary containing 'queries' list
    Returns:
        16-character hexadecimal bundle identifier
    """
    queries = jreq.get('queries', [])
    if not queries:
        return '0000000000000000'

    # Get host from request headers
    host = get_request_host()

    # Convert queries to hashable tuple (includes datasource.uid)
    queries_tuple = _queries_to_hashable(queries)

    # Generate bundle ID with host included
    bundle_id = _generate_bundle_id_from_tuple(queries_tuple, host)

    # Store in registry for debugging (thread-safe, size-limited)
    _register_bundle_id(bundle_id, queries, host, jreq)

    return bundle_id


def get_bundle_id_cache_info():
    """Get cache statistics for monitoring."""
    return _generate_bundle_id_from_tuple.cache_info()


def clear_bundle_id_cache():
    """Clear the bundle ID cache."""
    _generate_bundle_id_from_tuple.cache_clear()


def _register_bundle_id(bundle_id: str, queries: List[dict], host: str, jreq: dict) -> None:
    """
    Register a bundle_id with its query information for debugging/logging.
    Maintains a size-limited registry using LRU eviction.
    Args:
        bundle_id: The generated bundle identifier
        queries: List of query dictionaries
        host: Request host
        jreq: Full request dictionary used to extract start and end values
    """
    with _registry_lock:
        # If bundle_id already exists, move it to end (most recent)
        if bundle_id in _opentsdb_bundle_registry:
            _opentsdb_bundle_registry.move_to_end(bundle_id)
        else:
            # Add new entry
            _opentsdb_bundle_registry[bundle_id] = {
                'queries': queries,
                'host': host,
                'start': jreq.get('start'),
                'end': jreq.get('end')
            }

            # Evict oldest entry if size limit exceeded
            if len(_opentsdb_bundle_registry) > _MAX_REGISTRY_SIZE:
                _opentsdb_bundle_registry.popitem(last=False)


def get_bundle_info(bundle_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve query information for a given bundle_id (for debugging/logging).
    Args:
        bundle_id: The bundle identifier to look up
    Returns:
        Dictionary containing query information, or None if not found
    Example:
        >>> info = get_bundle_info('a3f5c8d9e2b1f4a7')
        >>> if info:
        ...     print(f"Host: {info['host']}")
        ...     print(f"Queries: {info['queries']}")
    """
    with _registry_lock:
        return _opentsdb_bundle_registry.get(bundle_id)


def get_all_bundle_ids() -> Dict[str, Dict[str, Any]]:
    """
    Get all registered bundle_ids with their query information (for debugging).
    Returns:
        Dictionary mapping bundle_ids to their query information
    Example:
        >>> all_bundles = get_all_bundle_ids()
        >>> for bundle_id, info in all_bundles.items():
        ...     print(f"{bundle_id}: {len(info['queries'])} queries")
    """
    with _registry_lock:
        return dict(_opentsdb_bundle_registry)


def clear_bundle_registry():
    """Clear the bundle ID registry (for debugging/testing)."""
    with _registry_lock:
        _opentsdb_bundle_registry.clear()


def get_bundle_registry_stats() -> Dict[str, Any]:
    """
    Get statistics about the bundle ID registry.
    Returns:
        Dictionary with registry statistics
    """
    with _registry_lock:
        memory_size = sys.getsizeof(_opentsdb_bundle_registry) + sum(
            sys.getsizeof(bundle_id) + sys.getsizeof(bundle_info)
            for bundle_id, bundle_info in _opentsdb_bundle_registry.items()
        )
        return {
            'size': len(_opentsdb_bundle_registry),
            'max_size': _MAX_REGISTRY_SIZE,
            'memory_size': memory_size,
            'bundle_ids': list(_opentsdb_bundle_registry.keys())
        }


class OpenTsdbApi(object):
    exposed = True

    def __init__(self, logger, mdHandler, port):
        self.logger = logger
        self.__md = mdHandler
        self.port = port
        self.internal_metrics: defaultdict[int, dict[str, Union[int, float]]] = defaultdict(dict)

    @property
    def md(self):
        return self.__md

    @property
    def qh(self):
        return self.__md.qh

    @property
    def TOPO(self):
        return self.__md.metaData

    @cond_execution_time(detail_level=1)
    def format_response(self, data: dict, jreq: dict) -> List[dict]:
        respList = []
        metrics = set(data.values())
        if jreq.get('start') == 'last':
            for metric in metrics:
                for st in metric.timeseries:
                    timestmp = ''
                    val = 'null'
                    if len(st.dps) > 0:
                        timestmp = list(st.dps.keys())[0]
                        val = st.dps[timestmp]
                    res = LastSingleTimeSeriesResponse(jreq.get('inputQuery'),
                                                       timestmp,
                                                       val,
                                                       st.tags)
                    respList.append(res.to_dict())
        else:
            for metric in metrics:
                for st in metric.timeseries:
                    res = SingleTimeSeriesResponse(jreq.get('inputQuery'),
                                                   jreq.get('showQuery'),
                                                   jreq.get('globalAnnotations'),
                                                   st.tags, st.aggregatedTags)
                    # self.logger.trace(f'OpenTSDB queryResponse for :
                    #                   {data.keys()[0]} with {len(st.dps)} datapoints')
                    respList.append(res.to_dict(st.dps))
        return respList

    @execution_time()
    def query(self, jreq: dict, bundle_id: Optional[str] = None) -> List[dict]:

        import threading
        current = threading.current_thread()

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
            request_data['bundle_id'] = bundle_id

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
            if analytics.http_metrics_enabled:
                try:
                    from stats import get_metrics_collector

                    # Get metrics from query handler
                    metrics = collector.md.qh.internal_metrics.pop(collector.thread.ident)

                    # Collect metrics from both thread identifiers efficiently
                    keys_to_remove = [collector.thread.ident, current.ident]
                    col_metrics = {}
                    for key in keys_to_remove:
                        if key in collector.internal_metrics:
                            col_metrics.update(collector.internal_metrics.pop(key))

                    # Merge all metrics
                    metrics.update(col_metrics)

                    # Build labels dict
                    labels = {
                        "bundle_id": bundle_id,
                        "collector_name": collector.thread.name
                    }

                    if collector.request.filters:
                        labels.update(collector.request.filters)

                    self.logger.trace(
                        MSG['CollectorThreadTrace'],
                        metrics,
                        labels,
                        bundle_id,
                    )

                    stats_collector = get_metrics_collector()
                    stats_collector.record_metric(labels=labels, metrics=metrics)
                except Exception as exc:
                    self.logger.debug(MSG['HttpMetricsRecordFailed'].format(exc))
            # cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
            resp.extend(coll_resp)
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        return resp

    @cond_execution_time(detail_level=1)
    def build_collector(self, jreq: dict) -> SensorCollector:

        q = jreq.get('inputQuery')
        bundle_id = jreq.get('bundle_id', None)

        sensor = self.TOPO.getSensorForMetric(q.get('metric'))
        period = self.md.getSensorPeriod(sensor)
        if period < 1:
            self.logger.error(MSG['SensorDisabled'].format(q.get('metric')))
            raise cherrypy.HTTPError(
                400, MSG['SensorDisabled'].format(q.get('metric')))

        args = {}
        args['metricsaggr'] = {q.get('metric'): q.get('aggregator')}

        if jreq.get('start') == 'last':
            args['nsamples'] = 1
            if q.get('tags'):
                args['filters'] = q.get('tags')
        else:
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

        if 'arrays' in jreq:
            args['dpsArrays'] = jreq['arrays']

        args['rawData'] = q.get('explicitTags', False) or q.get('isCounter', False)

        args['sensor'] = sensor
        args['period'] = period

        request = QueryPolicy(**args)
        self.logger.trace(f'request instance {str(request.__dict__)}')

        collector = SensorCollector(sensor, period, self.logger, request, bundle_id=bundle_id)
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

        self.logger.trace(f"Request headers:{str(cherrypy.request.headers)}")
        conn = cherrypy.request.headers.get('Host').split(':')
        if len(conn) == 2 and int(conn[1]) != int(self.port):
            self.logger.error(MSG['EndpointNotSupportedForPort'].
                              format(cherrypy.request.script_name, str(conn[1])))
            raise cherrypy.HTTPError(400, ERR[400])

        # /api/suggest
        if 'suggest' in cherrypy.request.script_name:
            resp = self.suggest(params)

        # /api/search/lookup
        elif 'lookup' in cherrypy.request.script_name:
            resp = self.lookup(params)

        # /api/query/last
        elif '/api/query/last' == cherrypy.request.script_name:
            jreq = {}

            if params.get('timeseries') is None:
                self.logger.error(MSG['QueryError'].format('empty'))
                raise cherrypy.HTTPError(400, ERR[400])

            queries = []
            timeseries = params.get('timeseries')
            if not isinstance(timeseries, list):
                timeseries = [timeseries]
            for timeserie in timeseries:
                try:
                    metricDict = {}
                    params_list = re.split(r'\{(.*)\}', timeserie.strip())
                    if len(params_list[0]) == 0:
                        break
                    metricDict['metric'] = params_list[0]

                    if len(params_list) > 1:
                        attr = params_list[1]
                        filterBy = dict(x.split('=') for x in attr.split(','))
                        metricDict['tags'] = filterBy
                    queries.append(metricDict)

                except Exception as e:
                    self.logger.exception(MSG['IntError'].format(str(e)))
                    raise cherrypy.HTTPError(500, MSG[500])
            if len(queries) == 0:
                raise cherrypy.HTTPError(400, ERR[400])
            jreq['start'] = 'last'
            jreq['queries'] = queries

            # Generate bundle_id only if metrics are enabled
            bundle_id = None
            if analytics.http_metrics_enabled:
                bundle_id = generate_query_bundle_id_cached(jreq)
                self.logger.trace(MSG['BundleIdGenerated'].format(cherrypy.request.script_name, bundle_id))

            resp = self.query(jreq, bundle_id=bundle_id)

        # /api/bundle_ids - List all registered bundle IDs (only if http_metrics_enabled)
        elif '/api/bundle_ids' == cherrypy.request.script_name:
            if not analytics.http_metrics_enabled:
                self.logger.error('Bundle ID endpoint requires http_metrics_enabled=True')
                raise cherrypy.HTTPError(503, MSG['BundleIdTrackingDisabled'])
            if params.get('bundle_id'):
                # Get specific bundle ID info
                bundle_id = params.get('bundle_id')
                info = get_bundle_info(bundle_id)
                if info:
                    resp = {
                        'bundle_id': bundle_id,
                        'found': True,
                        'info': info
                    }
                else:
                    resp = {
                        'bundle_id': bundle_id,
                        'found': False,
                        'message': 'Bundle ID not found in registry'
                    }
            else:
                # List all bundle IDs with stats
                all_bundles = get_all_bundle_ids()
                stats = get_bundle_registry_stats()
                resp = {
                    'registry_type': 'opentsdb',
                    'stats': stats,
                    'bundles': all_bundles
                }

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

        else:
            self.logger.error(MSG['EndpointNotSupported'].
                              format(cherrypy.request.script_name))
            raise cherrypy.HTTPError(400, ERR[400])

        del cherrypy.response.headers['Allow']
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        # cherrypy.response.headers['Content-Type'] = 'application/json'
        # resp = json.dumps(resp)
        return resp

    @cherrypy.config(**{'tools.json_in.force': False})
    @cherrypy.tools.json_in()  # @UndefinedVariable
    @cherrypy.tools.json_out()  # @UndefinedVariable
    def POST(self, **params):
        ''' Process POST. tools.json_in.force is set to False for
        compatability between versions of grafana < 3 and version 3.'''

        self.logger.trace(f"Request headers:{str(cherrypy.request.headers)}")
        conn = cherrypy.request.headers.get('Host').split(':')
        if len(conn) == 2 and int(conn[1]) != int(self.port):
            self.logger.error(MSG['EndpointNotSupportedForPort'].
                              format(cherrypy.request.script_name, str(conn[1])))
            raise cherrypy.HTTPError(400, ERR[400])

        # /api/query
        if '/api/query' == cherrypy.request.script_name:

            # read query request parameters
            jreq = cherrypy.request.json
            if jreq.get('queries') is None:
                self.logger.error(MSG['QueryError'].format('empty'))
                raise cherrypy.HTTPError(400, ERR[400])

            if params and params.get('arrays') == 'true':
                jreq['arrays'] = True

            # Generate bundle_id only if metrics are enabled
            bundle_id = None
            if analytics.http_metrics_enabled:
                bundle_id = generate_query_bundle_id_cached(jreq)
                self.logger.trace(MSG['BundleIdGenerated'].format(cherrypy.request.script_name, bundle_id))

            resp = self.query(jreq, bundle_id=bundle_id)

            if analytics.http_metrics_enabled:
                try:
                    import threading
                    current = threading.current_thread()
                    if current.ident in self.internal_metrics:
                        metrics = self.internal_metrics.pop(current.ident)
                        metric_name = jreq['queries'][0].get('metric') if len(jreq['queries']) == 1 else "multiple_metrics"

                        # Build labels dict in one operation instead of multiple updates
                        labels = {
                            "bundle_id": bundle_id,
                            "collector_name": metric_name,
                            **params  # Unpack params directly
                        }

                        from stats import get_metrics_collector
                        stats_collector = get_metrics_collector()
                        stats_collector.record_metric(labels=labels, metrics=metrics)
                except Exception as exc:
                    self.logger.debug(MSG['HttpMetricsRecordFailed'].format(exc))
            return resp

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
                d['tags'] = identifiers
                self.results.append(d)


class SingleTimeSeriesResponse(object):

    def __init__(self, inputQuery, showQuery=False,
                 globalAnnotations=False, tags: dict = None,
                 aggrTags: list = None):
        self.metric = inputQuery.get('metric')
        self.dps = defaultdict()
        if showQuery:
            self.query = inputQuery
        if globalAnnotations:
            self.globalAnnotations = []
        self.tags = tags or defaultdict(list)
        self.aggregatedTags = aggrTags or []

    def to_dict(self, dps: T = None):
        ''' Converts the SingleTimeSeriesResponse object to dict. '''
        res = self.__dict__
        # Since a single Timeseries might have a huge number of datapoints (dps),
        # first convert object to dict and then fetch the dict of dps to it
        if dps:
            res['dps'] = dps
        elif isinstance(dps, list):
            res['dps'] = []
        return res


class LastSingleTimeSeriesResponse(object):

    def __init__(self, inputQuery, timestmp, value, tags: dict = None):
        self.metric = inputQuery.get('metric')
        self.timestamp = timestmp
        self.value = value
        self.tags = tags or defaultdict(list)

    def to_dict(self):
        ''' Converts the LastSingleTimeSeriesResponse object to dict. '''
        res = self.__dict__
        return res
