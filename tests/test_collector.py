import logging
import os
import json
from unittest import mock
from source.bridgeLogger import configureLogging
from source.queryHandler.Topo import Topo
from nose2.tools.decorators import with_setup
from source.collector import QueryPolicy, SensorCollector


def my_setup():
    global path, topo, logger, prometheus_attrs, pfilters, pquery_filters
    path = os.getcwd()
    topoStrFile = os.path.join(path, "tests", "test_data", 'topoStr.json')
    with open(topoStrFile) as f:
        topoStr = json.load(f)
    topo = Topo(topoStr)
    logger = configureLogging(path, None)
    prometheus_attrs = {'sensor': 'GPFSFilesystem', 'period': 300,
            'nsamples': 300, 'rawData': True}
    pfilters = {'node':'scale-16', 'gpfs_filesystem_name' : 'afmCacheFS'}
    pquery_filters = [ f"{k}={v}" for k, v in pfilters.items()]


@with_setup(my_setup)
def test_case01():
    with mock.patch('source.collector.QueryPolicy.md') as md:
        md_instance = md.return_value
        md_instance.includeDiskData.return_value = False
        md_instance.logger = logging.getLogger(__name__)
        request = QueryPolicy(**prometheus_attrs)
        query = request.get_zimon_query()
        query.includeDiskData = md_instance.includeDiskData.return_value
        queryString = 'get -j {0} {1} group {2} bucket_size {3} {4}'.format(
                '', '-z', prometheus_attrs.get('sensor'),
                prometheus_attrs.get('period'),
                f"last {prometheus_attrs.get('period')}")
        queryString += '\n'
        assert "group" in query.__str__()
        assert "last" in query.__str__()
        assert "from" not in query.__str__()
        assert queryString == query.__str__()


@with_setup(my_setup)
def test_case02():
    prometheus_attrs.update({'nsamples': 1, 'rawData': False})
    with mock.patch('source.collector.QueryPolicy.md') as md:
        md_instance = md.return_value
        md_instance.includeDiskData.return_value = False
        md_instance.logger = logging.getLogger(__name__)
        request = QueryPolicy(**prometheus_attrs)
        query = request.get_zimon_query()
        query.includeDiskData = md_instance.includeDiskData.return_value
        queryString = 'get -j {0} {1} group {2} bucket_size {3} {4}'.format(
                '', '', prometheus_attrs.get('sensor'),
                prometheus_attrs.get('period'),
                f"last {prometheus_attrs.get('nsamples')}")
        queryString += '\n'
        assert "group" in query.__str__()
        assert "last" in query.__str__()
        assert "from" not in query.__str__()


@with_setup(my_setup)
def test_case03():
    prometheus_attrs.update({'filters' : pfilters})
    with mock.patch('source.collector.QueryPolicy.md') as md:
        md_instance = md.return_value
        md_instance.includeDiskData.return_value = False
        md_instance.logger = logging.getLogger(__name__)
        request = QueryPolicy(**prometheus_attrs)
        query = request.get_zimon_query()
        query.includeDiskData = md_instance.includeDiskData.return_value
        queryString = 'get -j {0} {1} group {2} bucket_size {3} {4}'.format(
                '', '-z', prometheus_attrs.get('sensor'),
                prometheus_attrs.get('period'),
                f"last {prometheus_attrs.get('period')}")
        queryString += ' from ' + ",".join(pquery_filters)
        queryString += '\n'
        assert "group" in query.__str__()
        assert "last" in query.__str__()
        assert "from" in query.__str__()
        assert queryString == query.__str__()


@with_setup(my_setup)
def test_case04():
    prometheus_attrs.update({'filters' : pfilters})
    prometheus_attrs.update({'nsamples': 1, 'rawData': False})
    with mock.patch('source.collector.QueryPolicy.md') as md:
        md_instance = md.return_value
        md_instance.includeDiskData.return_value = False
        md_instance.logger = logging.getLogger(__name__)
        request = QueryPolicy(**prometheus_attrs)
        query = request.get_zimon_query()
        query.includeDiskData = md_instance.includeDiskData.return_value
        queryString = 'get -j {0} {1} group {2} bucket_size {3} {4}'.format(
                '', '', prometheus_attrs.get('sensor'),
                prometheus_attrs.get('period'),
                f"last {prometheus_attrs.get('nsamples')}")
        queryString += ' from ' + ",".join(pquery_filters)
        queryString += '\n'
        assert "group" in query.__str__()
        assert "last" in query.__str__()
        assert "from" in query.__str__()
        assert queryString == query.__str__()


@with_setup(my_setup)
@mock.patch('source.collector.QueryPolicy.md')
@mock.patch('source.collector.SensorTimeSeries.md')
@mock.patch('source.collector.SensorCollector.md')
def test_case05(col_md, sts_md, md):
    sensor = prometheus_attrs.get('sensor')
    period = prometheus_attrs.get('period')
    logger = logging.getLogger(__name__)
    prometheus_attrs.update({'filters' : pfilters})
    prometheus_attrs.update({'nsamples': 1, 'rawData': False})

    md_instance = md.return_value
    md_instance.includeDiskData.return_value = False
    md_instance.logger.return_value = logger
    md_instance.metaData.return_value = topo

    md_instance1 = sts_md.return_value
    md_instance1.includeDiskData.return_value = False
    md_instance1.logger.return_value = logger
    md_instance1.metaData.return_value = topo

    md_instance2 = col_md.return_value
    md_instance2.includeDiskData.return_value = False
    md_instance2.logger.return_value = logger
    md_instance2.metaData.return_value = topo

    request = QueryPolicy(**prometheus_attrs)
    collector = SensorCollector(sensor, period, logger, request)
    assert collector.sensor == sensor
    assert collector.period == period
    assert collector.request == request
    assert collector.labels == topo.getSensorLabels(sensor)

