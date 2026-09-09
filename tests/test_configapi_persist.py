"""Tests for _persist() null-removal and _apply_update() restart-pending
persistence introduced to support "disabling" optional keys via the API.
"""
import os
import tempfile
import configparser
from unittest.mock import MagicMock
from source.configapi import ConfigApi
from source.messages import MSG


def _make_config_api(ini_content):
    """Return a ConfigApi instance backed by a real temp custom file."""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False)
    f.write(ini_content)
    f.close()

    logger = MagicMock()
    logger.trace = MagicMock()
    logger.details = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()

    cm = MagicMock()
    cm.customFile = f.name
    cm.DEFAULT_CUSTOM_CONFIG = '/nonexistent/config.ini'

    # Minimal template path — point at the real template so _build_section_maps works
    source_dir = os.path.join(os.path.dirname(__file__), '..', 'source')
    cm.templateFile = os.path.join(source_dir, 'config.ini')

    # Minimal brFullConfig with the keys used in tests
    brFullConfig = {'port': 4242, 'rawCounters': True, 'prometheus': None,
                    'logLevel': 15, 'includeDiskData': False, 'retryDelay': 60}

    api = ConfigApi(logger, brFullConfig, cm)
    return api, f.name


def _read_ini(path):
    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    cfg.read(path)
    return cfg


def test_persist_null_removes_existing_key():
    """Passing None for a key that exists in the file removes it."""
    api, tmp = _make_config_api(
        "[opentsdb_plugin]\nport = 4242\n"
    )
    try:
        api._persist({'port': None})
        cfg = _read_ini(tmp)
        assert not cfg.has_option('opentsdb_plugin', 'port')
    finally:
        os.unlink(tmp)


def test_persist_null_on_absent_key_does_not_raise():
    """Passing None for a key not in the file is a safe no-op."""
    api, tmp = _make_config_api("[server]\nserver = localhost\n")
    try:
        api._persist({'port': None})   # port not in file — must not raise
        cfg = _read_ini(tmp)
        assert not cfg.has_option('opentsdb_plugin', 'port')
    finally:
        os.unlink(tmp)


def test_persist_value_writes_key_to_correct_section():
    """Passing a real value writes key = value under the correct section."""
    api, tmp = _make_config_api("[server]\nserver = localhost\n")
    try:
        api._persist({'port': 4242})
        cfg = _read_ini(tmp)
        assert cfg.has_option('opentsdb_plugin', 'port')
        assert cfg.get('opentsdb_plugin', 'port') == '4242'
    finally:
        os.unlink(tmp)


def test_persist_mixed_set_and_remove():
    """In one call: one key is set, another is removed."""
    api, tmp = _make_config_api(
        "[opentsdb_plugin]\nport = 4242\n"
        "[prometheues_exporter_plugin]\nrawCounters = True\n"
    )
    try:
        api._persist({'port': None, 'rawCounters': False})
        cfg = _read_ini(tmp)
        assert not cfg.has_option('opentsdb_plugin', 'port')
        assert cfg.get('prometheues_exporter_plugin', 'rawCounters') == 'False'
    finally:
        os.unlink(tmp)


def test_persist_moves_key_from_wrong_section_to_correct_one():
    """If a key was previously written to the wrong section (e.g. 'server'
    instead of 'opentsdb_plugin'), _persist() evicts it from all sections
    and re-writes it under the correct one."""
    api, tmp = _make_config_api(
        "[server]\nport = 4242\n"   # misplaced — should be opentsdb_plugin
    )
    try:
        api._persist({'port': 4242})
        cfg = _read_ini(tmp)
        assert not cfg.has_option('server', 'port'), \
            "port still present in wrong section [server]"
        assert cfg.has_option('opentsdb_plugin', 'port'), \
            "port not moved to correct section [opentsdb_plugin]"
        assert cfg.get('opentsdb_plugin', 'port') == '4242'
    finally:
        os.unlink(tmp)


def test_persist_null_removes_key_from_wrong_section():
    """A null persist also evicts the key even when it sits in the wrong
    section — the real-system scenario where port was stored under [server]."""
    api, tmp = _make_config_api(
        "[server]\nport = 4242\n"
    )
    try:
        api._persist({'port': None})
        cfg = _read_ini(tmp)
        assert not cfg.has_option('server', 'port'), \
            "port still in [server] after null persist"
        assert not cfg.has_option('opentsdb_plugin', 'port'), \
            "port unexpectedly appeared in [opentsdb_plugin]"
    finally:
        os.unlink(tmp)


def test_apply_update_restart_key_is_pending_and_persisted():
    """A RESTART_REQUIRED_KEY goes into restart_required (not rejected) and is persisted."""
    api, tmp = _make_config_api(
        "[opentsdb_plugin]\nport = 4242\n"
    )
    try:
        updated, rejected, restart_required, persisted = api._apply_update({'port': 9999})
        assert 'port' not in updated
        assert 'port' not in rejected
        assert 'port' in restart_required
        assert restart_required['port'] == MSG['ConfigApiRestartRequired']
        assert persisted is True
        cfg = _read_ini(tmp)
        assert cfg.get('opentsdb_plugin', 'port') == '9999'
    finally:
        os.unlink(tmp)


