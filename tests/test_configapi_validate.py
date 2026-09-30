import json
import pytest
from unittest.mock import MagicMock, patch
from nose2.tools.decorators import with_setup
from source.configapi import _ValidateApi, _run_validators


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_request(data):
    req = MagicMock()
    req.body = _FakeBody(data)
    return req


def _fake_response():
    resp = MagicMock()
    resp.headers = {}
    return resp


def _decode(raw):
    return json.loads(raw.decode('utf-8'))


class _FakeBody:
    def __init__(self, data):
        self._data = data if isinstance(data, bytes) else data.encode('utf-8')

    def read(self):
        return self._data


# ---------------------------------------------------------------------------
# Setup / teardown
# ---------------------------------------------------------------------------


def my_setup():
    global VALID_CONFIG, api
    # A minimal config that passes all startup validators:
    #   - has a port                   (checkApplicationPort)
    #   - has apiKeyName + apiKeyValue (checkAPIsettings)
    #   - basic auth disabled          (checkBasicAuthsettings skipped)
    #   - protocol http                (checkTLSsettings not triggered)
    #   - caCertPath False             (checkCAsettings not triggered)
    VALID_CONFIG = {
        'port': 4242,
        'prometheus': None,
        'apiKeyName': 'scale_grafana',
        'apiKeyValue': 'e40960c9-de0a-4c75-bc71-0bcae6db23b2',
        'enabled': False,
        'username': None,
        'password': None,
        'protocol': 'http',
        'tlsKeyPath': None,
        'tlsKeyFile': None,
        'tlsCertFile': None,
        'caCertPath': False,
        'server': 'localhost',
        'serverPort': 9980,
        'rawCounters': True,
        'logLevel': 15,
        'includeDiskData': False,
        'retryDelay': 60,
    }
    logger = MagicMock()
    logger.trace = MagicMock()
    api = _ValidateApi(logger, dict(VALID_CONFIG))


def my_teardown():
    global VALID_CONFIG, api
    VALID_CONFIG = {}
    api = None


def _make_api(config=None):
    logger = MagicMock()
    logger.trace = MagicMock()
    cfg = dict(VALID_CONFIG) if config is None else config
    return _ValidateApi(logger, cfg)


# ---------------------------------------------------------------------------
# _run_validators unit tests
# ---------------------------------------------------------------------------

@with_setup(my_setup)
def test_case01():
    """A fully-populated valid config produces an empty error list."""
    assert _run_validators(VALID_CONFIG) == []


@with_setup(my_setup)
def test_case02():
    """Removing both port and prometheus triggers exactly one port error."""
    cfg = dict(VALID_CONFIG, port=None, prometheus=None)
    errors = _run_validators(cfg)
    assert len(errors) == 1


@with_setup(my_setup)
def test_case03():
    """A None apiKeyName causes checkAPIsettings to report an ApiKey error."""
    cfg = dict(VALID_CONFIG, apiKeyName=None)
    errors = _run_validators(cfg)
    assert any('ApiKey' in e for e in errors)


@with_setup(my_setup)
def test_case04():
    """Enabling basic auth without username/password produces a BasicAuth error."""
    cfg = dict(VALID_CONFIG, enabled=True, username=None, password=None)
    errors = _run_validators(cfg)
    assert any('basic auth' in e.lower() or 'BasicAuth' in e for e in errors)


@with_setup(my_setup)
def test_case05():
    """Setting protocol to https without any TLS paths triggers an SSL/cert error."""
    cfg = dict(VALID_CONFIG, protocol='https',
               tlsKeyPath=None, tlsKeyFile=None, tlsCertFile=None)
    errors = _run_validators(cfg)
    assert any('ssl' in e.lower() or 'SSL' in e or 'cert' in e.lower()
               for e in errors)


@with_setup(my_setup)
def test_case06():
    """Validators run independently; both a missing port and a missing API key are reported."""
    cfg = dict(VALID_CONFIG, port=None, prometheus=None, apiKeyName=None)
    errors = _run_validators(cfg)
    assert len(errors) >= 2


# ---------------------------------------------------------------------------
# GET /config/validate
# ---------------------------------------------------------------------------

@with_setup(my_setup)
def test_case07():
    """GET returns {valid: true} when the live config passes all validators."""
    with patch('cherrypy.response', _fake_response()):
        result = _decode(api.GET())
    assert result == {'valid': True}


@with_setup(my_setup)
def test_case08():
    """GET returns {valid: false, errors: [...]} when the live config is invalid."""
    invalid_api = _make_api(dict(VALID_CONFIG, port=None, prometheus=None))
    with patch('cherrypy.response', _fake_response()):
        result = _decode(invalid_api.GET())
    assert result['valid'] is False
    assert isinstance(result['errors'], list)
    assert len(result['errors']) > 0


@with_setup(my_setup)
def test_case09():
    """GET sets the Content-Type response header to application/json."""
    resp = _fake_response()
    with patch('cherrypy.response', resp):
        api.GET()
    assert resp.headers['Content-Type'] == 'application/json'


