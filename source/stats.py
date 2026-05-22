'''
##############################################################################
# Copyright 2026 IBM Corp.
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

Created on Apr 17, 2026

@author: hwassman
'''

import time
import copy
import cherrypy
import json
import sys
from collections import defaultdict, deque
from threading import Lock, Timer
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class HTTPRequestMetric:
    """Data class for storing HTTP request metrics"""
    timestamp: float
    labels: Dict[str, Any]
    metrics: Dict[str, Any]

    def convert_bundle_to_metrics_timeseries(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convert bundle metrics to time series format.
        Returns:
            Dictionary mapping metric names to lists of time series data points
        """
        sorted_metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # deep copy labels
        labels = self.labels.copy()
        timestamp = self.timestamp

        for key, value in self.metrics.items():
            # Create dict in one operation instead of multiple updates
            timeserie = {
                "labels": labels,
                "value": value,
                "timestamp": timestamp
            }
            sorted_metrics[key].append(timeserie)

        # Return defaultdict directly - no need to convert to regular dict
        return sorted_metrics


class HTTPMetricsCollector:
    """
    Collects and stores HTTP request/response metrics for monitoring.
    Thread-safe implementation with configurable retention and automatic cleanup.
    Features:
    - Thread-safe metric collection using locks
    - Configurable maximum history size
    - Automatic cleanup of old metrics via periodic background task
    - Prometheus exposition format support
    The collector automatically removes metrics older than retention_seconds
    by running a background cleanup task at regular intervals (cleanup_interval).
    """

    def __init__(self, max_history: int = 1000, retention_seconds: int = 3600, cleanup_interval: int = 300):
        """
        Initialize the metrics collector.
        Args:
            max_history: Maximum number of metrics to keep in memory
            retention_seconds: How long to keep metrics (in seconds)
            cleanup_interval: How often to run cleanup (in seconds, default: 300 = 5 minutes)
        """
        self.max_history = max_history
        self.retention_seconds = retention_seconds
        self.cleanup_interval = cleanup_interval
        self.metrics: deque = deque(maxlen=max_history)
        self.lock = Lock()

        # Aggregated statistics
        self.stats = {'total_requests': 0}

        # Cleanup timer
        self._cleanup_timer: Optional[Timer] = None
        self._cleanup_running = False

    def record_metric(self, labels: dict, metrics: dict):
        """
        Record a new HTTP request metric.
        Args:
            endpoint: The API endpoint path
            method: HTTP method (GET, POST, etc.)
            status_code: HTTP status code
            request_size: Request body size in bytes
            response_size: Response body size in bytes
            duration: Request duration in seconds
            remote_addr: Remote client address
        """
        metric = HTTPRequestMetric(
            timestamp=time.time(),
            labels=labels,
            metrics=metrics
        )

        with self.lock:
            self.metrics.append(metric)

            # Update aggregated statistics
            self.stats['total_requests'] += 1

    def cleanup_old_metrics(self):
        """Remove metrics older than retention_seconds"""
        cutoff_time = time.time() - self.retention_seconds
        with self.lock:
            while self.metrics and self.metrics[0].timestamp < cutoff_time:
                self.metrics.popleft()

    def start_periodic_cleanup(self):
        """Start periodic cleanup using threading.Timer"""
        if self._cleanup_running:
            return
        self._cleanup_running = True
        self._schedule_cleanup()

    def _schedule_cleanup(self):
        """Internal method to schedule the next cleanup"""
        if not self._cleanup_running:
            return
        try:
            self.cleanup_old_metrics()
        except Exception as e:
            # Log error but continue scheduling
            print(f"Error during metrics cleanup: {e}", file=sys.stderr)
        # Schedule next cleanup
        self._cleanup_timer = Timer(self.cleanup_interval, self._schedule_cleanup)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()

    def stop_periodic_cleanup(self):
        """Stop periodic cleanup"""
        self._cleanup_running = False
        if self._cleanup_timer:
            self._cleanup_timer.cancel()
            self._cleanup_timer = None

    def get_recent_metrics(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get recent metrics as a list of dictionaries.
        Args:
            limit: Maximum number of metrics to return (None for all)
        Returns:
            List of metric dictionaries
        """
        with self.lock:
            metrics_list = list(self.metrics)
            if limit:
                metrics_list = metrics_list[-limit:]
            return metrics_list

    def get_metrics_last_5_minutes(self) -> List['HTTPRequestMetric']:
        """
        Get metrics from the last 5 minutes.
        This method leverages the fact that metrics are stored in chronological order
        (oldest first) in the deque, allowing for efficient filtering.
        Returns:
            List of HTTPRequestMetric objects with timestamps from the last 5 minutes
        """
        cutoff_time = time.time() - 300  # 300 seconds = 5 minutes
        # print(f"cutoff_time: {cutoff_time}")
        # print(f"cutoff_time int: {(int(time.time()) * 1000) - 300}")

        with self.lock:
            # Since deque is ordered by timestamp (oldest first), we can find the first
            # metric that's within our time window and slice from there
            metrics_list = list(self.metrics)

            # Binary search for the first metric >= cutoff_time
            left, right = 0, len(metrics_list)
            while left < right:
                mid = (left + right) // 2
                if metrics_list[mid].timestamp < cutoff_time:
                    left = mid + 1
                else:
                    right = mid

            # Extract only the metrics dict from matching HTTPRequestMetric objects
            return metrics_list[left:]

    def get_statistics(self) -> Dict:
        """
        Get aggregated statistics.
        Returns:
            Dictionary containing aggregated statistics
        """
        with self.lock:
            memory_size = sys.getsizeof(self.metrics) + sum(sys.getsizeof(obj) for obj in self.metrics)
            stats_copy = {
                'total_requests': self.stats['total_requests'],
                # 'total_request_bytes': self.stats['total_request_bytes'],
                # 'total_response_bytes': self.stats['total_response_bytes'],
                # 'total_transfer_bytes': self.stats['total_request_bytes'] + self.stats['total_response_bytes'],
                # 'by_endpoint': dict(self.stats['by_endpoint']),
                # 'by_status': dict(self.stats['by_status']),
                'metrics_in_memory_count': len(self.metrics),
                'metrics_in_memory_size': memory_size
            }

        try:
            from opentsdb import get_bundle_registry_stats
            from prometheus import get_prometheus_bundle_registry_stats

            opentsdb_stats = get_bundle_registry_stats()
            prometheus_stats = get_prometheus_bundle_registry_stats()

            opentsdb_count = opentsdb_stats.get('size', 0)
            prometheus_count = prometheus_stats.get('size', 0)
            opentsdb_memory_size = opentsdb_stats.get('memory_size', 0)
            prometheus_memory_size = prometheus_stats.get('memory_size', 0)

            stats_copy.update({
                'opentsdb_bundle_ids_count': opentsdb_count,
                'prometheus_bundle_ids_count': prometheus_count,
                'bundle_ids_count_total': opentsdb_count + prometheus_count,
                'opentsdb_bundle_registry_memory_size': opentsdb_memory_size,
                'prometheus_bundle_registry_memory_size': prometheus_memory_size,
                'bundle_registry_memory_size_total': opentsdb_memory_size + prometheus_memory_size,
            })
        except Exception:
            pass

        return stats_copy

    def get_prometheus_metrics(self, metric_prefix='grafana_bridge') -> List[str]:
        """
        Generate Prometheus exposition format metrics from the last 5 minutes.
        Args:
            metric_prefix: Prefix for metric names (currently unused)
        Returns:
            List of formatted metric lines in Prometheus exposition format
        """
        metrics = self.get_metrics_last_5_minutes()
        # Use defaultdict to avoid setdefault calls
        merged: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for metric in metrics:
            bundle_timeseries = metric.convert_bundle_to_metrics_timeseries()
            for key, value in bundle_timeseries.items():
                merged[key].extend(value)

        # Build output lines
        lines = []
        lines_append = lines.append  # Cache method reference for performance

        for key, value in merged.items():
            actor, method = key.split("_", 1)
            if not any(sub in key for sub in ("size", "amount", "bytes", "content")):
                description = f'time in seconds how long {actor} took to complete {method}'
            else:
                description = f'bytes received by {actor} though {method} completion'

            lines_append(f'# HELP {key} {description}')
            lines_append(f'# TYPE {key} gauge')

            # Inline metric_exprfmt for better performance
            for timeserie in value:
                labels_dict = timeserie.get("labels")
                if labels_dict:
                    labels = ','.join(f'{k}="{v}"' for k, v in labels_dict.items())
                    fmtstr = f"{key}{{{labels}}} {timeserie['value']} {int(timeserie['timestamp']) * 1000}"
                else:
                    fmtstr = f"{key} {timeserie['value']} {int(timeserie['timestamp']) * 1000}"
                lines_append(fmtstr)

        return lines

    def get_csv_metrics(self, limit: Optional[int] = None) -> str:
        """
        Generate CSV format metrics with flexible headers.
        Args:
            limit: Maximum number of metrics to include (None for all available metrics)
                   Default is None to export all metrics in memory (up to max_history)
        Returns:
            String containing CSV formatted metrics with header
        Performance Note:
            With default max_history=1000, processing all metrics typically takes < 100ms.
            Use limit parameter to reduce processing time for very large datasets.
        """
        import csv
        from io import StringIO

        # Get all recent metrics or limited subset
        metrics = self.get_recent_metrics(limit=limit)

        # Collect all unique label keys across all metrics
        all_label_keys = set()
        rows_data = []

        for metric in metrics:
            bundle_timeseries = metric.convert_bundle_to_metrics_timeseries()
            for metric_name, timeseries_list in bundle_timeseries.items():
                for timeserie in timeseries_list:
                    labels_dict = timeserie.get("labels", {})
                    all_label_keys.update(labels_dict.keys())

                    # Store row data for later processing
                    rows_data.append({
                        'timestamp': timeserie['timestamp'],
                        'metric_name': metric_name,
                        'labels': labels_dict,
                        'value': timeserie['value']
                    })

        # Sort label keys for consistent column ordering
        sorted_label_keys = sorted(all_label_keys)

        # Build CSV header
        header = ['timestamp', 'metric_name'] + sorted_label_keys + ['value']

        # Generate CSV content
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(header)

        # Write data rows
        for row_data in rows_data:
            row = [
                datetime.fromtimestamp(row_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                row_data['metric_name']
            ]

            # Add label values in the same order as header
            for label_key in sorted_label_keys:
                row.append(row_data['labels'].get(label_key, ''))

            # Add metric value
            row.append(row_data['value'])
            writer.writerow(row)

        return output.getvalue()

    def get_opentsdb_metrics(self, limit: Optional[int] = None,
                            aggregated_tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Generate OpenTSDB format metrics.
        The response format follows the OpenTSDB specification at:
        https://opentsdb.net/docs/build/html/api_http/query/index.html
        Args:
            limit: Maximum number of metrics to include (None for all available metrics)
            aggregated_tags: Optional list of tag names that were aggregated over
        Returns:
            List of dictionaries, each representing a time series in OpenTSDB format:
            [
                {
                    "metric": "<metric_name>",
                    "tags": {<label_key>: <label_value>, ...},
                    "aggregatedTags": [<tag_name>, ...],
                    "dps": {<timestamp_ms>: <value>, ...}
                },
                ...
            ]
            
        Example:
            >>> collector.record_metric(
            ...     labels={"bundle_id": "abc123", "collector_name": "test"},
            ...     metrics={"request_count": 100, "response_time_ms": 250}
            ... )
            >>> response = collector.get_opentsdb_metrics()
            >>> print(response)
            [
                {
                    "metric": "request_count",
                    "tags": {"bundle_id": "abc123", "collector_name": "test"},
                    "aggregatedTags": [],
                    "dps": {"1609459200000": 100}
                },
                {
                    "metric": "response_time_ms",
                    "tags": {"bundle_id": "abc123", "collector_name": "test"},
                    "aggregatedTags": [],
                    "dps": {"1609459200000": 250}
                }
            ]
        """
        metrics_list = self.get_recent_metrics(limit=limit)
        # Dictionary to group time series by (metric_name, labels_tuple)
        timeseries_map: Dict[tuple, Dict[str, Any]] = {}
        for http_metric in metrics_list:
            timestamp_ms = str(int(http_metric.timestamp * 1000))

            # Create a hashable key from labels for grouping
            labels_key = frozenset(http_metric.labels.items())

            # Process each metric in the HTTPRequestMetric
            for metric_name, metric_value in http_metric.metrics.items():
                # Create unique key for this time series
                ts_key = (metric_name, labels_key)
                # Initialize time series entry if not exists
                if ts_key not in timeseries_map:
                    timeseries_map[ts_key] = {
                        "metric": metric_name,
                        "tags": http_metric.labels.copy(),
                        "aggregatedTags": aggregated_tags or [],
                        "dps": {}
                    }

                # Add datapoint to this time series
                timeseries_map[ts_key]["dps"][timestamp_ms] = metric_value

        # Convert map to list of response objects
        return list(timeseries_map.values())

    def reset_statistics(self):
        """Reset all statistics and clear metrics history"""
        with self.lock:
            self.metrics.clear()
            self.stats = {
                'total_requests': 0,
            }


# Global metrics collector instance
_metrics_collector: Optional[HTTPMetricsCollector] = None


def get_metrics_collector() -> HTTPMetricsCollector:
    """Get or create the global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = HTTPMetricsCollector()
    return _metrics_collector


class HTTPMetricsAPI:
    """REST API endpoint for accessing HTTP metrics"""
    exposed = True

    def __init__(self, logger):
        self.logger = logger
        self.collector = get_metrics_collector()

    def GET(self, **params):
        """
        Get HTTP metrics or bundle IDs.
        Query parameters:
            format: 'prometheus' (default), 'json', 'csv', 'opentsdb', or 'stats' (for /http_metrics)
            limit: Number of recent metrics to return (for json format)
            bundle_id: Specific bundle ID to retrieve (for /bundle_ids)
            registry: 'opentsdb', 'prometheus', or 'all' (default 'all') (for /bundle_ids)
        """
        format = params.get('format', 'prometheus')
        limit = params.get('limit', None)
        bundle_id = params.get('bundle_id', None)
        registry = params.get('registry', 'all')
        # /bundle_ids - Unified endpoint for both OpenTSDB and Prometheus bundle IDs
        if '/bundle_ids' == cherrypy.request.script_name:
            try:
                from opentsdb import get_bundle_info, get_all_bundle_ids, get_bundle_registry_stats
                from prometheus import get_prometheus_bundle_info, get_all_prometheus_bundle_ids, get_prometheus_bundle_registry_stats
                if bundle_id:
                    # Get specific bundle ID from requested registry/registries
                    result = {
                        'bundle_id': bundle_id,
                        'registries': {}
                    }

                    if registry in ['all', 'opentsdb']:
                        opentsdb_info = get_bundle_info(bundle_id)
                        result['registries']['opentsdb'] = {
                            'found': opentsdb_info is not None,
                            'info': opentsdb_info if opentsdb_info else None
                        }

                    if registry in ['all', 'prometheus']:
                        prometheus_info = get_prometheus_bundle_info(bundle_id)
                        result['registries']['prometheus'] = {
                            'found': prometheus_info is not None,
                            'info': prometheus_info if prometheus_info else None
                        }

                    cherrypy.response.headers['Content-Type'] = 'application/json'
                    return json.dumps(result)
                else:
                    # List all bundle IDs from requested registry/registries
                    result = {
                        'registries': {}
                    }

                    if registry in ['all', 'opentsdb']:
                        result['registries']['opentsdb'] = {
                            'stats': get_bundle_registry_stats(),
                            'bundles': get_all_bundle_ids()
                        }

                    if registry in ['all', 'prometheus']:
                        result['registries']['prometheus'] = {
                            'stats': get_prometheus_bundle_registry_stats(),
                            'bundles': get_all_prometheus_bundle_ids()
                        }

                    cherrypy.response.headers['Content-Type'] = 'application/json'
                    return json.dumps(result)

            except Exception as e:
                self.logger.error(f'Error retrieving bundle IDs: {e}')
                raise cherrypy.HTTPError(500, f'Error retrieving bundle IDs: {str(e)}')

        # /http_metrics
        elif '/http_metrics' == cherrypy.request.script_name:
            # Validate format parameter
            supported_formats = ['json', 'prometheus', 'csv', 'opentsdb', 'stats']
            if format not in supported_formats:
                raise cherrypy.HTTPError(400, f"Unsupported format '{format}'. Supported formats: {', '.join(supported_formats)}")
            
            try:
                if format == 'prometheus':
                    metrics_lines = self.collector.get_prometheus_metrics()
                    cherrypy.response.headers['Content-Type'] = 'text/plain; charset=utf-8'
                    resString = '\n'.join(metrics_lines) + '\n'
                    return resString
                elif format == 'opentsdb':
                    opentsdb_response = self.collector.get_opentsdb_metrics()
                    cherrypy.response.headers['Content-Type'] = 'application/json'
                    return json.dumps(opentsdb_response)
                elif format == 'csv':
                    limit_int = int(limit) if limit else None
                    csv_content = self.collector.get_csv_metrics(limit=limit_int)
                    cherrypy.response.headers['Content-Type'] = 'text/csv; charset=utf-8'
                    cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="http_metrics.csv"'
                    return csv_content
                elif format == 'stats':
                    resp = self.collector.get_statistics()
                    cherrypy.response.headers['Content-Type'] = 'application/json'
                    return json.dumps(resp)
                else:  # json format
                    limit_int = int(limit) if limit else None
                    return {
                        'metrics': self.collector.get_recent_metrics(limit=limit_int),
                        'statistics': self.collector.get_statistics()
                    }
            except Exception as e:
                self.logger.error(f'Error retrieving HTTP metrics: {e}')
                raise cherrypy.HTTPError(500, f'Error retrieving metrics: {str(e)}')
        # /internal_stat
        elif '/internal_stats' == cherrypy.request.script_name:
            resp = self.collector.get_statistics()
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return json.dumps(resp)

    @cherrypy.tools.json_out()
    def DELETE(self):
        """Reset all metrics and statistics"""
        try:
            self.collector.reset_statistics()
            self.logger.info('HTTP metrics reset successfully')
            return {'status': 'success', 'message': 'Metrics reset successfully'}
        except Exception as e:
            self.logger.error(f'Error resetting HTTP metrics: {e}')
            raise cherrypy.HTTPError(500, f'Error resetting metrics: {str(e)}')
