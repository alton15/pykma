import pytest

from pykma.errors import AuthError, KMAError, QuotaError, RequestError, raise_for_result


def test_정상은_아무것도_던지지_않는다():
    # given / when / then
    raise_for_result("00", "NORMAL_SERVICE")


@pytest.mark.parametrize("code", ["20", "21", "30", "31", "32", "33"])
def test_인증_관련_코드는_AuthError다(code):
    # given / when / then
    with pytest.raises(AuthError):
        raise_for_result(code, "SERVICE_ACCESS_DENIED_ERROR")


def test_한도_초과는_QuotaError다():
    # given / when / then
    with pytest.raises(QuotaError):
        raise_for_result("22", "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR")


@pytest.mark.parametrize("code", ["10", "11", "12"])
def test_파라미터_오류는_RequestError다(code):
    # given / when / then
    with pytest.raises(RequestError):
        raise_for_result(code, "INVALID_REQUEST_PARAMETER_ERROR")


@pytest.mark.parametrize("code", ["01", "02", "03", "04", "05", "99"])
def test_나머지_코드도_KMAError로_올라온다(code):
    # given / when / then — 조용히 넘기지 않는다. NODATA(03)도 마찬가지다.
    with pytest.raises(KMAError):
        raise_for_result(code, "UNKNOWN_ERROR")


def test_모든_예외가_KMAError를_상속한다():
    # given / when / then — 호출자가 하나만 잡아도 전부 걸린다
    for cls in (AuthError, QuotaError, RequestError):
        assert issubclass(cls, KMAError)


def test_예외_메시지에_코드와_사유가_담긴다():
    # given / when
    with pytest.raises(AuthError) as caught:
        raise_for_result("30", "SERVICE_KEY_IS_NOT_REGISTERED_ERROR")

    # then
    assert "30" in str(caught.value)
    assert "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" in str(caught.value)
