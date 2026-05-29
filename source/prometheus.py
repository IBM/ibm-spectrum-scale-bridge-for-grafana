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
import sys
import analytics
from functools import lru_cache
from messages import ERR, MSG
from typing import Optional, Union, Dict, Any
from collections import OrderedDict, defaultdict
from threading import Lock
from cherrypy.process.plugins import Monitor
from collector import SensorCollector, QueryPolicy
from utils import execution_time, cond_execution_time, get_request_host


# ============================================================================
# Bundle ID Generation with Caching and Registry (for Prometheus)
# ============================================================================

# Bundle ID registry for debugging/logging (limited size, thread-safe)
_prometheus_bundle_registry: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_prometheus_registry_lock = Lock()
_PROMETHEUS_MAX_REGISTRY_SIZE = 100  # Keep last 100 bundle_ids for debugging


def _normalize_prometheus_request(sensors: list, filters: Optional[dict] = None) -> dict:
    """Extract and normalize Prometheus request parameters for consistent hashing."""
    return {
        'sensors': sorted(sensors) if sensors else [],
        'filters': filters if filters else {}
    }


def _prometheus_request_to_hashable(sensors: list, filters: Optional[dict] = None) -> str:
    """Convert Prometheus request to a hashable string for caching."""
    norm_request = _normalize_prometheus_request(sensors, filters)
    return json.dumps(norm_request, sort_keys=True)


@lru_cache(maxsize=1000)
def _generate_prometheus_bundle_id_from_tuple(request_str: str, host: str) -> str:
    """
    Cached function that generates bundle_id using Python's built-in hash.
    Args:
        request_str: JSON-serialized request string
        host: Request host (without port)
    Returns:
        16-character hexadecimal bundle identifier
    """
    # Combine request and host for hashing
    combined = (request_str, host)
    hash_value = hash(combined)
    return f"{abs(hash_value):016x}"


def generate_prometheus_bundle_id_cached(sensors: list, filters: Optional[dict] = None) -> str:
    """
    Generate a deterministic, cached identifier for a Prometheus request.
    Includes host and sensor/filter information in the hash.
    Also stores the mapping in a registry for debugging/logging purposes.
    Args:
        sensors: List of sensor names
        filters: Optional dictionary of filters
    Returns:
        16-character hexadecimal bundle identifier
    """
    if not sensors:
        return '0000000000000000'

    # Get host from request headers
    host = get_request_host()

    # Convert request to hashable string
    request_str = _prometheus_request_to_hashable(sensors, filters)

    # Generate bundle ID with host included
    bundle_id = _generate_prometheus_bundle_id_from_tuple(request_str, host)

    # Store in registry for debugging (thread-safe, size-limited)
    _register_prometheus_bundle_id(bundle_id, sensors, filters, host)

    return bundle_id


def get_prometheus_bundle_id_cache_info():
    """Get cache statistics for monitoring."""
    return _generate_prometheus_bundle_id_from_tuple.cache_info()


def clear_prometheus_bundle_id_cache():
    """Clear the bundle ID cache."""
    _generate_prometheus_bundle_id_from_tuple.cache_clear()


def _register_prometheus_bundle_id(bundle_id: str, sensors: list, filters: Optional[dict], host: str) -> None:
    """
    Register a Prometheus bundle_id with its request information for debugging/logging.
    Maintains a size-limited registry using LRU eviction.
    Args:
        bundle_id: The generated bundle identifier
        sensors: List of sensor names
        filters: Optional dictionary of filters
        host: Request host
    """
    with _prometheus_registry_lock:
        # If bundle_id already exists, move it to end (most recent)
        if bundle_id in _prometheus_bundle_registry:
            _prometheus_bundle_registry.move_to_end(bundle_id)
        else:
            # Add new entry
            _prometheus_bundle_registry[bundle_id] = {
                'sensors': sensors,
                'filters': filters if filters else {},
                'host': host
            }

            # Evict oldest entry if size limit exceeded
            if len(_prometheus_bundle_registry) > _PROMETHEUS_MAX_REGISTRY_SIZE:
                _prometheus_bundle_registry.popitem(last=False)


