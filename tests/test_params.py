from source.confParser import ConfigManager, merge_defaults_and_args, parse_cmd_args
from nose.tools import with_setup


def my_setup():
    global a, b, c, d, e, f, g, m, n
    a = ConfigManager().defaults
    b, c = parse_cmd_args([])
    d, e = parse_cmd_args(['-p', '8443', '-t', '/etc/my_tls'])
    f, g = parse_cmd_args(['-p', '8443', '-t', None, '-k', 'None', '-m', "None"])
    m, n = parse_cmd_args(['-d', 'yes'])


@with_setup(my_setup)
def test_case01():
    result = merge_defaults_and_args(a, b)
    assert len(result.keys()) > 0
    assert 'port' in result.keys()
    assert 'serverPort' in result.keys()


@with_setup(my_setup)
def test_case02():
    result = merge_defaults_and_args(a, b)
    assert len(result.keys()) > 0
    assert 'logLevel' in result.keys()
    assert isinstance(result.get('logLevel'), int)
    assert result.get('logLevel') == 15


@with_setup(my_setup)
def test_case03():
    result = merge_defaults_and_args(a, d)
    assert len(result.keys()) > 0
    assert 'port' in result.keys()
    assert result.get('port') == 8443


@with_setup(my_setup)
def test_case04():
    result = merge_defaults_and_args(a, f)
    assert len(result.keys()) > 0
    assert 'tlsKeyPath' not in result.keys()
    assert 'tlsKeyFile' not in result.keys()
    assert 'tlsCertFile' not in result.keys()
    assert result.get('port') == 8443


@with_setup(my_setup)
def test_case05():
    result = merge_defaults_and_args(a, f)
    assert len(result.keys()) > 0
    assert 'includeDiskData' in result.keys()
    assert result.get('includeDiskData') == False


@with_setup(my_setup)
def test_case06():
    result = merge_defaults_and_args(a, m)
    assert len(result.keys()) > 0
    assert 'includeDiskData' in result.keys()
    assert result.get('includeDiskData') == True
