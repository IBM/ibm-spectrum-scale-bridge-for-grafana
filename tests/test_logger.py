import logging
from source.bridgeLogger import configureLogging
from nose.tools import assert_raises


def test_case01():
    with assert_raises(TypeError):
        configureLogging()


def test_case02():
    with assert_raises(TypeError):
        configureLogging('/tmp')


def test_case03():
    result = configureLogging('/tmp', 'mylog', 'abc')
    assert isinstance(result, logging.Logger)
