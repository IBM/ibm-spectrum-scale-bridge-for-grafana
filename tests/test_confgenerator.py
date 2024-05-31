import logging
import os
from unittest import mock
from nose2.tools.decorators import with_setup
from source.profiler import Profiler
from source.metadata import MetadataHandler
from source.confgenerator import PrometheusConfigGenerator


def my_setup():
    global attr, attr1, args, endpoints, sensors_conf

    path = os.getcwd()
    pwFile = os.path.join(path, "tests", "test_data", 'basic_auth')

    attr = {'port': 4242, 'prometheus': 9250, 'rawCounters': True, 'protocol': 'http', 'enabled': True,
            'username': 'scale_admin', 'password': 'TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg==', 'server': 'localhost',
            'serverPort': 9980, 'retryDelay': 60, 'apiKeyName': 'scale_grafana',
            'apiKeyValue': 'c0a910e4-094a-46d8-b04d-c2f73a43fd17', 'caCertPath': False,
            'includeDiskData': False, 'logPath': '/var/log/ibm_bridge_for_grafana', 'logLevel': 10,
            'logFile': 'zserver.log'}

    attr1 = {'port': 4242, 'prometheus': 9250, 'rawCounters': True, 'protocol': 'http', 'enabled': True,
             'username': 'scale_admin', 'server': 'localhost',
             'serverPort': 9980, 'retryDelay': 60, 'apiKeyName': 'scale_grafana',
             'apiKeyValue': 'c0a910e4-094a-46d8-b04d-c2f73a43fd17', 'caCertPath': False,
             'includeDiskData': False, 'logPath': '/var/log/ibm_bridge_for_grafana', 'logLevel': 10,
             'logFile': 'zserver.log'}

    attr1['password'] = pwFile

    args = {'server': 'localhost', 'port': 9980, 'retryDelay': 60,
            'apiKeyName': 'scale_grafana',
            'apiKeyValue': 'c0a910e4-094a-46d8-b04d-c2f73a43fd17'}

    endpoints = {"/metrics_gpfs_disk": "GPFSDisk",
                 "/metrics_gpfs_filesystem": "GPFSFilesystem",
                 "//metrics_gpfs_fileset": "GPFSFileset",
                 "/metrics_gpfs_pool": "GPFSPool"}

    sensors_conf = [{'name': '"CPU"', 'period': '1'},
                    {'name': '"Load"', 'period': '1'},
                    {'name': '"Memory"', 'period': '1'},
                    {'filter': '"netdev_name=veth.*|docker.*|flannel.*|cali.*|cbr.*"',
                     'name': '"Network"', 'period': '1'},
                    {'name': '"Netstat"', 'period': '10'},
                    {'name': '"Diskstat"', 'period': '0'},
                    {'filter': '"mountPoint=/.*/docker.*|/.*/kubelet.*"', 'name': '"DiskFree"', 'period': '600'},
                    {'name': '"Infiniband"', 'period': '0'},
                    {'name': '"GPFSDisk"', 'period': '0'},
                    {'name': '"GPFSFilesystem"', 'period': '10'},
                    {'name': '"GPFSNSDDisk"', 'period': '10', 'restrict': '"nsdNodes"'},
                    {'name': '"GPFSPoolIO"', 'period': '0'}, {'name': '"GPFSVFSX"', 'period': '10'},
                    {'name': '"GPFSIOC"', 'period': '0'}, {'name': '"GPFSVIO64"', 'period': '0'},
                    {'name': '"GPFSPDDisk"', 'period': '10', 'restrict': '"nsdNodes"'},
                    {'name': '"GPFSvFLUSH"', 'period': '0'}, {'name': '"GPFSNode"', 'period': '10'},
                    {'name': '"GPFSNodeAPI"', 'period': '10'}, {'name': '"GPFSFilesystemAPI"', 'period': '10'},
                    {'name': '"GPFSLROC"', 'period': '0'}, {'name': '"GPFSCHMS"', 'period': '0'},
                    {'name': '"GPFSAFM"', 'period': '10', 'restrict': '"scale-16.vmlocal,scale-17.vmlocal"'},
                    {'name': '"GPFSAFMFS"', 'period': '10', 'restrict': '"scale-16.vmlocal,scale-17.vmlocal"'},
                    {'name': '"GPFSAFMFSET"', 'period': '10', 'restrict': '"scale-16.vmlocal,scale-17.vmlocal"'},
                    {'name': '"GPFSRPCS"', 'period': '10'}, {'name': '"GPFSWaiters"', 'period': '10'},
                    {'name': '"GPFSFilesetQuota"', 'period': '3600', 'restrict': '"@CLUSTER_PERF_SENSOR"'},
                    {'name': '"GPFSFileset"', 'period': '300', 'restrict': '"@CLUSTER_PERF_SENSOR"'},
                    {'name': '"GPFSPool"', 'period': '300', 'restrict': '"@CLUSTER_PERF_SENSOR"'},
                    {'name': '"GPFSDiskCap"', 'period': '86400', 'restrict': '"@CLUSTER_PERF_SENSOR"'},
                    {'name': '"GPFSEventProducer"', 'period': '0'}, {'name': '"GPFSMutex"', 'period': '0'},
                    {'name': '"GPFSCondvar"', 'period': '0'}, {'name': '"TopProc"', 'period': '60'},
                    {'name': '"GPFSQoS"', 'period': '0'}, {'name': '"GPFSFCM"', 'period': '0'},
                    {'name': '"GPFSBufMgr"', 'period': '30'},
                    {'name': '"NFSIO"', 'period': '10', 'restrict': '"cesNodes"', 'type': '"Generic"'},
                    {'name': '"SMBStats"', 'period': '1', 'restrict': '"cesNodes"', 'type': '"Generic"'},
                    {'name': '"SMBGlobalStats"', 'period': '1', 'restrict': '"cesNodes"', 'type': '"Generic"'},
                    {'name': '"CTDBStats"', 'period': '1', 'restrict': '"cesNodes"', 'type': '"Generic"'},
                    {'name': '"CTDBDBStats"', 'period': '1', 'restrict': '"cesNodes"', 'type': '"Generic"'}]


