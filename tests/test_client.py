import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from pykma import KMA
from pykma.errors import AuthError, KMAError, QuotaError, ResponseError

FIXTURES = Path(__file__).parent / "fixtures"
AT = datetime(2026, 9, 7, 14, 30)
SEOUL = (37.5665, 126.9780)


def _ok(_request: httpx.Request) -> httpx.Response:
    body = json.loads((FIXTURES / "vilage_fcst.json").read_text(encoding="utf-8"))
    return httpx.Response(200, json=body)


def _client(
    handler: Callable[[httpx.Request], httpx.Response], service_key: str = "test-key"
) -> KMA:
    return KMA(service_key=service_key, transport=httpx.MockTransport(handler))


def _capturing() -> tuple[dict[str, str], Callable[[httpx.Request], httpx.Response]]:
    """요청 파라미터를 담아 두는 핸들러."""
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return _ok(request)

    return seen, handler


def test_예보를_시간대_객체로_돌려준다():
    # given
    kma = _client(_ok)

    # when
    forecasts = kma.forecast(*SEOUL, at=AT)

    # then
    assert len(forecasts) == 7
    assert forecasts[0].at < forecasts[-1].at
    assert forecasts[0].temperature == 27.0


def test_위경도를_격자로_바꿔_보낸다():
    # given
    seen, handler = _capturing()

    # when
    _client(handler).forecast(*SEOUL, at=AT)

    # then — 서울시청은 (60, 127)이다
    assert seen["nx"] == "60"
    assert seen["ny"] == "127"


def test_발표시각을_계산해_보낸다():
    # given
    seen, handler = _capturing()

    # when — 14:30이면 14시 발표(+10분 제공)가 최신이다
    _client(handler).forecast(*SEOUL, at=AT)

    # then
    assert seen["base_date"] == "20260907"
    assert seen["base_time"] == "1400"


def test_오퍼레이션마다_다른_경로를_친다():
    # given
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return _ok(request)

    kma = _client(handler)

    # when
    kma.forecast(*SEOUL, at=AT)
    kma.soon(*SEOUL, at=AT)

    # then
    assert paths[0].endswith("/getVilageFcst")
    assert paths[1].endswith("/getUltraSrtFcst")


def test_인코딩된_인증키를_디코딩해_보낸다():
    # given — 포털은 인코딩·디코딩 두 형태의 키를 준다.
    # 인코딩된 쪽을 그대로 넘기면 %가 재인코딩돼 인증에 실패한다.
    seen, handler = _capturing()

    # when
    _client(handler, service_key="abc%2Bdef%3D%3D").forecast(*SEOUL, at=AT)

    # then
    assert seen["serviceKey"] == "abc+def=="


def test_디코딩된_인증키는_그대로_보낸다():
    # given
    seen, handler = _capturing()

    # when
    _client(handler, service_key="abc+def==").forecast(*SEOUL, at=AT)

    # then
    assert seen["serviceKey"] == "abc+def=="


def test_HTTP_200인데_XML_에러면_예외를_던진다():
    # given — 인증 실패 시 포털은 200과 함께 XML 에러 본문을 준다
    xml = (FIXTURES / "auth_error.xml").read_text(encoding="utf-8")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=xml, headers={"content-type": "application/xml"})

    # when / then
    with pytest.raises(AuthError, match=r"\[30\]"):
        _client(handler).forecast(*SEOUL, at=AT)


def test_본문_결과코드가_오류면_예외를_던진다():
    # given — JSON 봉투 안에 오류 코드가 담겨 오는 경우
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"response": {"header": {"resultCode": "22", "resultMsg": "LIMITED"}}}
        )

    # when / then
    with pytest.raises(QuotaError):
        _client(handler).forecast(*SEOUL, at=AT)


def test_JSON이_아니면_ResponseError다():
    # given
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json at all")

    # when / then
    with pytest.raises(ResponseError):
        _client(handler).forecast(*SEOUL, at=AT)


