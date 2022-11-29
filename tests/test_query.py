from source.queryHandler.Query import Query
from source.__version__ import __version__ as version
from nose2.tools.decorators import with_setup


def my_setup():
    global metrics, metrics1, capSensors
    metrics = ['cpu_user']
    metrics1 = ['gpfs_fs_inode_used']
    capSensors = ['GPFSDiskCap','GPFSPoolCap', 'GPFSInodeCap']

@with_setup(my_setup)
def test_case01():
    query = Query(metrics)
    assert len(str(query)) > 0
    assert "cpu_user" in str(query)
    assert "-ar" not in str(query)

@with_setup(my_setup)
def test_case02():
    query = Query(metrics1)
    assert "-ar" in str(query)
    query.addMetric('cpu_user')
    assert "-ar" in str(query)

@with_setup(my_setup)
def test_case03():
    for sensor in capSensors:
        query = Query()
        query.sensor = sensor
        assert "-ar" in str(query)
    query = Query()
    query.sensor = 'CPU'
    assert "-ar" not in str(query)
    assert "group" in str(query)
    query = Query(includeDiskData=True)
    query.sensor = 'GPFSDiskCap'
    assert "-ar" in str(query)
