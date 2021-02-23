import os


def test_case01():
    result = os.system('python ./source/zimonGrafanaIntf.py -a 2')
    assert result > 0


def test_case02():
    result = os.system('python ./source/zimonGrafanaIntf.py -a')
    assert result > 0


def test_case03():
    result = os.system('python ./source/zimonGrafanaIntf.py -c 10 -v "/opt/registry/certs"')
    assert result > 0
