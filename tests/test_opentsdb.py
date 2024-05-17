import logging
from unittest import mock
from nose2.tools.decorators import with_setup
from source.queryHandler.QueryHandler import ColumnInfo, Key
from source.collector import MetricTimeSeries, TimeSeries
from source.opentsdb import OpenTsdbApi


def my_setup():
    global key1, key2, col1, col2, filtersMap, dps1, dps2, ts1, ts2, metricTS, data, jreq

    key1 = Key._from_string('scale-11|GPFSFilesystem|scale-cluster-1.vmlocal|localFS|gpfs_fs_bytes_read', '')
    key2 = Key._from_string('scale-11|GPFSFilesystem|scale-cluster-1.vmlocal|localFS|gpfs_fs_bytes_read', '')

    col1 = ColumnInfo(name='gpfs_fs_bytes_read', semType=2,
                      keys=(key1,), column=6)
    col2 = ColumnInfo(name='gpfs_fs_bytes_read', semType=2,
                      keys=(key2,), column=6)

    filtersMap = [{'node': 'scale-11', 'gpfs_cluster_name': 'scale-cluster-1.vmlocal', 'gpfs_fs_name': 'localFS'},
                  {'node': 'scale-12', 'gpfs_cluster_name': 'scale-cluster-1.vmlocal', 'gpfs_fs_name': 'localFS'}]

    dps1 = {1715963000: 0, 1715963010: 0, 1715963020: 0, 1715963030: 0, 1715963040: 0, 1715963050: 0,
            1715963060: 0, 1715963070: 0, 1715963080: 0, 1715963090: 0, 1715963100: 0, 1715963110: 0,
            1715963120: 0, 1715963130: 0, 1715963140: 0, 1715963150: 0, 1715963160: 0, 1715963170: 0}

    dps2 = {1715963000: 0, 1715963010: 0, 1715963020: 0, 1715963030: 0, 1715963040: 0, 1715963050: 0,
            1715963060: 0, 1715963070: 0, 1715963080: 0, 1715963090: 0, 1715963100: 0, 1715963110: 0,
            1715963120: 0, 1715963130: 0, 1715963140: 0, 1715963150: 0, 1715963160: 0, 1715963170: 0}

    ts1 = TimeSeries(col1, dps1, filtersMap)
    ts2 = TimeSeries(col2, dps2, filtersMap)

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


@with_setup(my_setup)
def test_case01():
    with mock.patch('source.metadata.MetadataHandler') as md:
        md_instance = md.return_value
        logger = logging.getLogger(__name__)
        opentsdb = OpenTsdbApi(logger, md_instance, '9999')
        resp = opentsdb.format_response(data, jreq)
        assert isinstance(resp, list)
        assert len(resp) > 0
        assert len(resp) == 2


@with_setup(my_setup)
def test_case02():
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
