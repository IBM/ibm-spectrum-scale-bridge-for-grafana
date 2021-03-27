from source.confParser import ConfigManager, Singleton
from nose.tools import with_setup


def my_setup():
    global a
    a = 1


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
    assert 'port' in connection.keys()


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
    mandatoryItems = ['port', 'serverPort']
    assert all(item in elements for item in mandatoryItems)


def test_case09():
    cm = ConfigManager()
    result = cm.defaults
    value = int(result['port'])
    assert value == 4242


def test_case10():
    cm = ConfigManager()
    result = cm.defaults
    assert int(result['port']) == 4242 and int(result['serverPort']) == 9084
