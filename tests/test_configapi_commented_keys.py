import os
import tempfile
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'source'))

from configapi import _parse_commented_keys


def _write_ini(content):
    """Write *content* to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False)
    f.write(content)
    f.close()
    return f.name


def test_template_only_extracts_commented_keys():
    """Commented-out keys in a single file are returned with their section."""
    path = _write_ini(
        "[basic_auth]\n"
        "enabled = True\n"
        "# password = TXlWZXJ5\n"
        "[tls]\n"
        "# tlsKeyPath = /etc/certs\n"
        "# tlsKeyFile = key.pem\n"
    )
    try:
        result = _parse_commented_keys([path])
        assert result['password'] == 'basic_auth'
        assert result['tlsKeyPath'] == 'tls'
        assert result['tlsKeyFile'] == 'tls'
        assert 'enabled' not in result          # live key, not commented
    finally:
        os.unlink(path)


def test_live_keys_not_captured():
    """Live (uncommented) keys must not appear in the result."""
    path = _write_ini(
        "[server]\n"
        "server = localhost\n"
        "serverPort = 9980\n"
        "# apiKeyValue = secret\n"
    )
    try:
        result = _parse_commented_keys([path])
        assert 'server' not in result
        assert 'serverPort' not in result
        assert result['apiKeyValue'] == 'server'
    finally:
        os.unlink(path)


def test_custom_file_overrides_template():
    """When a key is commented-out in both files, the custom file wins
    (last-file-wins — custom file is always appended second)."""
    template = _write_ini(
        "[opentsdb_plugin]\n"
        "# port = 4242\n"
    )
    custom = _write_ini(
        "[connection]\n"          # key re-commented under a different section
        "# port = 8443\n"
    )
    try:
        result = _parse_commented_keys([template, custom])
        assert result['port'] == 'connection'   # custom wins
    finally:
        os.unlink(template)
        os.unlink(custom)


def test_key_only_in_template_not_in_custom():
    """A key commented-out only in the template (absent from custom) still
    maps to the template section."""
    template = _write_ini(
        "[tls]\n"
        "# tlsCertFile = cert.pem\n"
    )
    custom = _write_ini(
        "[server]\n"
        "server = myhost\n"
    )
    try:
        result = _parse_commented_keys([template, custom])
        assert result['tlsCertFile'] == 'tls'
    finally:
        os.unlink(template)
        os.unlink(custom)


def test_missing_file_is_silently_skipped():
    """An OSError on a non-existent file must not raise; other files are
    still processed."""
    path = _write_ini(
        "[basic_auth]\n"
        "# password = abc\n"
    )
    try:
        result = _parse_commented_keys(['/nonexistent/file.ini', path])
        assert result['password'] == 'basic_auth'
    finally:
        os.unlink(path)


def test_empty_list_returns_empty_dict():
    assert _parse_commented_keys([]) == {}
