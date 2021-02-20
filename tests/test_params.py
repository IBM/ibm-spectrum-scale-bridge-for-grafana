from source.confParser import parse_defaults_from_config_file


def test_case01():
    result = parse_defaults_from_config_file()
    assert isinstance(result, dict)


def test_case02():
    result = parse_defaults_from_config_file()
    assert len(result.keys()) > 0


def test_case03():
    result = parse_defaults_from_config_file()
    elements = list(result.keys())
    mandatoryItems = ['port', 'serverport']
    assert all(item in elements for item in mandatoryItems)


def test_case04():
    result = parse_defaults_from_config_file()
    value = int(result['port'])
    assert value == 4242


def test_case05():
    result = parse_defaults_from_config_file()
    assert int(result['port']) == 4242 and int(result['serverport']) == 9084

