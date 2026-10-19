import logging
import os
import tempfile
from unittest import mock
import cherrypy
from nose2.tools.decorators import with_setup
from source.profiler import Profiler
from source.metadata import MetadataHandler
from source.confgenerator import PrometheusConfigGenerator, INTERNAL_METRICS_JOBS


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


def _make_generator(attr_override=None, endpoints_override=None):
    """Build a PrometheusConfigGenerator with metadata mocked via getSensorPeriod.

    Returns (generator, period_patcher). Callers must call period_patcher.stop()
    when done. Use _patch_resolved_target(gen) in tests that call build_scrape_jobs
    or generate_* to avoid real network calls from _resolve_target.
    """
    logger = logging.getLogger(__name__)
    args_local = {'server': 'localhost', 'port': 9980, 'retryDelay': 60,
                  'apiKeyName': 'scale_grafana',
                  'apiKeyValue': 'c0a910e4-094a-46d8-b04d-c2f73a43fd17',
                  'logger': logger}

    def _period_from_conf(sensor):
        """Replicate MetadataHandler.getSensorPeriod using the test fixture."""
        for sattr in sensors_conf:
            if sattr['name'] == f'"{sensor}"':
                return int(sattr['period'])
        return 0

    with mock.patch('source.metadata.MetadataHandler._MetadataHandler__initializeTables') as md_init:
        with mock.patch('source.metadata.MetadataHandler._MetadataHandler__getSupportedMetrics') as md_supp:
            with mock.patch('source.metadata.MetadataHandler.SensorsConfig',
                            return_value=sensors_conf) as md_sensConf:
                md = MetadataHandler(**args_local)
                md.__initializeTables = md_init.return_value
                md.__getSupportedMetrics = md_supp.return_value
                md.SensorsConfig = md_sensConf.return_value

    period_patcher = mock.patch.object(md, 'getSensorPeriod', side_effect=_period_from_conf)
    period_patcher.start()

    used_attr = attr_override if attr_override is not None else attr
    used_endpoints = endpoints_override if endpoints_override is not None else endpoints
    gen = PrometheusConfigGenerator(logger, md, used_attr, used_endpoints)
    return gen, period_patcher


def _patch_resolved_target(gen, host='10.0.0.1', port=None):
    """Patch _resolve_target to avoid real network calls in unit tests."""
    used_port = port if port is not None else str(gen.attr.get('prometheus', 9250))
    return mock.patch.object(gen, '_resolve_target', return_value=(host, used_port))


# ---------------------------------------------------------------------------
# Legacy tests (kept for regression)
# ---------------------------------------------------------------------------

@with_setup(my_setup)
def test_case01():
    with mock.patch('source.metadata.MetadataHandler._MetadataHandler__initializeTables') as md_init:
        with mock.patch('source.metadata.MetadataHandler._MetadataHandler__getSupportedMetrics') as md_supp:
            with mock.patch('source.metadata.MetadataHandler.SensorsConfig', return_value=sensors_conf) as md_sensConf:
                with mock.patch('source.confgenerator.PrometheusConfigGenerator._resolve_target',
                                return_value=('127.0.0.1', '9250')):
                    logger = logging.getLogger(__name__)
                    args['logger'] = logger
                    md = MetadataHandler(**args)
                    md.__initializeTables = md_init.return_value
                    md.__getSupportedMetrics = md_supp.return_value
                    md.SensorsConfig = md_sensConf.return_value
                    period_patcher = mock.patch.object(md, 'getSensorPeriod', return_value=10)
                    period_patcher.start()
                    try:
                        conf_generator = PrometheusConfigGenerator(logger, md, attr, endpoints)
                        resp = conf_generator.generate_prometheus_config()
                        assert isinstance(resp, str)
                        assert len(resp) > 0
                        assert "password" in resp
                        assert "password_file" not in resp
                    finally:
                        period_patcher.stop()


