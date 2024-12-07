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