def get_prometheus_bundle_info(bundle_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve request information for a given Prometheus bundle_id (for debugging/logging).
    Args:
        bundle_id: The bundle identifier to look up
    Returns:
        Dictionary containing request information, or None if not found
    Example:
        >>> info = get_prometheus_bundle_info('x9y8z7w6v5u4t3s2')
        >>> if info:
        ...     print(f"Host: {info['host']}")
        ...     print(f"Sensors: {info['sensors']}")
        ...     print(f"Filters: {info['filters']}")
    """
    with _prometheus_registry_lock:
        return _prometheus_bundle_registry.get(bundle_id)


def get_all_prometheus_bundle_ids() -> Dict[str, Dict[str, Any]]:
    """
    Get all registered Prometheus bundle_ids with their request information (for debugging).
    Returns:
        Dictionary mapping bundle_ids to their request information
    Example:
        >>> all_bundles = get_all_prometheus_bundle_ids()
        >>> for bundle_id, info in all_bundles.items():
        ...     print(f"{bundle_id}: {len(info['sensors'])} sensors")
    """
    with _prometheus_registry_lock:
        return dict(_prometheus_bundle_registry)


def clear_prometheus_bundle_registry():
    """Clear the Prometheus bundle ID registry (for debugging/testing)."""
    with _prometheus_registry_lock:
        _prometheus_bundle_registry.clear()


def get_prometheus_bundle_registry_stats() -> Dict[str, Any]:
    """
    Get statistics about the Prometheus bundle ID registry.
    Returns:
        Dictionary with registry statistics
    """
    with _prometheus_registry_lock:
        memory_size = sys.getsizeof(_prometheus_bundle_registry) + sum(
            sys.getsizeof(bundle_id) + sys.getsizeof(bundle_info)
            for bundle_id, bundle_info in _prometheus_bundle_registry.items()
        )
        return {
            'size': len(_prometheus_bundle_registry),
            'max_size': _PROMETHEUS_MAX_REGISTRY_SIZE,
            'memory_size': memory_size,
            'bundle_ids': list(_prometheus_bundle_registry.keys())
        }


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
        self.internal_metrics: defaultdict[int, dict[str, Union[int, float]]] = defaultdict(dict)
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

    @cond_execution_time(detail_level=1)
    def format_response(self, data) -> [str]:
        resp = []
        for name, metric in data.items():
            header = metric.str_descfmt()
            resp.extend(header)
            for sts in metric.timeseries:
                if len(sts.dps) == 0:
                    self.logger.warning(MSG['NoDps'].format(name, '|'.join(self.tags.values())))
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
        return resp

    @execution_time()
    def metrics(self, export_sensors: Optional[list] = None, filters: Optional[dict] = None, bundle_id: Optional[str] = None):
        export_sensors = export_sensors or []
        resp = []

        if self.cache_strategy and self.caching_collectors:
            for collector in self.caching_collectors:
                respList = self.format_response(collector.cached_metrics)
                resp.extend(respList)
        elif len(export_sensors) > 0:
            resp = self._metrics(export_sensors, filters, bundle_id)
        else:
            resp = self._metrics(self.static_sensors_list, None, bundle_id)

        return resp

    def _metrics(self, export_sensors: list, filters: Optional[dict] = None, bundle_id: Optional[str] = None):
        resp = []
        collectors = []

        import threading
        current = threading.current_thread()

        for sensor in export_sensors:
            collector = self.build_collector(sensor, filters, bundle_id=bundle_id)
            collectors.append(collector)

        for collector in collectors:
            collector.start_collect()

        for collector in collectors:
            collector.thread.join()

        for collector in collectors:
            self.logger.trace('Finished custom thread %r.' % collector.thread.name)
            respList = self.format_response(collector.metrics)
            if len(respList) <= len(collector.metrics) * 2:
                self.logger.warning(MSG['AllDpsNullForSensor'].format(collector.sensor))
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
                    # Build labels dict in one operation instead of multiple updates
                    labels = {
                        "bundle_id": bundle_id,
                        "collector_name": collector.sensor
                    }
                    # Add filters if provided
                    if filters:
                        labels.update(filters)
                    self.logger.trace(
                        MSG['CollectorThreadTrace'],
                        metrics,
                        labels,
                        bundle_id,
                    )
                    # Record metrics
                    stats_collector = get_metrics_collector()
                    stats_collector.record_metric(labels=labels, metrics=metrics)
                except Exception as exc:
                    self.logger.debug(MSG['HttpMetricsRecordFailed'].format(exc))
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

    @cond_execution_time(detail_level=1)
    def build_collector(self, sensor: str, filters: Optional[dict] = None, bundle_id: Optional[str] = None) -> SensorCollector:

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
        collector = SensorCollector(sensor, period, self.logger, request, bundle_id=bundle_id)
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

            # Generate bundle_id only if http metrics are enabled
            bundle_id = None
            if analytics.http_metrics_enabled:
                bundle_id = generate_prometheus_bundle_id_cached([sensor], params)
                self.logger.trace(MSG['BundleIdGenerated'].format(cherrypy.request.script_name, bundle_id))

            resp = self.metrics([sensor], params, bundle_id=bundle_id)
            cherrypy.response.headers['Content-Type'] = 'text/plain'
            resString = '\n'.join(resp) + '\n'
            if analytics.http_metrics_enabled:
                try:
                    from stats import get_metrics_collector
                    import threading
                    current = threading.current_thread()
                    if current.ident in self.internal_metrics:
                        metrics = self.internal_metrics.pop(current.ident)
                        # Build labels dict in one operation instead of multiple updates
                        labels = {
                            "bundle_id": bundle_id,
                            "collector_name": sensor,
                            **params  # Unpack params directly
                        }
                        stats_collector = get_metrics_collector()
                        stats_collector.record_metric(labels=labels, metrics=metrics)
                except Exception as exc:
                    self.logger.debug(MSG['HttpMetricsRecordFailed'].format(exc))
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

        # /bundle_ids - List all registered Prometheus bundle IDs (only if http_metrics_enabled)
        elif '/bundle_ids' == cherrypy.request.script_name:
            if not analytics.http_metrics_enabled:
                self.logger.error(MSG['BundleIdTrackingDisabled'])
                raise cherrypy.HTTPError(503, MSG['BundleIdTrackingDisabled'])

            if params.get('bundle_id'):
                # Get specific bundle ID info
                bundle_id = params.get('bundle_id')
                info = get_prometheus_bundle_info(bundle_id)
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
                        'message': MSG['BundleIdNotFound']
                    }
            else:
                # List all bundle IDs with stats
                all_bundles = get_all_prometheus_bundle_ids()
                stats = get_prometheus_bundle_registry_stats()
                resp = {
                    'registry_type': 'prometheus',
                    'stats': stats,
                    'bundles': all_bundles
                }
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
