import logging
import os
from unittest import mock
from nose2.tools.decorators import with_setup
from source.queryHandler.QueryHandler import ColumnInfo, Key
from source.profiler import Profiler
from source.collector import MetricTimeSeries, TimeSeries
from source.opentsdb import OpenTsdbApi


def my_setup():
    global key1, key2, key3, col1, col2, col3, labels, filtersMap, dps1, dps2, ts1, ts2, metricTS, data, jreq

    key1 = Key._from_string('scale-11|GPFSFilesystem|scale-cluster-1.vmlocal|localFS|gpfs_fs_bytes_read', '')
    key2 = Key._from_string('scale-12|GPFSFilesystem|scale-cluster-1.vmlocal|localFS|gpfs_fs_bytes_read', '')
    key3 = Key._from_string('scale-13|GPFSFilesystem|scale-cluster-1.vmlocal|localFS|gpfs_fs_bytes_read', '')

    col1 = ColumnInfo(name='gpfs_fs_bytes_read', semType=2,
                      keys=(key1,), column=6)
    col2 = ColumnInfo(name='gpfs_fs_bytes_read', semType=2,
                      keys=(key2,), column=6)
    col3 = ColumnInfo(name='gpfs_fs_bytes_read', semType=2,
                      keys=(key3,), column=6)

    labels = ['node', 'gpfs_cluster_name', 'gpfs_fs_name']

    filtersMap = [{'node': 'scale-11', 'gpfs_cluster_name': 'scale-cluster-1.vmlocal', 'gpfs_fs_name': 'localFS'},
                  {'node': 'scale-12', 'gpfs_cluster_name': 'scale-cluster-1.vmlocal', 'gpfs_fs_name': 'localFS'}]

    dps1 = {1715963000: 0, 1715963010: 0, 1715963020: 0, 1715963030: 0, 1715963040: 0, 1715963050: 0,
            1715963060: 0, 1715963070: 0, 1715963080: 0, 1715963090: 0, 1715963100: 0, 1715963110: 0,
            1715963120: 0, 1715963130: 0, 1715963140: 0, 1715963150: 0, 1715963160: 0, 1715963170: 0}

    dps2 = {1715963000: 0, 1715963010: 0, 1715963020: 0, 1715963030: 0, 1715963040: 0, 1715963050: 0,
            1715963060: 0, 1715963070: 0, 1715963080: 0, 1715963090: 0, 1715963100: 0, 1715963110: 0,
            1715963120: 0, 1715963130: 0, 1715963140: 0, 1715963150: 0, 1715963160: 0, 1715963170: 0}

    ts1 = TimeSeries(col1, dps1, filtersMap, labels)
    ts2 = TimeSeries(col2, dps2, filtersMap, labels)

    metricTS = MetricTimeSeries('gpfs_fs_bytes_read', '')
    metricTS.timeseries = [ts1, ts2]

    data = {'gpfs_fs_bytes_read': metricTS}
    jreq = {'start': 1715916393902, 'msResolution': False, 'globalAnnotations': True, 'showQuery': True,
            'inputQuery': {'aggregator': 'noop', 'alias': '$tag_node', 'currentFilterGroupBy': False,
                           'currentFilterKey': '', 'currentFilterType': 'literal_or', 'currentFilterValue': '',
                           'datasource': {'type': 'opentsdb', 'uid': 'a7fc0a73-eac4-4da7-974a-353e200e9f55'},
                           'downsampleAggregator': 'sum', 'downsampleFillPolicy': 'none', 'downsampleInterval': '15m',
                           'filters': [
                               {'filter': 'localFS', 'groupBy': False,
                                'tagk': 'gpfs_fs_name', 'type': 'pm_filter'
                                },
                               {'filter': 'scale-11|scale-12',
                                'groupBy': False, 'tagk': 'node', 'type': 'pm_filter'
                                }],
                           'metric': 'gpfs_fs_bytes_read', 'refId': 'A', 'downsample': '15m-sum', 'index': 0
                           }
            }