@with_setup(my_setup)
def test_case02():
    with mock.patch('source.metadata.MetadataHandler._MetadataHandler__initializeTables') as md_init:
        with mock.patch('source.metadata.MetadataHandler._MetadataHandler__getSupportedMetrics') as md_supp:
            with mock.patch('source.metadata.MetadataHandler.SensorsConfig', return_value=sensors_conf) as md_sensConf:
                with mock.patch('source.confgenerator.PrometheusConfigGenerator._resolve_target',
                                return_value=('127.0.0.1', '9250')):
                    logger = logging.getLogger(__name__)
                    args['logger'] = logger
                    md = MetadataHandler(**args)
                    md.__initializeTables = md_init.return_value
                    md.__getSupportedMetrics = md_supp.return_value
                    md.SensorsConfig = md_sensConf.return_value
                    period_patcher = mock.patch.object(md, 'getSensorPeriod', return_value=10)
                    period_patcher.start()
                    try:
                        conf_generator = PrometheusConfigGenerator(logger, md, attr1, endpoints)
                        resp = conf_generator.generate_prometheus_config()
                        assert isinstance(resp, str)
                        assert len(resp) > 0
                        assert "password_file" in resp
                    finally:
                        period_patcher.stop()


@with_setup(my_setup)
def test_case03():
    with mock.patch('source.metadata.MetadataHandler._MetadataHandler__initializeTables') as md_init:
        with mock.patch('source.metadata.MetadataHandler._MetadataHandler__getSupportedMetrics') as md_supp:
            with mock.patch('source.metadata.MetadataHandler.SensorsConfig', return_value=sensors_conf) as md_sensConf:
                with mock.patch('source.confgenerator.PrometheusConfigGenerator._resolve_target',
                                return_value=('127.0.0.1', '9250')):
                    logger = logging.getLogger(__name__)
                    args['logger'] = logger
                    md = MetadataHandler(**args)
                    md.__initializeTables = md_init.return_value
                    md.__getSupportedMetrics = md_supp.return_value
                    md.SensorsConfig = md_sensConf.return_value
                    period_patcher = mock.patch.object(md, 'getSensorPeriod', return_value=10)
                    period_patcher.start()
                    try:
                        conf_generator = PrometheusConfigGenerator(logger, md, attr, endpoints)
                        profiler = Profiler()
                        resp = profiler.run(conf_generator.generate_prometheus_config)
                        assert resp is not None
                        assert os.path.exists(os.path.join(profiler.path, "profiling_generate_prometheus_config.prof"))
                        response = profiler.stats(os.path.join(profiler.path, "profiling_generate_prometheus_config.prof"))
                        assert response is not None
                        print('\n'.join(response) + '\n')
                    finally:
                        period_patcher.stop()


# ---------------------------------------------------------------------------
# scrape interval rule: max(period, 10)
# ---------------------------------------------------------------------------

@with_setup(my_setup)
def test_period_1_sensor_gets_min_interval():
    """A sensor with period=1 gets scrape_interval 10s."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_smb': 'SMBStats'})
    try:
        with _patch_resolved_target(gen):
            jobs = gen.build_scrape_jobs()
            assert len(jobs) == 1
            assert jobs[0]['scrape_interval'] == '10s', \
                f"Expected 10s for period-1 sensor, got {jobs[0]['scrape_interval']}"
    finally:
        _p.stop()


@with_setup(my_setup)
def test_period_10_sensor_gets_min_interval():
    """A sensor with period=10 gets scrape_interval 10s (boundary case)."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        with _patch_resolved_target(gen):
            jobs = gen.build_scrape_jobs()
            assert len(jobs) == 1
            assert jobs[0]['scrape_interval'] == '10s'
    finally:
        _p.stop()


@with_setup(my_setup)
def test_period_300_sensor_large_interval():
    """A sensor with period=300 gets scrape_interval 300s."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_fileset': 'GPFSFileset'})
    try:
        with _patch_resolved_target(gen):
            jobs = gen.build_scrape_jobs()
            assert len(jobs) == 1
            assert jobs[0]['scrape_interval'] == '300s'
    finally:
        _p.stop()


# ---------------------------------------------------------------------------
# job_suffix
# ---------------------------------------------------------------------------

@with_setup(my_setup)
def test_job_suffix_applied_to_sensor_jobs():
    """job_suffix is appended to every bridge-generated job name."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        with _patch_resolved_target(gen):
            jobs = gen.build_scrape_jobs(job_suffix='_clusterA')
            assert len(jobs) == 1
            assert jobs[0]['job_name'] == 'GPFSFilesystem_clusterA'
    finally:
        _p.stop()


