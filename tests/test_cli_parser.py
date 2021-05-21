from source.confParser import parse_cmd_args
from nose.tools import with_setup
from argparse import Namespace


def my_setup():
    global a, b, c, d, e, f, g, h
    a = ['-p', '8443', '-t', '/etc/my_tls']
    b = ['-a']
    c = ['-a', 'abc']
    d = ['-c', '10', '-v', '/opt/registry/certs']
    e = ['-c', '10', '-t', '/opt/registry/certs']
    f = ['-c', '10', '-s', '9.155.108.199', '-p', '8443', '-t', '/opt/registry/certs', '--tlsKeyFile', 'privkey.pem', '--tlsCertFile', 'cert.pem']
    g = ['-p', '4242', '-P', '9084']
    h = ['-d', 'no']


def test_case01():
    args, msg = parse_cmd_args([])
    assert isinstance(args, Namespace)
    result = vars(args)
    assert isinstance(result, dict)


def test_case02():
    args, msg = parse_cmd_args([])
    result = vars(args)
    assert len(result.keys()) > 0


def test_case03():
    args, msg = parse_cmd_args([])
    result = vars(args)
    elements = list(result.keys())
    mandatoryItems = ['port', 'serverPort']
    assert all(item in elements for item in mandatoryItems)


@with_setup(my_setup)
def test_case04():
    args, msg = parse_cmd_args(g)
    result = vars(args)
    assert isinstance(result['port'], int)
    assert result['port'] == 4242


@with_setup(my_setup)
def test_case05():
    args, msg = parse_cmd_args(g)
    result = vars(args)
    assert result['port'] == 4242 and result['serverPort'] == 9084


@with_setup(my_setup)
def test_case06():
    args, msg = parse_cmd_args(e)
    result = vars(args)
    assert len(result.keys()) > 0
    assert 'port' in result.keys()
    assert 'serverPort' in result.keys()


@with_setup(my_setup)
def test_case07():
    args, msg = parse_cmd_args(a)
    result = vars(args)
    assert len(result.keys()) > 0
    assert 'port' in result.keys()
    assert result.get('port') == 8443

def test_case08():
    args, msg = parse_cmd_args([])
    result = vars(args)
    assert 'includeDiskData' in result.keys()
    assert result.get('includeDiskData') == None

@with_setup(my_setup)
def test_case09():
    args, msg = parse_cmd_args(h)
    result = vars(args)
    assert 'includeDiskData' in result.keys()
    assert result.get('includeDiskData') == 'no'

