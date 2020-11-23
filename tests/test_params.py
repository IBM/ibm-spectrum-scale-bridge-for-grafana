import os


def test_case01():
    result = os.system("python ./source/zimonGrafanaIntf.py")
    assert result == 0


def test_case02():
    result = os.system("python ./source/zimonGrafanaIntf.py --port 4242")
    assert result == 0


def test_case03():
    result = os.system("python ./source/zimonGrafanaIntf.py -c 10")
    assert result == 0


def test_case04():
    result = os.system("python ./source/zimonGrafanaIntf.py --port 8443")
    assert result == 0


def test_case05():
    result = os.system('python ./source/zimonGrafanaIntf.py --port 8443 --keyPath "/tmp"')
    assert result == 0


def test_case06():
    result = os.system('python ./source/zimonGrafanaIntf.py -a 2')
    assert result > 0
