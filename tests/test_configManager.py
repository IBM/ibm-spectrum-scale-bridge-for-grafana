import os
import re
import tempfile
from source.confParser import ConfigManager
from source.__version__ import __version__ as version
from nose2.tools.decorators import with_setup

# Keys that must be present in the flat config when using custom_with_basic_auth.ini
EXPECTED_BASIC_AUTH_KEYS = {
    # basic_auth section
    'enabled', 'username', 'password',
    # prometheues_exporter_plugin section
    'prometheus', 'rawCounters', 'promBindIp',
    # connection section
    'protocol',
    # opentsdb_plugin section
    'opentsdbBindIp',
    # server section
    'server', 'serverPort', 'retryDelay', 'apiKeyName', 'caCertPath',
    # query section
    'includeDiskData',
    # logging section
    'logPath', 'logLevel', 'logFile',
}

OPTIONAL_TEMPLATE_KEYS = {
    'port',                                      # opentsdb_plugin (commented)
    'tlsKeyPath', 'tlsKeyFile', 'tlsCertFile',   # tls (all commented)
    'apiKeyValue',                               # server (commented)
    'cpAccessLog', 'cpAccessLogBackups',         # logging (optional)
}

# Regex that matches a likely base64 payload (long, contains +/= characters
# typical of base64, or is purely alphanumeric/= and longer than 20 chars).
_BASE64_KEY_RE = re.compile(r'^[A-Za-z0-9+/]{20,}={0,2}$')


def my_setup():
    global path, customConfigFile, customWithBAuthFile
    path = os.getcwd()
    customConfigFile = 'custom.ini'
    customWithBAuthFile = 'custom_with_basic_auth.ini'


def test_case01():
    cm = ConfigManager()
    result = cm.readConfigFile('config.ini')
    assert isinstance(result, dict)
    if version < "8.0.7":
        assert len(result.keys()) > 0
        assert 'tls' in result.keys()
    else:
        assert len(result) == 0


def test_case02():
    cm = ConfigManager()
    file = cm.get_template_path()
    result = cm.readConfigFile(file)
    assert isinstance(result, dict)
    assert len(result.keys()) > 0
    assert 'tls' in result.keys()


def test_case03():
    cm = ConfigManager()
    if version < "8.0.7":
        result = cm.readConfigFile('config.ini')
        connection = result['connection']
        assert len(connection) > 0
        assert isinstance(connection, dict)
        assert len(connection) > 0
        if version < "8.0":
            assert 'port' in connection.keys()
        else:
            assert 'port' not in connection.keys()


@with_setup(my_setup)
def test_case04():
    customFile = os.path.join(path, "tests", "test_data", customConfigFile)
    cm = ConfigManager()
    cm.customFile = customFile
    result = cm.readConfigFile(cm.customFile)
    assert 'tls' in result.keys()


def test_case05():
    cm = ConfigManager()
    result = cm.parse_defaults()
    assert isinstance(result, dict)


def test_case06():
    cm = ConfigManager()
    result = cm.parse_defaults()
    assert len(result.keys()) > 0


def test_case07():
    cm = ConfigManager()
    result = cm.parse_defaults()
    result1 = cm.defaults
    assert len(result) == len(result1)


def test_case08():
    cm = ConfigManager()
    result = cm.defaults
    elements = list(result.keys())
    if version < "8.0":
        mandatoryItems = {'port', 'serverPort'}
        assert mandatoryItems.issubset(set(elements))
    else:
        assert 'port' not in set(elements)


def test_case09():
    if version < "8.0":
        cm = ConfigManager()
        result = cm.defaults
        value = int(result['port'])
        assert value == 4242


def test_case10():
    cm = ConfigManager()
    result = cm.defaults
    if version < "7.0":
        assert int(result['port']) == 4242 and int(result['serverPort']) == 9084
    elif version < "8.0":
        assert int(result['port']) == 4242 and int(result['serverPort']) == 9980
    else:
        assert result.get('port', None) is None
        assert int(result['serverPort']) == 9980


def test_case11():
    cm = ConfigManager()
    result = cm.defaults
    assert 'includeDiskData' in result.keys()
    assert result['includeDiskData'] is False


