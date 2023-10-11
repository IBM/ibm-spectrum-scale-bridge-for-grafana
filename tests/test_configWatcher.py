import os
import time
from source.watcher import ConfigWatcher
from source.bridgeLogger import configureLogging
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
    dummyFile = os.path.join(path, wrongSensorsConfig)
    cw = ConfigWatcher([dummyFile])
    assert len(cw.paths) == 1
    assert len(cw.filenames) == 0
    cw.start_watch()
    time.sleep(3)
    cw.stop_watch()
    assert len(cw.paths) == 1
    assert len(cw.filenames) == 0


@with_setup(my_setup)
def test_case02():
    cw = ConfigWatcher([path])
    assert len(cw.paths) > 0
    assert len(cw.filenames) == 0
    cw.start_watch()
    time.sleep(3)
    cw.stop_watch()
    assert len(cw.paths) > 0
    assert len(cw.filenames) > 1