@with_setup(my_setup)
def test_job_suffix_not_applied_to_self_job():
    """The static prometheus self-scrape job is never suffixed."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        with _patch_resolved_target(gen):
            resp = gen.generate_prometheus_config(job_suffix='_clusterA')
            assert 'job_name: prometheus\n' in resp
            assert 'job_name: prometheus_clusterA' not in resp
    finally:
        _p.stop()


@with_setup(my_setup)
def test_invalid_job_suffix_raises():
    """_parse_params raises HTTPError 400 for an invalid job_suffix."""
    import cherrypy
    gen, _p = _make_generator()
    try:
        try:
            gen._parse_params({'job_suffix': 'bad suffix!'})
            assert False, 'Expected HTTPError'
        except cherrypy.HTTPError as e:
            assert e.status == 400
    finally:
        _p.stop()


@with_setup(my_setup)
def test_empty_suffix_unchanged_output():
    """An empty job_suffix produces the same job names as no suffix."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        with _patch_resolved_target(gen):
            jobs_no_suffix = gen.build_scrape_jobs(job_suffix='')
            jobs_empty = gen.build_scrape_jobs(job_suffix='')
            assert [j['job_name'] for j in jobs_no_suffix] == \
                   [j['job_name'] for j in jobs_empty]
    finally:
        _p.stop()


# ---------------------------------------------------------------------------
# internal_metrics
# ---------------------------------------------------------------------------

@with_setup(my_setup)
def test_internal_metrics_false_adds_no_extra_jobs():
    """internal_metrics=False (default) adds no internal jobs."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        with _patch_resolved_target(gen):
            jobs = gen.build_scrape_jobs(internal_metrics=False)
            names = [j['job_name'] for j in jobs]
            for internal_name in INTERNAL_METRICS_JOBS:
                assert internal_name not in names
    finally:
        _p.stop()


@with_setup(my_setup)
def test_internal_metrics_true_adds_both_jobs():
    """internal_metrics=True adds exactly two internal jobs with correct paths and interval."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        with _patch_resolved_target(gen):
            with mock.patch('source.confgenerator.analytics') as mock_analytics:
                mock_analytics.http_metrics_enabled = True
                jobs = gen.build_scrape_jobs(internal_metrics=True)
            internal_jobs = [j for j in jobs if j['job_name'] in INTERNAL_METRICS_JOBS]
            assert len(internal_jobs) == 2
            for job in internal_jobs:
                assert job['scrape_interval'] == '60s'
                assert job['metrics_path'] in INTERNAL_METRICS_JOBS.values()
    finally:
        _p.stop()


@with_setup(my_setup)
def test_internal_metrics_with_suffix():
    """internal_metrics jobs also get the job_suffix."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        with _patch_resolved_target(gen):
            with mock.patch('source.confgenerator.analytics') as mock_analytics:
                mock_analytics.http_metrics_enabled = True
                jobs = gen.build_scrape_jobs(job_suffix='_X', internal_metrics=True)
            for base_name in INTERNAL_METRICS_JOBS:
                assert any(j['job_name'] == base_name + '_X' for j in jobs)
    finally:
        _p.stop()


@with_setup(my_setup)
def test_internal_metrics_disabled_raises():
    """internal_metrics=True raises cherrypy.HTTPError(400) when http_metrics_enabled is False."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        with _patch_resolved_target(gen):
            with mock.patch('source.confgenerator.analytics') as mock_analytics:
                mock_analytics.http_metrics_enabled = False
                try:
                    gen.build_scrape_jobs(internal_metrics=True)
                    assert False, 'Expected cherrypy.HTTPError'
                except cherrypy.HTTPError as e:
                    assert e.status == 400
    finally:
        _p.stop()


@with_setup(my_setup)
def test_invalid_internal_metrics_param():
    """_parse_params raises HTTPError 400 for an invalid internal_metrics value."""
    import cherrypy
    gen, _p = _make_generator()
    try:
        try:
            gen._parse_params({'internal_metrics': 'yes'})
            assert False, 'Expected HTTPError'
        except cherrypy.HTTPError as e:
            assert e.status == 400
    finally:
        _p.stop()