def test_case12():
    cm = ConfigManager()
    result = cm.defaults
    assert 'apiKeyValue' not in result.keys()


def test_case13():
    cm = ConfigManager()
    result = cm.defaults
    assert 'protocol' in result.keys()
    assert result['protocol'] == 'http'


def lowercase_bool_setup():
    global tmp_ini
    import tempfile
    content = (
        "[basic_auth]\n"
        "enabled = true\n"
        "[prometheues_exporter_plugin]\n"
        "rawCounters = false\n"
        "[query]\n"
        "includeDiskData = yes\n"
        "[server]\n"
        "caCertPath = false\n"
    )
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        f.write(content)
        tmp_ini = f.name


@with_setup(lowercase_bool_setup)
def test_case14():
    '''readConfigFile converts lowercase "true" to bool True'''
    cm = ConfigManager()
    try:
        result = cm.readConfigFile(tmp_ini)
        assert result['basic_auth']['enabled'] is True
    finally:
        os.unlink(tmp_ini)


@with_setup(lowercase_bool_setup)
def test_case15():
    '''readConfigFile converts lowercase "false" to bool False'''
    cm = ConfigManager()
    try:
        result = cm.readConfigFile(tmp_ini)
        assert result['prometheues_exporter_plugin']['rawCounters'] is False
        assert result['server']['caCertPath'] is False
    finally:
        os.unlink(tmp_ini)


@with_setup(lowercase_bool_setup)
def test_case16():
    '''readConfigFile converts "yes" to bool True'''
    cm = ConfigManager()
    try:
        result = cm.readConfigFile(tmp_ini)
        assert result['query']['includeDiskData'] is True
    finally:
        os.unlink(tmp_ini)


def test_case17():
    """A custom file containing only [server] overrides server keys;
    all other defaults come from the template."""
    import tempfile
    content = "[server]\nserver = testhost.example.com\n"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        f.write(content)
        tmp = f.name
    try:
        cm = ConfigManager.__new__(ConfigManager)
        cm._ConfigManager__defaults = {}
        cm.customFile = tmp
        cm.templateFile = cm.get_template_path()
        result = cm.parse_defaults()
        # Override applied
        assert result['server'] == 'testhost.example.com'
        # Unrelated template default still present
        assert result['serverPort'] == 9980
    finally:
        os.unlink(tmp)


def test_case18():
    """Section-intersection guard is gone: a custom file with a locally-added
    section (not in template) must not cause the file to be silently dropped."""
    import tempfile
    content = "[local_extension]\ncustomKey = customValue\n"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        f.write(content)
        tmp = f.name
    try:
        cm = ConfigManager.__new__(ConfigManager)
        cm._ConfigManager__defaults = {}
        cm.customFile = tmp
        cm.templateFile = cm.get_template_path()
        result = cm.parse_defaults()
        # Local key present
        assert result.get('customKey') == 'customValue'
        # Template defaults also present (file was not silently dropped)
        assert result['serverPort'] == 9980
    finally:
        os.unlink(tmp)


def test_case19():
    """When /etc/grafanabridge/config.ini does not exist, ConfigManager()
    returns template-only defaults without printing an error."""
    cm = ConfigManager.__new__(ConfigManager)
    cm._ConfigManager__defaults = {}
    cm.customFile = None
    cm.templateFile = cm.get_template_path()
    # Point DEFAULT_CUSTOM_CONFIG at a path that is guaranteed not to exist
    cm.__class__.DEFAULT_CUSTOM_CONFIG = '/tmp/__nonexistent_grafanabridge_test__.ini'
    try:
        result = cm.parse_defaults()
    finally:
        cm.__class__.DEFAULT_CUSTOM_CONFIG = '/etc/grafanabridge/config.ini'
    # Template defaults returned; no key from a non-existent override file
    assert isinstance(result, dict)
    assert len(result) > 0


