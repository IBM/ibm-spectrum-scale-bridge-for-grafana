"""Tests for ConfigApi._nested_view() — the data returned by GET /config.

Uses tests/test_data/custom_with_basic_auth.ini which has:
  - password = TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg==  (live, must be hidden)
  - prometheus = 9250                              (live, must be shown)
  - port commented-out                             (must show as "disabled")
"""
import os
from unittest.mock import MagicMock
from nose2.tools.decorators import with_setup

from source.configapi import ConfigApi, HIDDEN_KEYS


def my_setup():
    global api
    path = os.getcwd()
    template = os.path.join(path, 'source', 'config.ini')
    custom = os.path.join(path, 'tests', 'test_data', 'custom_with_basic_auth.ini')
    logger = MagicMock()
    logger.trace = logger.details = logger.info = logger.error = logger.warning = MagicMock()
    cm = MagicMock()
    cm.customFile = custom
    cm.DEFAULT_CUSTOM_CONFIG = '/nonexistent/config.ini'
    cm.templateFile = template
    brFullConfig = {
        'enabled': True, 'username': 'scale_admin',
        'password': 'TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg==',
        'prometheus': 9250, 'promBindIp': '0.0.0.0', 'rawCounters': True,
        'protocol': 'http', 'opentsdbBindIp': '0.0.0.0',
        'server': 'localhost', 'serverPort': 9980, 'retryDelay': 60,
        'apiKeyName': 'scale_grafana', 'caCertPath': False,
        'includeDiskData': False,
        'logPath': '/var/log/ibm_bridge_for_grafana', 'logLevel': 15,
        'logFile': 'zserver.log', 'cpAccessLog': 'on', 'cpAccessLogBackups': 10,
    }
    api = ConfigApi(logger, brFullConfig, cm)


@with_setup(my_setup)
def test_case01():
    """password is live in the file but must never appear in the GET response."""
    view = api._nested_view()
    basic_auth = view.get('basic_auth', {})
    assert 'password' not in basic_auth, \
        f"password must not appear in basic_auth: {basic_auth}"


@with_setup(my_setup)
def test_case02():
    """username is a non-secret live key — must appear with correct value."""
    view = api._nested_view()
    assert view['basic_auth']['username'] == 'scale_admin'


@with_setup(my_setup)
def test_case03():
    """enabled is a non-secret live key — must appear."""
    view = api._nested_view()
    assert view['basic_auth']['enabled'] is True


@with_setup(my_setup)
def test_case04():
    """prometheus = 9250 is live in the custom file — must appear."""
    view = api._nested_view()
    assert view['prometheues_exporter_plugin']['prometheus'] == 9250


@with_setup(my_setup)
def test_case05():
    """port is commented-out in the custom file — must appear as 'disabled'."""
    view = api._nested_view()
    opentsdb = view.get('opentsdb_plugin', {})
    assert 'port' in opentsdb, f"port missing from opentsdb_plugin: {opentsdb}"
    assert opentsdb['port'] == 'disabled', \
        f"expected 'disabled', got {opentsdb['port']!r}"


@with_setup(my_setup)
def test_case06():
    """All INI sections must be present in the response."""
    view = api._nested_view()
    expected = {'basic_auth', 'connection', 'logging', 'opentsdb_plugin',
                'prometheues_exporter_plugin', 'query', 'server', 'tls'}
    assert expected.issubset(view.keys()), \
        f"missing sections: {expected - view.keys()}"


@with_setup(my_setup)
def test_case07():
    """password, apiKeyValue, configFile must not appear in any section."""
    view = api._nested_view()
    for section, keys in view.items():
        leaked = HIDDEN_KEYS & keys.keys()
        assert not leaked, \
            f"hidden key(s) {leaked} leaked into section [{section}]"


@with_setup(my_setup)
def test_case08():
    """basic_auth must contain exactly 'enabled' and 'username'.
    'password' is the only other documented key but it is in HIDDEN_KEYS
    and must be absent regardless of whether it is live in the file."""
    view = api._nested_view()
    basic_auth = view.get('basic_auth', {})
    assert set(basic_auth.keys()) == {'enabled', 'username'}, \
        f"unexpected keys in basic_auth: {set(basic_auth.keys())}"


@with_setup(my_setup)
def test_case09():
    """_section_to_keys['basic_auth'] must contain exactly the keys documented
    in the INI schema: 'enabled', 'username', 'password'.
    No garbage keys (e.g. base64 strings) must be present."""
    basic_auth_keys = set(api._section_to_keys.get('basic_auth', []))
    assert basic_auth_keys == {'enabled', 'username', 'password'}, \
        f"unexpected keys in _section_to_keys['basic_auth']: {basic_auth_keys}"