@with_setup(my_setup)
def test_case01():
    with mock.patch('source.metadata.MetadataHandler._MetadataHandler__initializeTables') as md_init:
        with mock.patch('source.metadata.MetadataHandler._MetadataHandler__getSupportedMetrics') as md_supp:
            with mock.patch('source.metadata.MetadataHandler.SensorsConfig', return_value=sensors_conf) as md_sensConf:
                with mock.patch('source.confgenerator.PrometheusConfigGenerator.host_ip', return_value='127.0.0.1'):
                    logger = logging.getLogger(__name__)
                    args['logger'] = logger
                    md = MetadataHandler(**args)
                    md.__initializeTables = md_init.return_value
                    md.__getSupportedMetrics = md_supp.return_value
                    md.SensorsConfig = md_sensConf.return_value
                    conf_generator = PrometheusConfigGenerator(logger, md, attr, endpoints)
                    resp = conf_generator.generate_config()
                    assert isinstance(resp, str)
                    assert len(resp) > 0
                    assert "password" in resp
                    assert "password_file" not in resp


@with_setup(my_setup)
def test_case02():
    with mock.patch('source.metadata.MetadataHandler._MetadataHandler__initializeTables') as md_init:
        with mock.patch('source.metadata.MetadataHandler._MetadataHandler__getSupportedMetrics') as md_supp:
            with mock.patch('source.metadata.MetadataHandler.SensorsConfig', return_value=sensors_conf) as md_sensConf:
                with mock.patch('source.confgenerator.PrometheusConfigGenerator.host_ip', return_value='127.0.0.1'):
                    logger = logging.getLogger(__name__)
                    args['logger'] = logger
                    md = MetadataHandler(**args)
                    md.__initializeTables = md_init.return_value
                    md.__getSupportedMetrics = md_supp.return_value
                    md.SensorsConfig = md_sensConf.return_value
                    conf_generator = PrometheusConfigGenerator(logger, md, attr1, endpoints)
                    resp = conf_generator.generate_config()
                    assert isinstance(resp, str)
                    assert len(resp) > 0
                    assert "password_file" in resp


@with_setup(my_setup)
def test_case03():
    with mock.patch('source.metadata.MetadataHandler._MetadataHandler__initializeTables') as md_init:
        with mock.patch('source.metadata.MetadataHandler._MetadataHandler__getSupportedMetrics') as md_supp:
            with mock.patch('source.metadata.MetadataHandler.SensorsConfig', return_value=sensors_conf) as md_sensConf:
                with mock.patch('source.confgenerator.PrometheusConfigGenerator.host_ip', return_value='127.0.0.1'):
                    logger = logging.getLogger(__name__)
                    args['logger'] = logger
                    md = MetadataHandler(**args)
                    md.__initializeTables = md_init.return_value
                    md.__getSupportedMetrics = md_supp.return_value
                    md.SensorsConfig = md_sensConf.return_value
                    conf_generator = PrometheusConfigGenerator(logger, md, attr, endpoints)
                    profiler = Profiler()
                    resp = profiler.run(conf_generator.generate_config)
                    assert resp is not None
                    assert os.path.exists(os.path.join(profiler.path, "profiling_generate_config.prof"))
                    response = profiler.stats(os.path.join(profiler.path, "profiling_generate_config.prof"))
                    assert response is not None
                    print('\n'.join(response) + '\n')
