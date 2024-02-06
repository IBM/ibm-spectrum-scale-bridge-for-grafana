from source.confParser import ConfigManager
from source.__version__ import __version__ as version


def test_case01():
    cm = ConfigManager()
    result = cm.readConfigFile('config.ini')
    assert isinstance(result, dict)


def test_case02():
    cm = ConfigManager()
    result = cm.readConfigFile('config.ini')
    assert len(result.keys()) > 0


def test_case03():
    cm = ConfigManager()
    result = cm.readConfigFile('config.ini')
    assert 'tls' in result.keys()


def test_case04():
    cm = ConfigManager()
    result = cm.readConfigFile('config.ini')
    connection = result['connection']
    assert len(connection) > 0
    assert isinstance(connection, dict)
    assert len(connection) > 0
    if version < "8.0":
        assert 'port' in connection.keys()
    else:
        assert 'port' not in connection.keys()


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
        mandatoryItems = ['port', 'serverPort']
        assert all(item in elements for item in mandatoryItems)
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
        assert result.get('port', None) == None
        assert int(result['serverPort']) == 9980


def test_case11():
    cm = ConfigManager()
    result = cm.defaults
    assert 'includeDiskData' in result.keys()
    assert result['includeDiskData'] == 'no'


def test_case12():
    cm = ConfigManager()
    result = cm.defaults
    assert 'apiKeyValue' not in result.keys()


def test_case13():
    cm = ConfigManager()
    result = cm.defaults
    assert 'protocol' in result.keys()
    assert result['protocol'] == 'http'