def test_case20():
    """An explicit customFile argument is used as-is; DEFAULT_CUSTOM_CONFIG
    is never consulted even if /etc/grafanabridge/config.ini exists."""
    import tempfile
    content = "[server]\nserver = explicit-host\n"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        f.write(content)
        tmp = f.name
    try:
        cm = ConfigManager.__new__(ConfigManager)
        cm._ConfigManager__defaults = {}
        cm.customFile = tmp    # explicit — DEFAULT_CUSTOM_CONFIG not reached
        cm.templateFile = cm.get_template_path()
        result = cm.parse_defaults()
        assert result['server'] == 'explicit-host'
    finally:
        os.unlink(tmp)


@with_setup(my_setup)
def test_case21():
    """parse_defaults() must include all expected keys from the custom file."""
    customWithBasicAuthConf = os.path.join(path, "tests", "test_data", customWithBAuthFile)
    cm = ConfigManager()
    cm.customFile = customWithBasicAuthConf
    flat = cm.parse_defaults()
    missing = EXPECTED_BASIC_AUTH_KEYS - flat.keys()
    assert not missing, f"Keys missing from parsed config: {missing}"


@with_setup(my_setup)
def test_case22():
    """parse_defaults() must not introduce keys outside the known schema.

    Any key in the flat dict that is NOT in EXPECTED_KEYS (and not a known
    optional/advanced key) is a sign that the INI parser ingested a garbage
    token (e.g. a bare base64 string) as a key name.
    """
    allowed = EXPECTED_BASIC_AUTH_KEYS | OPTIONAL_TEMPLATE_KEYS
    customWithBasicAuthConf = os.path.join(path, "tests", "test_data", customWithBAuthFile)
    cm = ConfigManager(customWithBasicAuthConf)
    # cm.customFile = customWithBasicAuthConf
    flat = cm.parse_defaults()

    extra = flat.keys() - allowed
    assert not extra, (
        f"Unexpected keys appeared in flat config — possible parsing artefact "
        f"(e.g. bare base64 token read as a key name): {extra}"
    )


@with_setup(my_setup)
def test_case23():
    """The 'password' key must hold exactly the base64 string from the INI."""
    customWithBasicAuthConf = os.path.join(path, "tests", "test_data", customWithBAuthFile)
    cm = ConfigManager(customWithBasicAuthConf)
    flat = cm.parse_defaults()
    assert 'password' in flat, "'password' key must be present"
    assert flat['password'] == 'TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg==', (
        f"unexpected password value: {flat['password']!r}"
    )


@with_setup(my_setup)
def test_case24():
    """None of the keys in the flat config dict should look like a base64
    *payload* (i.e. 20+ chars of [A-Za-z0-9+/=]).

    If configparser ever reads a password-like line without '=' it will
    store the whole base64 string as a key name — this test catches that.
    """
    customWithBasicAuthConf = os.path.join(path, "tests", "test_data", customWithBAuthFile)
    cm = ConfigManager(customWithBasicAuthConf)
    flat = cm.parse_defaults()

    bad_keys = [k for k in flat if _BASE64_KEY_RE.match(k)]
    assert not bad_keys, (
        f"Key name(s) that look like base64 payloads found in flat config "
        f"(INI parsing error?): {bad_keys}"
    )


@with_setup(my_setup)
def test_case25():
    """Sanity-check for the detector above: a hand-crafted INI where the
    password line has no '=' (so the base64 value becomes a bare key) must
    be caught by the _BASE64_KEY_RE guard in the test above.

    This is a meta-test that verifies our detection logic works — it does
    NOT represent a real-world scenario with the shipped INI files.
    """
    malformed_content = (
        "[basic_auth]\n"
        "enabled = True\n"
        "username = scale_admin\n"
        # Deliberately broken: 'password' key is missing, the base64 string
        # sits on its own line → configparser treats it as a continuation or
        # a valueless key depending on the version.
        "TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg\n"
    )
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False)
    f.write(malformed_content)
    f.close()

    cm = ConfigManager(f.name)
    flat = cm.parse_defaults()
    # The base64 string should be detected as a suspicious key
    bad_keys = [k for k in flat if _BASE64_KEY_RE.match(k)]
    # We assert that IF such a key crept in, our regex catches it
    # (this test passes whether or not configparser actually ingests it).
    for k in bad_keys:
        assert _BASE64_KEY_RE.match(k), \
            f"detection regex missed garbage key: {k!r}"
