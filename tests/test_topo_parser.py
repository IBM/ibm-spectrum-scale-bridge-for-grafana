import os
import json
from source.queryHandler.Topo import Topo
from nose2.tools.decorators import with_setup


def my_setup():
    global path, topoStrFile, topoStr, topo, metrics, metrics1, capSensors
    path = os.getcwd()
    topoStrFile = os.path.join(path, "tests", "test_data", 'topoStr.json')
    with open(topoStrFile) as f:
        topoStr = json.load(f)
    topo = Topo(topoStr)
    metrics = ['cpu_user']
    metrics1 = ['gpfs_fs_inode_used']
    capSensors = ['GPFSDiskCap', 'GPFSPoolCap', 'GPFSInodeCap']


@with_setup(my_setup)
def test_case01():
    searchSensor = 'GPFSDiskCap'
    sensorLabels = topo.getSensorLabels(searchSensor)
    assert len(sensorLabels) > 0
    assert "gpfs_disk_name" in sensorLabels


@with_setup(my_setup)
def test_case02():
    searchSensor = 'GPFSDiskCap'
    typesDict = topo.getSensorMetricTypes(searchSensor)
    assert len(typesDict) > 0
    assert 'counter' not in typesDict.values()
    assert 'gpfs_disk_disksize' in typesDict.keys()
    assert typesDict['gpfs_disk_disksize'] == 'quantity'


@with_setup(my_setup)
def test_case03():
    searchSensor = 'GPFSNSDFS'
    typesDict = topo.getSensorMetricTypes(searchSensor)
    assert len(typesDict) > 0
    assert 'counter' in typesDict.values()
