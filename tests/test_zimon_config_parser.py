import os
from source.queryHandler.SensorConfig import readSensorsConfig
from source.bridgeLogger import configureLogging
from nose2.tools.such import helper as assert_helper
from nose2.tools.decorators import with_setup


def my_setup():
    global path, logger, mainSensorsConfig, wrongSensorsConfig, sensorsCount
    path = os.getcwd()
    logger = configureLogging(path, None)
    mainSensorsConfig = 'ZIMonSensors.cfg'
    wrongSensorsConfig = 'ZIMonSensors-protocols-wrong.cfg'
    sensorsCount = 0


@with_setup(my_setup)
def test_case01():
    with assert_helper.assertRaises(OSError):
        readSensorsConfig(logger)


@with_setup(my_setup)
def test_case02():
    zimonFile = os.path.join(path, "tests", "test_data", mainSensorsConfig)
    sensorsList = readSensorsConfig(logger, zimonFile)
    assert isinstance(sensorsList, list)
    assert len(sensorsList) > 0
    assert len(sensorsList) == 32


@with_setup(my_setup)
def test_case03():
    zimonFile = os.path.join(path, "tests", "test_data", wrongSensorsConfig)
    sensorsList = readSensorsConfig(logger, zimonFile)
    nfsioConf = sensorsList[0]
    assert isinstance(sensorsList, list)
    assert isinstance(nfsioConf, dict)
    assert len(sensorsList) > 0
    assert len(sensorsList) == 1
    assert nfsioConf.get('name') == '"NFSIO"'


@with_setup(my_setup)
def test_case04():
    zimonFile = os.path.join(path, "tests", "test_data", mainSensorsConfig)
    sensorsList = readSensorsConfig(logger, zimonFile)
    sensorsCount = len(sensorsList)
    assert sensorsCount == 32

    zimonFile = os.path.join(path, "tests", "test_data")
    sensorsList1 = readSensorsConfig(logger, zimonFile)
    assert isinstance(sensorsList1, list)
    assert len(sensorsList1) > len(sensorsList)
