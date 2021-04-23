import os
from source.__version__ import __version__ as version


def test_case01():
    result = os.system('python ./source/zimonGrafanaIntf.py -a 2')
    assert result > 0


def test_case02():
    result = os.system('python ./source/zimonGrafanaIntf.py -a')
    assert result > 0


def test_case03():
    result = os.system('python ./source/zimonGrafanaIntf.py -c 10 -m "/opt/registry/certs"')
    assert result == 0


def test_case04():
    result = os.system('python ./source/zimonGrafanaIntf.py -c 10 -v "pw"')
    assert result == 0


def test_case05():
    result = os.system('python ./source/zimonGrafanaIntf.py -P 9084')
    if float(version) >= 7.0:
        assert result > 0
