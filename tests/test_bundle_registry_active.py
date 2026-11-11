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

Unit tests for the last_seen / active_size tracking of the bundle ID registries
'''

import time
from nose2.tools.decorators import with_setup
from source import opentsdb, prometheus


def opentsdb_setup():
    global ts_queries, ts_host, ts_jreq
    ts_queries = [{'metric': 'm'}]
    ts_host = 'h'
    ts_jreq = {'start': 1}
    opentsdb.clear_bundle_registry()
    opentsdb._register_bundle_id('a', ts_queries, ts_host, ts_jreq)


def prometheus_setup():
    global prom_sensors, prom_host
    prom_sensors = ['s']
    prom_host = 'h'
    prometheus.clear_prometheus_bundle_registry()
    prometheus._register_prometheus_bundle_id('p', prom_sensors, None, prom_host)


@with_setup(opentsdb_setup)
def test_opentsdb_new_entry_is_active():
    stats = opentsdb.get_bundle_registry_stats()
    assert stats['size'] == 1
    assert stats['active_size'] == 1


@with_setup(opentsdb_setup)
def test_opentsdb_old_entry_is_not_active_with_default_window():
    opentsdb._opentsdb_bundle_registry['a']['last_seen'] = time.time() - 1000
    stats = opentsdb.get_bundle_registry_stats()
    assert stats['size'] == 1
    assert stats['active_size'] == 0


@with_setup(opentsdb_setup)
def test_opentsdb_custom_window():
    opentsdb._opentsdb_bundle_registry['a']['last_seen'] = time.time() - 1000
    assert opentsdb.get_bundle_registry_stats(2000)['active_size'] == 1
    assert opentsdb.get_bundle_registry_stats(10)['active_size'] == 0


@with_setup(opentsdb_setup)
def test_opentsdb_reuse_refreshes_last_seen():
    opentsdb._opentsdb_bundle_registry['a']['last_seen'] = time.time() - 1000
    opentsdb._register_bundle_id('a', ts_queries, ts_host, ts_jreq)
    assert opentsdb.get_bundle_registry_stats()['active_size'] == 1


@with_setup(prometheus_setup)
def test_prometheus_new_entry_is_active():
    stats = prometheus.get_prometheus_bundle_registry_stats()
    assert stats['size'] == 1
    assert stats['active_size'] == 1


@with_setup(prometheus_setup)
def test_prometheus_old_entry_is_not_active():
    prometheus._prometheus_bundle_registry['p']['last_seen'] = time.time() - 1000
    stats = prometheus.get_prometheus_bundle_registry_stats()
    assert stats['size'] == 1
    assert stats['active_size'] == 0


@with_setup(prometheus_setup)
def test_prometheus_reuse_refreshes_last_seen():
    prometheus._prometheus_bundle_registry['p']['last_seen'] = time.time() - 1000
    prometheus._register_prometheus_bundle_id('p', prom_sensors, None, prom_host)
    assert prometheus.get_prometheus_bundle_registry_stats()['active_size'] == 1
