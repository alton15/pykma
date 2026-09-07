import pykma


def test_버전이_노출된다():
    # given / when
    version = pykma.__version__

    # then
    assert version.count(".") == 2