@with_setup(my_setup)
def test_internal_jobs_share_common_settings():
    """Internal jobs have the same scheme, TLS and auth as sensor jobs."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        with _patch_resolved_target(gen):
            with mock.patch('source.confgenerator.analytics') as mock_analytics:
                mock_analytics.http_metrics_enabled = True
                jobs = gen.build_scrape_jobs(internal_metrics=True)
            sensor_job = next(j for j in jobs if j['job_name'] == 'GPFSFilesystem')
            for base_name in INTERNAL_METRICS_JOBS:
                internal_job = next(j for j in jobs if j['job_name'] == base_name)
                assert internal_job['scheme'] == sensor_job['scheme']
                assert internal_job.get('tls_config') == sensor_job.get('tls_config')
                assert internal_job.get('basic_auth') == sensor_job.get('basic_auth')
                assert internal_job['static_configs'] == sensor_job['static_configs']
    finally:
        _p.stop()


# ---------------------------------------------------------------------------
# target param
# ---------------------------------------------------------------------------

@with_setup(my_setup)
def test_target_host_and_port_overrides_auto():
    """target=host:port overrides auto-detection entirely."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        jobs = gen.build_scrape_jobs(target_param='192.168.1.99:9999')
        assert jobs[0]['static_configs'][0]['targets'] == ['192.168.1.99:9999']
    finally:
        _p.stop()