@with_setup(my_setup)
def test_case10():
    """GET writes a trace log entry for the request."""
    with patch('cherrypy.response', _fake_response()):
        api.GET()
    # api.logger.trace accesses the mock logger instance injected into api
    # during setup to verify that processing a GET request on the validation
    # endpoint logged the expected trace message "GET /config/validate"
    # exactly once
    api.logger.trace.assert_called_once_with("GET /config/validate")


# ---------------------------------------------------------------------------
# POST /config/validate
# ---------------------------------------------------------------------------

@with_setup(my_setup)
def test_case11():
    """Empty body → validate live config as-is, same result as GET."""
    with patch('cherrypy.request', _patch_request(b'')), \
         patch('cherrypy.response', _fake_response()):
        result = _decode(api.POST())
    assert result['valid'] is True


@with_setup(my_setup)
def test_case12():
    """A valid overlay returns {valid: true} and includes the merged candidate config."""
    body = json.dumps({'logLevel': 10}).encode()
    with patch('cherrypy.request', _patch_request(body)), \
         patch('cherrypy.response', _fake_response()):
        result = _decode(api.POST())
    assert result['valid'] is True
    assert result['candidate']['logLevel'] == 10


@with_setup(my_setup)
def test_case13():
    """An overlay that breaks a validator returns {valid: false, errors, candidate}."""
    body = json.dumps({'port': None, 'prometheus': None}).encode()
    with patch('cherrypy.request', _patch_request(body)), \
         patch('cherrypy.response', _fake_response()):
        result = _decode(api.POST())
    assert result['valid'] is False
    assert len(result['errors']) > 0
    assert 'candidate' in result


@with_setup(my_setup)
def test_case14():
    """Dry-run must never mutate the live config dict."""
    original_port = api._config['port']
    body = json.dumps({'port': 9999}).encode()
    with patch('cherrypy.request', _patch_request(body)), \
         patch('cherrypy.response', _fake_response()):
        api.POST()
    assert api._config['port'] == original_port


@with_setup(my_setup)
def test_case15():
    """password and apiKeyValue must be stripped from the candidate field."""
    config_with_secrets = dict(VALID_CONFIG,
                               password='c2VjcmV0',
                               apiKeyValue='e40960c9-de0a-4c75-bc71-0bcae6db23b2')
    secret_api = _make_api(config_with_secrets)
    with patch('cherrypy.request', _patch_request(b'')), \
         patch('cherrypy.response', _fake_response()):
        result = _decode(secret_api.POST())
    assert 'password' not in result.get('candidate', {})
    assert 'apiKeyValue' not in result.get('candidate', {})


@with_setup(my_setup)
def test_case16():
    """A request body that is not valid JSON raises HTTPError 400."""
    import cherrypy as _cp
    with patch('cherrypy.request', _patch_request(b'not-json{{{')), \
         patch('cherrypy.response', _fake_response()):
        with pytest.raises(_cp.HTTPError) as exc_info:
            api.POST()
    assert exc_info.value.status == 400


@with_setup(my_setup)
def test_case17():
    """A JSON array body (not an object) raises HTTPError 400."""
    import cherrypy as _cp
    body = json.dumps([1, 2, 3]).encode()
    with patch('cherrypy.request', _patch_request(body)), \
         patch('cherrypy.response', _fake_response()):
        with pytest.raises(_cp.HTTPError) as exc_info:
            api.POST()
    assert exc_info.value.status == 400


@with_setup(my_setup)
def test_case18():
    """POST writes a trace log entry for the request."""
    with patch('cherrypy.request', _patch_request(b'')), \
         patch('cherrypy.response', _fake_response()):
        api.POST()
    api.logger.trace.assert_called_once_with("POST /config/validate")


@with_setup(my_setup)
def test_case19():
    """POST sets the Content-Type response header to application/json."""
    resp = _fake_response()
    with patch('cherrypy.request', _patch_request(b'')), \
         patch('cherrypy.response', resp):
        api.POST()
    assert resp.headers['Content-Type'] == 'application/json'


@with_setup(my_setup)
def test_case20(tmp_path):
    """An https overlay with all TLS files present validates successfully."""
    # create dummy private key/certificate files in the temporary directory
    # tmp_path is a standard pytest built-in fixture
    (tmp_path / 'privkey.pem').write_text('key')
    (tmp_path / 'cert.pem').write_text('cert')
    overlay = {
        'protocol': 'https',
        'tlsKeyPath': str(tmp_path),
        'tlsKeyFile': 'privkey.pem',
        'tlsCertFile': 'cert.pem',
    }
    tls_api = _make_api()
    with patch('cherrypy.request', _patch_request(json.dumps(overlay).encode())), \
         patch('cherrypy.response', _fake_response()):
        result = _decode(tls_api.POST())
    assert result['valid'] is True


@with_setup(my_setup)
def test_case21():
    """An https overlay pointing to a non-existent tlsKeyPath fails validation."""
    overlay = {
        'protocol': 'https',
        'tlsKeyPath': '/nonexistent/path',
        'tlsKeyFile': 'privkey.pem',
        'tlsCertFile': 'cert.pem',
    }
    tls_api = _make_api()
    with patch('cherrypy.request', _patch_request(json.dumps(overlay).encode())), \
         patch('cherrypy.response', _fake_response()):
        result = _decode(tls_api.POST())
    assert result['valid'] is False
    assert len(result['errors']) > 0
