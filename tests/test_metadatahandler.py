import os
from source.bridgeLogger import configureLogging
from source.zimonGrafanaIntf import MetadataHandler
from nose2.tools.such import helper as assert_helper
from nose2.tools.decorators import with_setup


def my_setup():
    global path, logger, mainSensorsConfig, wrongSensorsConfig, sensorsCount, myFile
    path = os.getcwd()
    logger = configureLogging(path, None)
    mainSensorsConfig = 'ZIMonSensors.cfg'
    wrongSensorsConfig = 'ZIMonSensors-protocols-wrong.cfg'
    myFile = os.path.join(path, "tests", "test_data", mainSensorsConfig)
    sensorsCount = 0


@with_setup(my_setup)
def test_case01():
    with assert_helper.assertRaises(KeyError):
        MetadataHandler()


@with_setup(my_setup)
def test_case02():
    with assert_helper.assertRaises(KeyError):
        MetadataHandler(logger=logger, apiKeyName='scale_grafana')

@with_setup(my_setup)
def test_case03():
    with assert_helper.assertRaises(KeyError):
        MetadataHandler(logger=logger, server='localhost', port='4242', apiKeyName='scale_grafana')


@with_setup(my_setup)
def test_case04():
    with assert_helper.assertRaises(OSError):
        md = MetadataHandler(logger=logger, server='localhost', port='4242', apiKeyName='scale_grafana', apiKeyValue='85bbe7f2-5f0f-43c8-88dd-9673c9e61390')
        md1 = MetadataHandler()
        assert md == md1
        assert md1.logger == logger
        assert md1.apiKeyName == 'scale_grafana'