def test_apply_update_restart_key_null_removes_from_file():
    """Sending null for a RESTART_REQUIRED_KEY removes it from the file."""
    api, tmp = _make_config_api(
        "[opentsdb_plugin]\nport = 4242\n"
    )
    try:
        updated, rejected, restart_required, persisted = api._apply_update({'port': None})
        assert 'port' not in updated
        assert 'port' not in rejected
        assert 'port' in restart_required
        assert persisted is True
        cfg = _read_ini(tmp)
        assert not cfg.has_option('opentsdb_plugin', 'port')
    finally:
        os.unlink(tmp)


def test_apply_update_writable_key_not_affected_by_restart_logic():
    """A WRITABLE_KEY is still applied live and persisted normally."""
    api, tmp = _make_config_api(
        "[prometheues_exporter_plugin]\nrawCounters = True\n"
    )
    try:
        updated, rejected, restart_required, persisted = api._apply_update({'rawCounters': False})
        assert updated == {'rawCounters': False}
        assert 'rawCounters' not in rejected
        assert 'rawCounters' not in restart_required
        assert persisted is True
        cfg = _read_ini(tmp)
        assert cfg.get('prometheues_exporter_plugin', 'rawCounters') == 'False'
    finally:
        os.unlink(tmp)


def test_apply_update_restart_and_writable_together():
    """Mixed body: writable key updated live, restart key in restart_required."""
    api, tmp = _make_config_api(
        "[opentsdb_plugin]\nport = 4242\n"
        "[prometheues_exporter_plugin]\nrawCounters = True\n"
    )
    try:
        updated, rejected, restart_required, persisted = api._apply_update(
            {'port': 8080, 'rawCounters': False}
        )
        assert updated == {'rawCounters': False}
        assert 'port' not in rejected
        assert 'port' in restart_required
        assert persisted is True
        cfg = _read_ini(tmp)
        assert cfg.get('opentsdb_plugin', 'port') == '8080'
        assert cfg.get('prometheues_exporter_plugin', 'rawCounters') == 'False'
    finally:
        os.unlink(tmp)


def _make_config_api_no_custom():
    """ConfigApi with no custom file and a non-existent DEFAULT_CUSTOM_CONFIG."""
    logger = MagicMock()
    logger.trace = logger.details = logger.info = logger.error = logger.warning = MagicMock()
    source_dir = os.path.join(os.path.dirname(__file__), '..', 'source')
    template = os.path.join(source_dir, 'config.ini')
    cm = MagicMock()
    cm.customFile = None
    cm.DEFAULT_CUSTOM_CONFIG = '/nonexistent/config.ini'
    cm.templateFile = template
    brFullConfig = {'rawCounters': True, 'logLevel': 15,
                    'includeDiskData': False, 'retryDelay': 60}
    return ConfigApi(logger, brFullConfig, cm)


def test_persist_returns_no_target_message_when_no_custom_file():
    """_persist() returns the ConfigApiNoTarget message string when there is
    no custom file and DEFAULT_CUSTOM_CONFIG does not exist."""
    api = _make_config_api_no_custom()
    result = api._persist({'rawCounters': False})
    assert result == MSG['ConfigApiNoTarget'], f"unexpected: {result!r}"


def test_persist_returns_template_blocked_message_when_template_passed_as_f():
    """_persist() returns ConfigApiTemplateWriteBlocked when customFile points
    at the template — the real-system scenario of passing --configFile source/config.ini."""
    logger = MagicMock()
    logger.trace = logger.details = logger.info = logger.error = logger.warning = MagicMock()
    source_dir = os.path.join(os.path.dirname(__file__), '..', 'source')
    template = os.path.join(source_dir, 'config.ini')
    cm = MagicMock()
    cm.customFile = template      # template passed as -F  ← the bug scenario
    cm.DEFAULT_CUSTOM_CONFIG = '/nonexistent/config.ini'
    cm.templateFile = template
    brFullConfig = {'rawCounters': True, 'logLevel': 15,
                    'includeDiskData': False, 'retryDelay': 60}
    api = ConfigApi(logger, brFullConfig, cm)
    result = api._persist({'rawCounters': False})
    assert result == MSG['ConfigApiTemplateWriteBlocked'], f"unexpected: {result!r}"


def test_apply_update_persisted_contains_message_when_template_is_target():
    """The persisted field in the _apply_update response carries the
    ConfigApiTemplateWriteBlocked message when the template is the write target."""
    logger = MagicMock()
    logger.trace = logger.details = logger.info = logger.error = logger.warning = MagicMock()
    source_dir = os.path.join(os.path.dirname(__file__), '..', 'source')
    template = os.path.join(source_dir, 'config.ini')
    cm = MagicMock()
    cm.customFile = template
    cm.DEFAULT_CUSTOM_CONFIG = '/nonexistent/config.ini'
    cm.templateFile = template
    brFullConfig = {'rawCounters': True, 'logLevel': 15,
                    'includeDiskData': False, 'retryDelay': 60,
                    'port': None, 'prometheus': None}
    api = ConfigApi(logger, brFullConfig, cm)
    _, rejected, restart_required, persisted = api._apply_update({'port': 4242})
    assert 'port' not in rejected
    assert 'port' in restart_required
    assert restart_required['port'] == MSG['ConfigApiRestartRequired']
    assert persisted == MSG['ConfigApiTemplateWriteBlocked']
