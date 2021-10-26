import logging
from source.bridgeLogger import configureLogging
from nose2.tools.such import helper as assert_helper


def test_case01():
    with assert_helper.assertRaises(TypeError):
        configureLogging()


def test_case02():
    with assert_helper.assertRaises(TypeError):
        configureLogging('/tmp')


def test_case03():
    with assert_helper.assertRaises(TypeError):
        configureLogging(None, 'myLog')


def test_case04():
    result = configureLogging('/tmp', 'mylog', 'abc')
    assert isinstance(result, logging.Logger)


def test_case05():
    result = configureLogging('/tmp', None, 'abc')
    assert isinstance(result, logging.Logger)


def test_case06():
    result = configureLogging('/tmp', None)
    assert isinstance(result, logging.Logger)