@with_setup(my_setup)
def test_target_host_only_uses_configured_port():
    """target=host (no port) uses the configured prometheus port."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        jobs = gen.build_scrape_jobs(target_param='192.168.1.99')
        assert jobs[0]['static_configs'][0]['targets'] == ['192.168.1.99:9250']
    finally:
        _p.stop()


@with_setup(my_setup)
def test_target_hostname_accepted():
    """target=hostname (no port) is accepted and uses the configured prometheus port."""
    gen, _p = _make_generator(
        endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        jobs = gen.build_scrape_jobs(target_param='mybridge.example.com')
        assert jobs[0]['static_configs'][0]['targets'] == ['mybridge.example.com:9250']
    finally:
        _p.stop()


@with_setup(my_setup)
def test_target_invalid_port_raises():
    """_parse_params raises HTTPError 400 when target port is not a number."""
    import cherrypy
    gen, _p = _make_generator()
    try:
        try:
            gen._parse_params({'target': 'host:notaport'})
            assert False, 'Expected HTTPError'
        except cherrypy.HTTPError as e:
            assert e.status == 400
    finally:
        _p.stop()


@with_setup(my_setup)
def test_target_empty_host_raises():
    """_parse_params raises HTTPError 400 when target host is empty."""
    import cherrypy
    gen, _p = _make_generator()
    try:
        try:
            gen._parse_params({'target': ':9250'})
            assert False, 'Expected HTTPError'
        except cherrypy.HTTPError as e:
            assert e.status == 400
    finally:
        _p.stop()


@with_setup(my_setup)
def test_no_target_uses_detect_outbound_ip_on_wildcard():
    """When promBindIp is a wildcard, outbound-route detection is used."""
    wildcard_attr = dict(attr, promBindIp='0.0.0.0')
    gen, _p = _make_generator(attr_override=wildcard_attr,
                              endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        with mock.patch.object(gen, '_detect_outbound_ip', return_value='10.1.2.3') as mock_detect:
            jobs = gen.build_scrape_jobs()
            mock_detect.assert_called_once()
            assert jobs[0]['static_configs'][0]['targets'] == ['10.1.2.3:9250']
    finally:
        _p.stop()


@with_setup(my_setup)
def test_no_target_uses_prombindip_when_not_wildcard():
    """When promBindIp is a real IP, it is used directly without network calls."""
    bound_attr = dict(attr, promBindIp='172.16.0.5')
    gen, _p = _make_generator(attr_override=bound_attr,
                              endpoints_override={'/metrics_gpfs_filesystem': 'GPFSFilesystem'})
    try:
        with mock.patch.object(gen, '_detect_outbound_ip') as mock_detect:
            jobs = gen.build_scrape_jobs()
            mock_detect.assert_not_called()
            assert jobs[0]['static_configs'][0]['targets'] == ['172.16.0.5:9250']
    finally:
        _p.stop()


@with_setup(my_setup)
def test_detect_outbound_ip_returns_none_on_error():
    """_detect_outbound_ip returns None when the socket connect fails."""
    gen, _p = _make_generator()
    try:
        with mock.patch('socket.socket') as mock_socket_cls:
            mock_socket_cls.return_value.__enter__.return_value.connect.side_effect = OSError('unreachable')
            result = gen._detect_outbound_ip()
            assert result is None
    finally:
        _p.stop()


@with_setup(my_setup)
def test_resolve_target_falls_back_to_any_available_when_outbound_fails():
    """When outbound detection fails, falls back to hostname resolution."""
    wildcard_attr = dict(attr, promBindIp='0.0.0.0')
    gen, _p = _make_generator(attr_override=wildcard_attr)
    try:
        with mock.patch.object(gen, '_detect_outbound_ip', return_value=None):
            with mock.patch('socket.getfqdn', return_value='myhost.local'):
                with mock.patch('socket.gethostbyname_ex', return_value=('myhost.local', [], ['192.168.0.1'])):
                    host, port = gen._resolve_target('')
                    assert host == '192.168.0.1'
                    assert port == '9250'
    finally:
        _p.stop()


# ---------------------------------------------------------------------------
# path param — write config to disk
# ---------------------------------------------------------------------------

@with_setup(my_setup)
def test_write_to_path_directory_creates_scrape_config_file():
    """_write_to_path with an existing dir and default filename writes scrape_configs.yml inside it."""
    gen, _p = _make_generator()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen._write_to_path('content', tmpdir)
            dest = os.path.join(tmpdir, 'scrape_configs.yml')
            assert os.path.isfile(dest)
            with open(dest) as f:
                assert f.read() == 'content'
    finally:
        _p.stop()


@with_setup(my_setup)
def test_write_to_path_directory_creates_prometheus_yml():
    """_write_to_path with an existing dir and default_filename='prometheus.yml' writes prometheus.yml inside it."""
    gen, _p = _make_generator()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            gen._write_to_path('content', tmpdir, default_filename='prometheus.yml')
            dest = os.path.join(tmpdir, 'prometheus.yml')
            assert os.path.isfile(dest)
            with open(dest) as f:
                assert f.read() == 'content'
    finally:
        _p.stop()


@with_setup(my_setup)
def test_write_to_path_explicit_file():
    """_write_to_path with an explicit file path writes to that exact file."""
    gen, _p = _make_generator()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, 'custom.yml')
            gen._write_to_path('hello', dest)
            assert os.path.isfile(dest)
            with open(dest) as f:
                assert f.read() == 'hello'
    finally:
        _p.stop()


@with_setup(my_setup)
def test_write_to_path_relative_path_raises_400():
    """_write_to_path raises cherrypy.HTTPError(400) for a relative path."""
    gen, _p = _make_generator()
    try:
        try:
            gen._write_to_path('x', 'relative/path.yml')
            assert False, 'Expected cherrypy.HTTPError'
        except cherrypy.HTTPError as e:
            assert e.status == 400
    finally:
        _p.stop()


@with_setup(my_setup)
def test_write_to_path_nonexistent_parent_raises_400():
    """_write_to_path raises cherrypy.HTTPError(400) when parent dir does not exist."""
    gen, _p = _make_generator()
    try:
        try:
            gen._write_to_path('x', '/nonexistent_dir_xyz/scrape.yml')
            assert False, 'Expected cherrypy.HTTPError'
        except cherrypy.HTTPError as e:
            assert e.status == 400
    finally:
        _p.stop()


@with_setup(my_setup)
def test_write_to_path_io_error_raises_500():
    """_write_to_path raises cherrypy.HTTPError(500) when the file cannot be written."""
    gen, _p = _make_generator()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = os.path.join(tmpdir, 'out.yml')
            with mock.patch('builtins.open', side_effect=OSError('disk full')):
                try:
                    gen._write_to_path('x', dest)
                    assert False, 'Expected cherrypy.HTTPError'
                except cherrypy.HTTPError as e:
                    assert e.status == 500
    finally:
        _p.stop()


@with_setup(my_setup)
def test_parse_params_returns_path_param():
    """_parse_params extracts the path query parameter."""
    gen, _p = _make_generator()
    try:
        _, _, _, path = gen._parse_params({'path': '/tmp/scrape.yml'})
        assert path == '/tmp/scrape.yml'
    finally:
        _p.stop()


@with_setup(my_setup)
def test_parse_params_empty_path_by_default():
    """_parse_params returns empty string for path when not supplied."""
    gen, _p = _make_generator()
    try:
        _, _, _, path = gen._parse_params({})
        assert path == ''
    finally:
        _p.stop()
