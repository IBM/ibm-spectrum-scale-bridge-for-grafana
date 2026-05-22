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

Unit tests for stats.py module
'''

import unittest
import time
import json
import csv
from io import StringIO
from unittest import mock
from source.stats import HTTPRequestMetric, HTTPMetricsCollector, get_metrics_collector


class TestHTTPRequestMetric(unittest.TestCase):
    """Test cases for HTTPRequestMetric dataclass"""

    def setUp(self):
        """Set up test fixtures"""
        self.timestamp = time.time()
        self.labels = {
            'bundle_id': 'test_bundle_123',
            'collector_name': 'GPFSFilesystemIO',
            'job': 'prometheus-job1'
        }
        self.metrics = {
            'PrometheusExporter_metrics': 0.234,
            'perfmon_response_duration': 0.189,
            'perfmon_response_amount': 1024,
            'perfmon_response_content': 512
        }
        self.metric = HTTPRequestMetric(
            timestamp=self.timestamp,
            labels=self.labels,
            metrics=self.metrics
        )

    def test_metric_creation(self):
        """Test HTTPRequestMetric creation"""
        self.assertEqual(self.metric.timestamp, self.timestamp)
        self.assertEqual(self.metric.labels, self.labels)
        self.assertEqual(self.metric.metrics, self.metrics)

    def test_convert_bundle_to_metrics_timeseries(self):
        """Test conversion of bundle to metrics timeseries"""
        result = self.metric.convert_bundle_to_metrics_timeseries()
        # Check that all metrics are present
        self.assertEqual(len(result), len(self.metrics))
        # Check structure of each metric
        for metric_name, metric_value in self.metrics.items():
            self.assertIn(metric_name, result)
            timeseries_list = result[metric_name]
            self.assertEqual(len(timeseries_list), 1)
            
            timeserie = timeseries_list[0]
            self.assertEqual(timeserie['labels'], self.labels)
            self.assertEqual(timeserie['value'], metric_value)
            self.assertEqual(timeserie['timestamp'], self.timestamp)


class TestHTTPMetricsCollector(unittest.TestCase):
    """Test cases for HTTPMetricsCollector class"""

    def setUp(self):
        """Set up test fixtures"""
        self.collector = HTTPMetricsCollector()
        self.timestamp = time.time()
        self.labels = {
            'bundle_id': 'test_bundle_456',
            'collector_name': 'GPFSPoolCap',
            'job': 'prometheus-job2'
        }
        self.metrics = {
            'PrometheusExporter_metrics': 0.156,
            'perfmon_response_duration': 0.123
        }

    def test_collector_initialization(self):
        """Test HTTPMetricsCollector initialization"""
        self.assertIsNotNone(self.collector.metrics)
        self.assertIsNotNone(self.collector.stats)
        self.assertIsNotNone(self.collector.lock)
        self.assertEqual(self.collector.stats['total_requests'], 0)

    def test_record_metric(self):
        """Test recording a metric"""
        initial_count = self.collector.stats['total_requests']
        self.collector.record_metric(self.labels, self.metrics)
        # Check that total_requests increased
        self.assertEqual(self.collector.stats['total_requests'], initial_count + 1)
        self.assertEqual(len(self.collector.metrics), 1)

    def test_get_recent_metrics_with_limit(self):
        """Test getting recent metrics with limit"""
        for i in range(10):
            self.collector.record_metric(self.labels, self.metrics)

        recent = self.collector.get_recent_metrics(limit=5)
        self.assertEqual(len(recent), 5)
        self.assertIsInstance(recent[0], HTTPRequestMetric)

    def test_get_recent_metrics_without_limit(self):
        """Test getting all recent metrics"""
        # Add 3 metrics
        for i in range(3):
            self.collector.record_metric(self.labels, self.metrics)
        # Get all metrics
        recent = self.collector.get_recent_metrics()
        self.assertEqual(len(recent), 3)

    def test_get_metrics_last_5_minutes(self):
        """Test getting metrics from last 5 minutes"""
        self.collector.record_metric(self.labels, self.metrics)
        # Get metrics from last 5 minutes
        recent_metrics = self.collector.get_metrics_last_5_minutes()
        # Should have at least the metric we just added
        self.assertGreaterEqual(len(recent_metrics), 1)

    def test_get_prometheus_metrics(self):
        """Test Prometheus metrics format generation"""
        self.collector.record_metric(self.labels, self.metrics)
        lines = self.collector.get_prometheus_metrics()
        # Check that output contains expected elements
        output = '\n'.join(lines)
        self.assertIn('# HELP', output)
        self.assertIn('# TYPE', output)
        self.assertIn('PrometheusExporter_metrics', output)
        self.assertIn('perfmon_response_duration', output)
        # Check that labels are included
        self.assertIn('bundle_id="test_bundle_456"', output)
        self.assertIn('collector_name="GPFSPoolCap"', output)

    def test_get_opentsdb_format(self):
        """Test OpenTSDB format generation via HTTPMetricsCollector"""
        self.collector.record_metric(self.labels, self.metrics)
        # Get metrics in OpenTSDB format
        opentsdb_response = self.collector.get_opentsdb_metrics()
        # Check that response is a list
        self.assertIsInstance(opentsdb_response, list)
        self.assertGreater(len(opentsdb_response), 0)
        # Check structure of first response
        first_metric = opentsdb_response[0]
        self.assertIn('metric', first_metric)
        self.assertIn('tags', first_metric)
        self.assertIn('dps', first_metric)
        # Check that tags match our labels
        self.assertEqual(first_metric['tags'], self.labels)
        # Check that dps is a dict with timestamp keys
        self.assertIsInstance(first_metric['dps'], dict)
        self.assertGreater(len(first_metric['dps']), 0)

    def test_get_opentsdb_format_with_aggregated_tags(self):
        """Test OpenTSDB format generation with aggregated tags"""
        self.collector.record_metric(self.labels, self.metrics)
        aggregated_tags = ['node', 'cluster']
        opentsdb_response = self.collector.get_opentsdb_metrics(aggregated_tags=aggregated_tags)
        # Check that aggregatedTags is present in response
        self.assertGreater(len(opentsdb_response), 0)
        first_metric = opentsdb_response[0]
        self.assertIn('aggregatedTags', first_metric)
        self.assertEqual(first_metric['aggregatedTags'], aggregated_tags)

    def test_get_csv_metrics(self):
        """Test CSV metrics format generation"""
        # Add metrics with different label sets
        labels1 = {'bundle_id': 'bundle1', 'collector_name': 'Collector1', 'job': 'job1'}
        labels2 = {'bundle_id': 'bundle2', 'collector_name': 'Collector2'}  # Missing 'job'

        self.collector.record_metric(labels1, self.metrics)
        self.collector.record_metric(labels2, self.metrics)

        csv_output = self.collector.get_csv_metrics()
        reader = csv.DictReader(StringIO(csv_output))
        rows = list(reader)

        # Check header contains all expected columns
        headers = reader.fieldnames
        self.assertIsNotNone(headers)
        self.assertIn('timestamp', headers)
        self.assertIn('metric_name', headers)
        self.assertIn('value', headers)
        self.assertIn('bundle_id', headers)
        self.assertIn('collector_name', headers)
        self.assertIn('job', headers)

        # Check that we have rows for all metrics
        # 2 records * 2 metrics each = 4 rows
        self.assertEqual(len(rows), 4)

        # Check that missing labels are handled (empty string)
        bundle2_rows = [r for r in rows if r['bundle_id'] == 'bundle2']
        self.assertTrue(all(r['job'] == '' for r in bundle2_rows))

    def test_get_csv_metrics_empty(self):
        """Test CSV generation with no metrics"""
        csv_output = self.collector.get_csv_metrics()

        lines = csv_output.strip().split('\n')
        self.assertEqual(len(lines), 1)  # Only header
        self.assertIn('timestamp', lines[0])

    def test_get_csv_metrics_with_limit(self):
        """Test CSV metrics format generation with limit parameter"""
        # Record multiple metrics
        for i in range(5):
            labels = self.labels.copy()
            labels['iteration'] = str(i)
            self.collector.record_metric(labels, self.metrics)
        csv_content = self.collector.get_csv_metrics(limit=2)
        self.assertIsInstance(csv_content, str)
        self.assertGreater(len(csv_content), 0)
        # Check for header row and limited data rows
        lines = csv_content.strip().split('\n')
        # Should have header + (2 metrics * number of metric keys in self.metrics)
        # Each metric generates multiple rows (one per metric key)
        self.assertGreater(len(lines), 1)  # At least header + some data
        # Verify we got limited results (not all 5 iterations)
        csv_full = self.collector.get_csv_metrics()
        lines_full = csv_full.strip().split('\n')
        self.assertLess(len(lines), len(lines_full))

    def test_get_statistics(self):
        """Test getting statistics"""

        for i in range(5):
            self.collector.record_metric(self.labels, self.metrics)

        stats = self.collector.get_statistics()

        # Check basic statistics
        self.assertEqual(stats['total_requests'], 5)
        self.assertEqual(stats['metrics_in_memory_count'], 5)
        self.assertIn('metrics_in_memory_size', stats)
        self.assertGreater(stats['metrics_in_memory_size'], 0)

    def test_reset_statistics(self):
        """Test resetting statistics"""

        self.collector.record_metric(self.labels, self.metrics)
        self.assertEqual(self.collector.stats['total_requests'], 1)
        self.assertEqual(len(self.collector.metrics), 1)

        self.collector.reset_statistics()

        # Check that everything is cleared
        self.assertEqual(self.collector.stats['total_requests'], 0)
        self.assertEqual(len(self.collector.metrics), 0)

    def test_maxlen_enforcement(self):
        """Test that metrics deque respects maxlen"""

        maxlen = 10000  # Default maxlen
        for i in range(maxlen + 100):
            self.collector.record_metric(self.labels, self.metrics)

        self.assertLessEqual(len(self.collector.metrics), maxlen)

    def test_thread_safety(self):
        """Test that collector is thread-safe"""
        import threading

        def add_metrics():
            for i in range(100):
                self.collector.record_metric(self.labels, self.metrics)

        # Create multiple threads
        threads = [threading.Thread(target=add_metrics) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(self.collector.stats['total_requests'], 500)


class TestGetMetricsCollector(unittest.TestCase):
    """Test cases for get_metrics_collector singleton function"""

    def test_singleton_pattern(self):
        """Test that get_metrics_collector returns the same instance"""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        self.assertIs(collector1, collector2)

    def test_collector_persistence(self):
        """Test that collector persists data across calls"""
        collector1 = get_metrics_collector()
        labels = {'test': 'label'}
        metrics = {'test_metric': 1.0}

        collector1.record_metric(labels, metrics)

        collector2 = get_metrics_collector()
        self.assertEqual(collector2.stats['total_requests'], 1)


if __name__ == '__main__':
    unittest.main()