def query_last_setup():
    global key1, col1, labels, filtersMap, dps1, ts1, metricTS, data, jreq

    key1 = Key._from_string('scale-16|CPU|cpu_user', '')
    col1 = ColumnInfo(name='cpu_user', semType=1, keys=(key1,), column=0)
    filtersMap = [{'node': 'scale-11'}, {'node': 'scale-12'}, {'node': 'scale-13'}, {'node': 'scale-14'}, {'node': 'scale-15'}, {'node': 'scale-16'}]
    labels = ['node']
    dps1 = {1737321193: 3.0}
    ts1 = TimeSeries(col1, dps1, filtersMap, labels)
    metricTS = MetricTimeSeries('cpu_user', '')
    metricTS.timeseries = [ts1]
    data = {'cpu_user': metricTS}
    jreq = {'start': 'last', 'inputQuery': {'metric': 'cpu_user',
                                            'tags': {'node': 'scale-16'},
                                            'index': 0}}


def query_arrays_setup():
    global key1, col1, labels, filtersMap, dps1, ts1, ts2, metricTS, metricTS1, data, data1, jreq

    key1 = Key._from_string('scale-11|CPU|cpu_system', '')
    col1 = ColumnInfo(name='cpu_user', semType=1, keys=(key1,), column=0)
    filtersMap = [{'node': 'scale-11'}, {'node': 'scale-12'}, {'node': 'scale-13'}, {'node': 'scale-14'}, {'node': 'scale-15'}, {'node': 'scale-16'}]
    labels = ['node']
    dps1 = [[1739214990, 3], [1739215050, 2], [1739215110, 3], [1739215170, 4], [1739215230, 3]]
    dps2 = []
    ts1 = TimeSeries(col1, dps1, filtersMap, labels)
    ts2 = TimeSeries(col1, dps2, filtersMap, labels)
    metricTS = MetricTimeSeries('cpu_system', '')
    metricTS.timeseries = [ts1]
    data = {'cpu_user': metricTS}
    metricTS1 = MetricTimeSeries('cpu_system', '')
    metricTS1.timeseries = [ts2]
    data1 = {'cpu_user': metricTS1}
    jreq = {'start': 1739214930519, 'end': 1739215230519, 'arrays': True,
            'inputQuery': {'aggregator': 'noop', 'downsample': '1m-avg',
                           'filters': [
                               {'filter': 'scale-11', 'groupBy': False,
                                'tagk': 'node', 'type': 'pm_filter'
                                }],
                           'metric': 'cpu_system', 'index': 0
                           }
            }

def query_raw_data_setup():
    global jreq, jreq1, jreq2, jreq3

    jreq = {'start': 1739214930519, 'end': 1739215230519, 'arrays': True,
            'inputQuery': {'aggregator': 'noop', 'downsample': '1m-avg',
                           'filters': [
                               {'filter': 'scale-11', 'groupBy': False,
                                'tagk': 'node', 'type': 'pm_filter'
                                }],
                           'metric': 'cpu_system', 'index': 0,
                           'shouldComputeRate': False, 'isCounter': False
                           }
            }
    jreq1 = {'start': 1739214930519, 'end': 1739215230519, 'arrays': True,
            'inputQuery': {'aggregator': 'noop', 'downsample': '1m-avg',
                           'filters': [
                               {'filter': 'scale-11', 'groupBy': False,
                                'tagk': 'node', 'type': 'pm_filter'
                                }],
                           'metric': 'cpu_system', 'index': 0,
                           'shouldComputeRate': True, 'isCounter': False
                           }
            }
    jreq2 = {'start': 1739214930519, 'end': 1739215230519, 'arrays': True,
            'inputQuery': {'aggregator': 'noop', 'downsample': '1m-avg',
                           'filters': [
                               {'filter': 'scale-11', 'groupBy': False,
                                'tagk': 'node', 'type': 'pm_filter'
                                }],
                           'metric': 'cpu_system', 'index': 0,
                           'shouldComputeRate': True, 'isCounter': True
                           }
            }


@with_setup(my_setup)
def test_case01():
    ts = TimeSeries(col3, dps2, filtersMap, labels)
    assert len(ts.tags) > 0
    assert len(ts.tags) == len(labels)
    assert all(item in ts.tags.keys() for item in labels)
    assert ts.tags['node'] == 'scale-13'
    assert ts.tags['gpfs_fs_name'] == 'localFS'


