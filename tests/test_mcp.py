from dataclasses import replace
from datetime import datetime

import pytest

from pykma.codes import Amount, Precipitation, Sky
from pykma.models import Forecast, Observation
from pykma_mcp.server import (
    format_forecasts,
    format_observation,
    main,
    mcp,
    weather_forecast,
    weather_now,
    weather_soon,
)

# 기본값은 한 번만 만들고, 각 테스트는 replace로 필요한 칸만 바꾼 사본을 쓴다.
_BASE_OBSERVATION = Observation(
    observed_at=datetime(2026, 9, 7, 14, 0),
    temperature=23.4,
    humidity=65,
    precipitation=Amount(raw="강수없음", value=0.0),
    precipitation_type=Precipitation.NONE,
    wind_speed=2.1,
    wind_direction=270,
    raw={},
)


def _observation(**overrides: object) -> Observation:
    return replace(_BASE_OBSERVATION, **overrides)


_BASE_FORECAST = Forecast(
    at=datetime(2026, 9, 7, 15, 0),
    temperature=24.0,
    sky=Sky.CLEAR,
    precipitation_type=Precipitation.NONE,
    rain_probability=20,
    precipitation=None,
    snow=None,
    humidity=None,
    wind_speed=None,
    wind_direction=None,
    min_temperature=None,
    max_temperature=None,
    raw={},
)


def _forecast(**overrides: object) -> Forecast:
    return replace(_BASE_FORECAST, **overrides)


def test_관측을_사람이_읽는_한_줄로_만든다():
    # given / when
    text = format_observation(_observation())

    # then
    assert "23.4" in text
    assert "65" in text
    assert "2026-09-07 14:00" in text
    assert "2.1" in text


def test_관측의_빈_값은_아예_적지_않는다():
    # given — None을 "None"으로 적으면 모델이 그걸 값으로 읽는다
    observation = _observation(humidity=None, wind_speed=None, wind_direction=None)

    # when
    text = format_observation(observation)

    # then
    assert "None" not in text
    assert "습도" not in text
    assert "23.4" in text


def test_예보를_시간대별_줄로_만든다():
    # given / when
    text = format_forecasts([_forecast()])

    # then
    assert "15:00" in text
    assert "24.0" in text
    assert "맑음" in text
    assert "20%" in text


def test_강수가_없으면_강수형태를_적지_않는다():
    # given — 매 줄에 "없음"이 붙으면 읽는 쪽이 시끄럽다
    text = format_forecasts([_forecast(precipitation_type=Precipitation.NONE)])

    # then
    assert "없음" not in text


def test_비가_오면_강수형태를_적는다():
    # given / when
    text = format_forecasts([_forecast(precipitation_type=Precipitation.RAIN)])

    # then
    assert "비" in text


@pytest.mark.parametrize(
    ("sky", "label"), [(Sky.CLEAR, "맑음"), (Sky.PARTLY_CLOUDY, "구름많음"), (Sky.CLOUDY, "흐림")]
)
def test_하늘상태를_말로_적는다(sky, label):
    # given / when
    text = format_forecasts([_forecast(sky=sky)])

    # then
    assert label in text


def test_최저최고기온을_적는다():
    # given / when
    text = format_forecasts([_forecast(min_temperature=18.0, max_temperature=27.0)])

    # then
    assert "최저 18.0" in text
    assert "최고 27.0" in text


def test_여러_시간대는_줄마다_하나씩이다():
    # given
    forecasts = [_forecast(), _forecast(at=datetime(2026, 9, 7, 16, 0))]

    # when
    text = format_forecasts(forecasts)

    # then
    assert len(text.splitlines()) == 2


def test_빈_예보도_문장을_준다():
    # given / when
    text = format_forecasts([])

    # then — 빈 문자열을 주면 에이전트가 도구가 실패한 것으로 읽는다
    assert text.strip()


def test_관측에_비가_오면_강수형태를_적는다():
    # given / when
    text = format_observation(_observation(precipitation_type=Precipitation.RAIN))

    # then
    assert "강수 비" in text


def test_예보의_실제_강수량은_적고_0은_적지_않는다():
    # given — "강수량 강수없음"은 줄만 길게 만든다
    wet = _forecast(precipitation=Amount(raw="30.0~50.0mm", value=30.0))
    dry = _forecast(precipitation=Amount(raw="강수없음", value=0.0))

    # when / then
    assert "30.0~50.0mm" in format_forecasts([wet])
    assert "강수량" not in format_forecasts([dry])


def test_도구_세_개가_등록돼_있다():
    # given / when — 이름이 바뀌면 사용자의 MCP 설정이 조용히 깨진다
    names = {tool.name for tool in mcp._tool_manager.list_tools()}

    # then
    assert {"weather_now", "weather_soon", "weather_forecast"} <= names


@pytest.mark.parametrize(
    ("tool", "method", "expected"),
    [
        (weather_now, "now", format_observation(_observation())),
        (weather_soon, "soon", format_forecasts([_forecast()])),
        (weather_forecast, "forecast", format_forecasts([_forecast()])),
    ],
)
def test_도구는_클라이언트를_불러_문장을_돌려준다(monkeypatch, tool, method, expected):
    # given — 실제 API를 치지 않는다
    called: dict[str, tuple[float, float]] = {}

    class FakeKMA:
        def _record(self, name, lat, lon):
            called[name] = (lat, lon)

        def now(self, lat, lon):
            self._record("now", lat, lon)
            return _observation()

        def soon(self, lat, lon):
            self._record("soon", lat, lon)
            return [_forecast()]

        def forecast(self, lat, lon):
            self._record("forecast", lat, lon)
            return [_forecast()]

    monkeypatch.setattr("pykma_mcp.server.KMA", FakeKMA)

    # when
    text = tool(37.5665, 126.9780)

    # then
    assert called[method] == (37.5665, 126.9780)
    assert text == expected


def test_진입점은_서버를_띄운다(monkeypatch):
    # given — 실제로 stdio 루프를 돌리면 테스트가 멈춘다
    ran: list[bool] = []
    monkeypatch.setattr(mcp, "run", lambda: ran.append(True))

    # when
    main()

    # then
    assert ran == [True]
