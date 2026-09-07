from datetime import datetime

import pytest

from pykma.codes import Precipitation, Sky
from pykma.models import build_forecasts, build_observation


def _ncst(category: str, value: str) -> dict[str, str]:
    return {
        "baseDate": "20260907",
        "baseTime": "1400",
        "category": category,
        "obsrValue": value,
        "nx": "60",
        "ny": "127",
    }


def _fcst(time: str, category: str, value: str, date: str = "20260907") -> dict[str, str]:
    return {
        "baseDate": "20260907",
        "baseTime": "1400",
        "fcstDate": date,
        "fcstTime": time,
        "category": category,
        "fcstValue": value,
        "nx": "60",
        "ny": "127",
    }


def test_실황은_한_개의_관측으로_묶인다():
    # given — 초단기실황은 T1H(기온)와 RN1(강수량)을 쓴다
    items = [
        _ncst("T1H", "23.4"),
        _ncst("REH", "65"),
        _ncst("RN1", "강수없음"),
        _ncst("PTY", "0"),
        _ncst("WSD", "2.1"),
        _ncst("VEC", "270"),
    ]

    # when
    observation = build_observation(items)

    # then
    assert observation.observed_at == datetime(2026, 9, 7, 14, 0)
    assert observation.temperature == 23.4
    assert observation.humidity == 65
    assert observation.precipitation is not None
    assert observation.precipitation.value == 0.0
    assert observation.precipitation_type is Precipitation.NONE
    assert observation.wind_speed == 2.1
    assert observation.wind_direction == 270


def test_실황_행이_비면_거절한다():
    # given / when / then — 조용히 빈 관측을 만들면 호출자가 못 알아챈다
    with pytest.raises(ValueError, match="자료가 없다"):
        build_observation([])


def test_예보는_시간대별로_한_개씩_묶인다():
    # given — 두 시간대가 뒤섞여 들어온다
    items = [
        _fcst("1500", "TMP", "24"),
        _fcst("1600", "TMP", "23"),
        _fcst("1500", "SKY", "1"),
        _fcst("1600", "SKY", "4"),
        _fcst("1500", "POP", "20"),
        _fcst("1600", "POP", "60"),
    ]

    # when
    forecasts = build_forecasts(items)

    # then
    assert len(forecasts) == 2
    assert forecasts[0].at == datetime(2026, 9, 7, 15, 0)
    assert forecasts[0].temperature == 24.0
    assert forecasts[0].sky is Sky.CLEAR
    assert forecasts[0].rain_probability == 20
    assert forecasts[1].at == datetime(2026, 9, 7, 16, 0)
    assert forecasts[1].sky is Sky.CLOUDY
    assert forecasts[1].rain_probability == 60


def test_예보는_시간_순으로_정렬된다():
    # given — 입력 순서가 뒤집혀 있고 날짜도 넘어간다
    items = [
        _fcst("0300", "TMP", "18", date="20260908"),
        _fcst("2300", "TMP", "20"),
        _fcst("1500", "TMP", "24"),
    ]

    # when
    forecasts = build_forecasts(items)

    # then
    assert [f.at for f in forecasts] == [
        datetime(2026, 9, 7, 15, 0),
        datetime(2026, 9, 7, 23, 0),
        datetime(2026, 9, 8, 3, 0),
    ]


def test_초단기예보의_T1H도_기온으로_읽힌다():
    # given — 단기예보는 TMP, 초단기예보는 T1H. 같은 속성으로 나와야 한다
    items = [_fcst("1500", "T1H", "24.5")]

    # when
    forecasts = build_forecasts(items)

    # then
    assert forecasts[0].temperature == 24.5


def test_초단기예보의_RN1도_강수량으로_읽힌다():
    # given — 단기예보는 PCP, 초단기예보는 RN1
    items = [_fcst("1500", "RN1", "1.0mm 미만")]

    # when
    forecasts = build_forecasts(items)

    # then
    assert forecasts[0].precipitation is not None
    assert forecasts[0].precipitation.value == 0.0
    assert forecasts[0].precipitation.raw == "1.0mm 미만"


def test_적설량을_읽는다():
    # given
    items = [_fcst("1500", "SNO", "1.0~4.9cm")]

    # when
    forecasts = build_forecasts(items)

    # then
    assert forecasts[0].snow is not None
    assert forecasts[0].snow.value == 1.0


def test_일_최저최고기온을_읽는다():
    # given — TMN/TMX는 하루에 한 번만 실려 온다
    items = [_fcst("0600", "TMN", "18.0"), _fcst("1500", "TMX", "27.0")]

    # when
    forecasts = build_forecasts(items)

    # then
    assert forecasts[0].min_temperature == 18.0
    assert forecasts[0].max_temperature is None
    assert forecasts[1].max_temperature == 27.0


def test_모르는_카테고리도_raw에_남는다():
    # given — 기상청이 카테고리를 추가해도 삼키면 안 된다
    items = [_fcst("1500", "TMP", "24"), _fcst("1500", "XYZ", "unknown")]

    # when
    forecasts = build_forecasts(items)

    # then
    assert forecasts[0].raw["XYZ"] == "unknown"
    assert forecasts[0].raw["TMP"] == "24"


def test_숫자로_못_읽는_값은_그_필드만_비우고_나머지는_살린다():
    # given — TMP가 깨졌지만 SKY는 멀쩡하다
    items = [_fcst("1500", "TMP", "n/a"), _fcst("1500", "SKY", "1")]

    # when
    forecasts = build_forecasts(items)

    # then
    assert forecasts[0].temperature is None
    assert forecasts[0].sky is Sky.CLEAR
    assert forecasts[0].raw["TMP"] == "n/a"


def test_없는_카테고리는_None이다():
    # given — 초단기실황에는 SKY도 POP도 없다
    items = [_fcst("1500", "TMP", "24")]

    # when
    forecast = build_forecasts(items)[0]

    # then
    assert forecast.sky is None
    assert forecast.rain_probability is None
    assert forecast.precipitation is None
    assert forecast.snow is None
    assert forecast.humidity is None
    assert forecast.wind_speed is None
    assert forecast.wind_direction is None
    assert forecast.precipitation_type is None


def test_빈_목록은_빈_결과다():
    # given / when / then — 예보는 없을 수 있다. 실황과 달리 오류가 아니다.
    assert build_forecasts([]) == []


def test_예보는_불변이다():
    # given
    forecast = build_forecasts([_fcst("1500", "TMP", "24")])[0]

    # when / then
    with pytest.raises(AttributeError):
        forecast.temperature = 0.0  # ty: ignore[invalid-assignment]
