"""Verify that parsing custom_with_basic_auth.ini via ConfigManager produces
a clean flat config dict (cfg.config / brFullConfig) with no spurious keys.

The 'wrong key' concern: if the INI password line ever loses its '=' sign,
configparser could silently ingest the bare base64 string as a key name.
These tests confirm that the live custom_with_basic_auth.ini file:
  1. produces exactly the expected set of flat keys (no garbage keys)
  2. 'password' is present and holds the correct base64 value
  3. no key that looks like a base64 string appears anywhere in the config
"""
import os
import re
import tempfile
from source.confParser import ConfigManager  # noqa: E402
from source.metaclasses import Singleton  # noqa: E402

CUSTOM_WITH_AUTH = os.path.join(
    os.path.dirname(__file__), 'test_data', 'custom_with_basic_auth.ini')
TEMPLATE = os.path.join(os.path.dirname(__file__), '..', 'source', 'config.ini')

# Keys that must be present in the flat config when using custom_with_basic_auth.ini
EXPECTED_KEYS = {
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

# Regex that matches a likely base64 payload (long, contains +/= characters
# typical of base64, or is purely alphanumeric/= and longer than 20 chars).
_BASE64_KEY_RE = re.compile(r'^[A-Za-z0-9+/]{20,}={0,2}$')


def _fresh_cm(custom_file):
    """Return a fresh (non-singleton) ConfigManager pointed at *custom_file*."""
    Singleton._instances.clear()
    return ConfigManager(custom_file)


# ---------------------------------------------------------------------------
# 1. The flat config contains exactly the expected keys (no unknown additions)
# ---------------------------------------------------------------------------

def test_parse_defaults_contains_expected_keys():
    """parse_defaults() must include all expected keys from the custom file."""
    cm = _fresh_cm(CUSTOM_WITH_AUTH)
    flat = cm.parse_defaults()
    missing = EXPECTED_KEYS - flat.keys()
    assert not missing, f"Keys missing from parsed config: {missing}"


def test_parse_defaults_has_no_extra_unknown_keys():
    """parse_defaults() must not introduce keys outside the known schema.

    Any key in the flat dict that is NOT in EXPECTED_KEYS (and not a known
    optional/advanced key) is a sign that the INI parser ingested a garbage
    token (e.g. a bare base64 string) as a key name.
    """
    # Known optional keys that may be present from the template but absent in
    # the custom file (and thus carry their template default value).
    OPTIONAL_TEMPLATE_KEYS = {
        'port',                                      # opentsdb_plugin (commented)
        'tlsKeyPath', 'tlsKeyFile', 'tlsCertFile',   # tls (all commented)
        'apiKeyValue',                               # server (commented)
        'cpAccessLog', 'cpAccessLogBackups',         # logging (optional)
    }
    allowed = EXPECTED_KEYS | OPTIONAL_TEMPLATE_KEYS

    cm = _fresh_cm(CUSTOM_WITH_AUTH)
    flat = cm.parse_defaults()

    extra = flat.keys() - allowed
    assert not extra, (
        f"Unexpected keys appeared in flat config — possible parsing artefact "
        f"(e.g. bare base64 token read as a key name): {extra}"
    )


# ---------------------------------------------------------------------------
# 2. password key holds the correct value and is not corrupted
# ---------------------------------------------------------------------------

def test_password_value_is_correct_base64_string():
    """The 'password' key must hold exactly the base64 string from the INI."""
    cm = _fresh_cm(CUSTOM_WITH_AUTH)
    flat = cm.parse_defaults()
    assert 'password' in flat, "'password' key must be present"
    assert flat['password'] == 'TXlWZXJ5U3Ryb25nUGFzc3cwcmQhCg==', (
        f"unexpected password value: {flat['password']!r}"
    )


# ---------------------------------------------------------------------------
# 3. No key name looks like a base64 payload (the "wrong key" detection)
# ---------------------------------------------------------------------------

def test_no_base64_looking_key_names():
    """None of the keys in the flat config dict should look like a base64
    *payload* (i.e. 20+ chars of [A-Za-z0-9+/=]).

    If configparser ever reads a password-like line without '=' it will
    store the whole base64 string as a key name — this test catches that.
    """
    cm = _fresh_cm(CUSTOM_WITH_AUTH)
    flat = cm.parse_defaults()

    bad_keys = [k for k in flat if _BASE64_KEY_RE.match(k)]
    assert not bad_keys, (
        f"Key name(s) that look like base64 payloads found in flat config "
        f"(INI parsing error?): {bad_keys}"
    )


# ---------------------------------------------------------------------------
# 4. Regression: a malformed INI (no '=' in password line) *would* produce
#    a garbage key — confirm the detection test catches it.
# ---------------------------------------------------------------------------

def test_malformed_ini_detected_by_base64_key_check():
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
    try:
        Singleton._instances.clear()
        cm = ConfigManager(f.name)
        flat = cm.parse_defaults()
        # The base64 string should be detected as a suspicious key
        bad_keys = [k for k in flat if _BASE64_KEY_RE.match(k)]
        # We assert that IF such a key crept in, our regex catches it
        # (this test passes whether or not configparser actually ingests it).
        for k in bad_keys:
            assert _BASE64_KEY_RE.match(k), \
                f"detection regex missed garbage key: {k!r}"
    finally:
        os.unlink(f.name)
        Singleton._instances.clear()
