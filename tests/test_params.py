from source.confParser import ConfigManager, merge_defaults_and_args, parse_cmd_args
from nose.tools import with_setup


def my_setup():
    global a, b, c, d, e
    a = ConfigManager().defaults
    b, c = parse_cmd_args([])
    d, e = parse_cmd_args(['-p', '8443', '-t', '/etc/my_tls'])


@with_setup(my_setup)
def test_case01():
    result = merge_defaults_and_args(a, b)
    assert len(result.keys()) > 0
    assert 'port' in result.keys()
    assert 'serverPort' in result.keys()


@with_setup(my_setup)
def test_case02():
    result = merge_defaults_and_args(a, d)
    assert len(result.keys()) > 0
    assert 'port' in result.keys()
    assert result.get('port') == 8443