@with_setup(my_setup)
def test_case02():
    with mock.patch('source.metadata.MetadataHandler') as md:
        md_instance = md.return_value
        logger = logging.getLogger(__name__)
        opentsdb = OpenTsdbApi(logger, md_instance, '9999')
        resp = opentsdb.format_response(data, jreq)
        assert isinstance(resp, list)
        assert len(resp) > 0
        assert len(resp) == 2


@with_setup(my_setup)
def test_case03():
    with mock.patch('source.metadata.MetadataHandler') as md:
        md_instance = md.return_value
        logger = logging.getLogger(__name__)
        opentsdb = OpenTsdbApi(logger, md_instance, '9999')
        resp = opentsdb.format_response(data, jreq)
        assert resp[0].get('metric') == "gpfs_fs_bytes_read"
        assert resp[0].get('query') == jreq.get('inputQuery')
        assert 'gpfs_fs_name' in resp[0].get('tags')
        assert 'node' in resp[0].get('tags')
        assert 'gpfs_cluster_name' in resp[0].get('tags')
        assert isinstance(resp[0].get('dps'), dict)


@with_setup(my_setup)
def test_case04():
    with mock.patch('source.metadata.MetadataHandler') as md:
        md_instance = md.return_value
        logger = logging.getLogger(__name__)
        opentsdb = OpenTsdbApi(logger, md_instance, '9999')
        profiler = Profiler()
        resp = profiler.run(opentsdb.format_response, *(data, jreq))
        # resp = opentsdb.format_response(data, jreq)
        assert resp is not None
        assert os.path.exists(os.path.join(profiler.path, "profiling_format_response.prof"))
        response = profiler.stats(os.path.join(profiler.path, "profiling_format_response.prof"))
        assert response is not None
        print('\n'.join(response) + '\n')


@with_setup(query_last_setup)
def test_case05():
    with mock.patch('source.metadata.MetadataHandler') as md:
        md_instance = md.return_value
        logger = logging.getLogger(__name__)
        opentsdb = OpenTsdbApi(logger, md_instance, '9999')
        resp = opentsdb.format_response(data, jreq)
        assert set(resp[0].keys()) == set(['metric', 'timestamp', 'value', 'tags'])
        assert resp[0].get('metric') == "cpu_user"
        assert 'gpfs_fs_name' not in resp[0].get('tags')
        assert 'node' in resp[0].get('tags')


@with_setup(query_arrays_setup)
def test_case06():
    with mock.patch('source.metadata.MetadataHandler') as md:
        md_instance = md.return_value
        logger = logging.getLogger(__name__)
        opentsdb = OpenTsdbApi(logger, md_instance, '9999')
        resp = opentsdb.format_response(data, jreq)
        assert set(resp[0].keys()) == set(['metric', 'dps', 'tags', 'aggregatedTags'])
        assert resp[0].get('metric') == "cpu_system"
        assert 'node' in resp[0].get('tags')
        assert isinstance(resp[0].get('dps'), list)


@with_setup(query_arrays_setup)
def test_case07():
    with mock.patch('source.metadata.MetadataHandler') as md:
        md_instance = md.return_value
        logger = logging.getLogger(__name__)
        opentsdb = OpenTsdbApi(logger, md_instance, '9999')
        resp = opentsdb.format_response(data1, jreq)
        assert set(resp[0].keys()) == set(['metric', 'dps', 'tags', 'aggregatedTags'])
        assert resp[0].get('metric') == "cpu_system"
        assert 'node' in resp[0].get('tags')
        assert isinstance(resp[0].get('dps'), list)
        assert len(resp[0].get('dps')) == 0


@with_setup(query_raw_data_setup)
def test_case08():
    q = jreq.get('inputQuery')
    args = {}
    args['rawData'] = q.get('explicitTags', False) or q.get('isCounter', False)
    assert args.get('rawData') == False
    q1 = jreq1.get('inputQuery')
    args1 = {}
    args1['rawData'] = q1.get('explicitTags', False) or q1.get('isCounter', False)
    assert args1.get('rawData') == False
    q2 = jreq2.get('inputQuery')
    args2 = {}
    args2['rawData'] = q2.get('explicitTags', False) or q2.get('isCounter', False)
    assert args2.get('rawData') == True
