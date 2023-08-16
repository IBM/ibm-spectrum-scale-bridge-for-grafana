import os
# import source.queryHandler.SensorConfig as SensorConfig
from source.queryHandler.SensorConfig import parseSensorsConfig, readSensorsConfig
from source.bridgeLogger import configureLogging
from nose2.tools.such import helper as assert_helper
from nose2.tools.decorators import with_setup


def my_setup():
    global path, logger, mainSensorsConfig, wrongSensorsConfig, zimonFile, sensorsCount
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


@with_setup(my_setup)
def test_case03():
    zimonFile = os.path.join(path, "tests", "test_data", wrongSensorsConfig)
    sensorsList = readSensorsConfig(logger, zimonFile)
    assert isinstance(sensorsList, list)
    assert len(sensorsList) > 0


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