def test_봉투는_맞는데_자료가_없으면_ResponseError다():
    # given
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"response": {"header": {"resultCode": "00", "resultMsg": "OK"}, "body": {}}},
        )

    # when / then
    with pytest.raises(ResponseError):
        _client(handler).forecast(*SEOUL, at=AT)


def test_HTTP_오류는_그대로_올린다():
    # given
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    # when / then
    with pytest.raises(httpx.HTTPStatusError):
        _client(handler).forecast(*SEOUL, at=AT)


@pytest.mark.parametrize(
    "body",
    [
        "not json at all",
        '{"response": {"header": {"resultCode": "30", "resultMsg": "NOT_REGISTERED"}}}',
    ],
)
def test_예외_메시지에_인증키가_들어가지_않는다(body):
    # given — 로그와 스택트레이스로 키가 새는 가장 흔한 경로다
    secret = "super-secret-key-value"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body, headers={"content-type": "application/json"})

    # when
    with pytest.raises(KMAError) as caught:
        _client(handler, service_key=secret).forecast(*SEOUL, at=AT)

    # then
    assert secret not in str(caught.value)
    assert secret not in repr(caught.value)


def test_인증키가_없으면_환경변수를_읽는다(monkeypatch):
    # given
    monkeypatch.setenv("KMA_SERVICE_KEY", "from-env")
    seen, handler = _capturing()

    # when
    KMA(transport=httpx.MockTransport(handler)).forecast(*SEOUL, at=AT)

    # then
    assert seen["serviceKey"] == "from-env"


def test_인자로_넘긴_키가_환경변수를_이긴다(monkeypatch):
    # given
    monkeypatch.setenv("KMA_SERVICE_KEY", "from-env")
    seen, handler = _capturing()

    # when
    _client(handler, service_key="explicit").forecast(*SEOUL, at=AT)

    # then
    assert seen["serviceKey"] == "explicit"


def test_인증키가_아무_데도_없으면_네트워크_전에_거절한다(monkeypatch):
    # given
    monkeypatch.delenv("KMA_SERVICE_KEY", raising=False)

    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("네트워크를 치면 안 된다")

    # when / then
    with pytest.raises(AuthError, match="KMA_SERVICE_KEY"):
        KMA(transport=httpx.MockTransport(handler)).forecast(*SEOUL, at=AT)


def test_격자_밖_좌표는_네트워크_전에_거절한다():
    # given
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("네트워크를 치면 안 된다")

    # when / then
    with pytest.raises(ValueError, match="격자 밖"):
        _client(handler).forecast(35.6762, 139.6503, at=AT)


def test_실황은_관측_하나를_돌려준다():
    # given
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
                    "body": {
                        "items": {
                            "item": [
                                {
                                    "baseDate": "20260907",
                                    "baseTime": "1400",
                                    "category": "T1H",
                                    "obsrValue": "23.4",
                                    "nx": 60,
                                    "ny": 127,
                                }
                            ]
                        }
                    },
                }
            },
        )

    # when
    observation = _client(handler).now(*SEOUL, at=AT)

    # then
    assert observation.temperature == 23.4
    assert observation.observed_at == datetime(2026, 9, 7, 14, 0)


async def test_비동기_예보도_같은_결과를_준다():
    # given
    kma = _client(_ok)

    # when
    forecasts = await kma.aforecast(*SEOUL, at=AT)

    # then
    assert len(forecasts) == 7
    assert forecasts[0].temperature == 27.0


async def test_비동기_초단기예보도_동작한다():
    # given
    kma = _client(_ok)

    # when
    forecasts = await kma.asoon(*SEOUL, at=AT)

    # then
    assert forecasts


async def test_비동기_실황도_오류를_그대로_올린다():
    # given
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"response": {"header": {"resultCode": "22", "resultMsg": "LIMITED"}}}
        )

    # when / then
    with pytest.raises(QuotaError):
        await _client(handler).anow(*SEOUL, at=AT)
