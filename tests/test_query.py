from source.queryHandler.Query import Query
from source.__version__ import __version__ as version
from nose2.tools.decorators import with_setup


def my_setup():
    global metrics, metrics1
    metrics = ['cpu_user']
    metrics1 = ['gpfs_fs_inode_used']

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
