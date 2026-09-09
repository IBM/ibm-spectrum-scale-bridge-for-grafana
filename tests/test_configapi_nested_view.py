"""Tests for ConfigApi._nested_view() — the data returned by GET /config.

Uses tests/test_data/custom_with_basic_auth.ini which has:
  - password = TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg==  (live, must be hidden)
  - prometheus = 9250                              (live, must be shown)
  - port commented-out                             (must show as "disabled")
"""
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from configapi import ConfigApi

SOURCE_DIR = os.path.join(os.path.dirname(__file__), '..', 'source')
TEMPLATE = os.path.join(SOURCE_DIR, 'config.ini')
CUSTOM_WITH_AUTH = os.path.join(
    os.path.dirname(__file__), 'test_data', 'custom_with_basic_auth.ini')


def _make_api():
    logger = MagicMock()
    logger.trace = logger.details = logger.info = logger.error = logger.warning = MagicMock()
    cm = MagicMock()
    cm.customFile = CUSTOM_WITH_AUTH
    cm.DEFAULT_CUSTOM_CONFIG = '/nonexistent/config.ini'
    cm.templateFile = TEMPLATE
    # brFullConfig mirrors what the bridge builds from custom_with_basic_auth.ini
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
    return ConfigApi(logger, brFullConfig, cm)


def test_password_not_in_response():
    """password is live in the file but must never appear in the GET response."""
    view = _make_api()._nested_view()
    basic_auth = view.get('basic_auth', {})
    assert 'password' not in basic_auth, \
        f"password must not appear in basic_auth: {basic_auth}"


def test_username_shown():
    """username is a non-secret live key — must appear with correct value."""
    view = _make_api()._nested_view()
    assert view['basic_auth']['username'] == 'scale_admin'


def test_enabled_shown():
    """enabled is a non-secret live key — must appear."""
    view = _make_api()._nested_view()
    assert view['basic_auth']['enabled'] is True


def test_prometheus_shown_with_live_value():
    """prometheus = 9250 is live in the custom file — must appear."""
    view = _make_api()._nested_view()
    assert view['prometheues_exporter_plugin']['prometheus'] == 9250


def test_port_shown_as_disabled():
    """port is commented-out in the custom file — must appear as 'disabled'."""
    view = _make_api()._nested_view()
    opentsdb = view.get('opentsdb_plugin', {})
    assert 'port' in opentsdb, f"port missing from opentsdb_plugin: {opentsdb}"
    assert opentsdb['port'] == 'disabled', \
        f"expected 'disabled', got {opentsdb['port']!r}"


def test_all_expected_sections_present():
    """All INI sections must be present in the response."""
    view = _make_api()._nested_view()
    expected = {'basic_auth', 'connection', 'logging', 'opentsdb_plugin',
                'prometheues_exporter_plugin', 'query', 'server', 'tls'}
    assert expected.issubset(view.keys()), \
        f"missing sections: {expected - view.keys()}"


def test_no_hidden_keys_anywhere():
    """password, apiKeyValue, configFile must not appear in any section."""
    from configapi import HIDDEN_KEYS
    view = _make_api()._nested_view()
    for section, keys in view.items():
        leaked = HIDDEN_KEYS & keys.keys()
        assert not leaked, \
            f"hidden key(s) {leaked} leaked into section [{section}]"


def test_basic_auth_section_contains_only_expected_keys():
    """basic_auth must contain exactly 'enabled' and 'username'.
    'password' is the only other documented key but it is in HIDDEN_KEYS
    and must be absent regardless of whether it is live in the file."""
    view = _make_api()._nested_view()
    basic_auth = view.get('basic_auth', {})
    assert set(basic_auth.keys()) == {'enabled', 'username'}, \
        f"unexpected keys in basic_auth: {set(basic_auth.keys())}"

def test_section_to_keys_basic_auth_contains_only_expected_keys():
    """_section_to_keys['basic_auth'] must contain exactly the keys documented
    in the INI schema: 'enabled', 'username', 'password'.
    No garbage keys (e.g. base64 strings) must be present."""
    api = _make_api()
    basic_auth_keys = set(api._section_to_keys.get('basic_auth', []))
    assert basic_auth_keys == {'enabled', 'username', 'password'}, \
        f"unexpected keys in _section_to_keys['basic_auth']: {basic_auth_keys}"
