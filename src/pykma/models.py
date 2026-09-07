"""응답의 평평한 행을 시간대별 객체로 묶는다.

기상청 응답은 한 시간대의 값들이 한 행에 모여 있지 않다. category 하나가
한 행이라 3일치 예보가 수백 행으로 온다. 쓰려면 (fcstDate, fcstTime)으로
묶어야 하는데, 그 pivot을 다들 각자 다시 짜고 있다.

같은 뜻인데 오퍼레이션마다 다른 코드도 여기서 흡수한다. 기온은 단기예보에서
TMP, 초단기에서 T1H다. 강수량은 PCP와 RN1이다. 사용자는 .temperature 하나만
보면 된다.

모르는 카테고리도 raw에 남긴다. 값 하나가 깨져도 그 필드만 비우고 나머지
시간대는 살린다 — 한 칸 때문에 예보 전체를 잃으면 안 된다.
"""

from dataclasses import dataclass
from datetime import datetime

from .codes import Amount, Precipitation, Sky, parse_amount, parse_precipitation, parse_sky

__all__ = ["Forecast", "Observation", "build_forecasts", "build_observation"]


@dataclass(frozen=True)
class Observation:
    """초단기실황 한 개. 예보가 아니라 실제 관측값이다."""

    observed_at: datetime
    temperature: float | None
    humidity: int | None
    precipitation: Amount | None
    precipitation_type: Precipitation | None
    wind_speed: float | None
    wind_direction: int | None
    raw: dict[str, str]
    """파싱 전 카테고리 → 값. 모르는 카테고리도 여기 남는다."""


@dataclass(frozen=True)
class Forecast:
    """예보 한 시간대. 초단기예보와 단기예보가 같은 타입을 쓴다."""

    at: datetime
    temperature: float | None
    sky: Sky | None
    precipitation_type: Precipitation | None
    rain_probability: int | None
    precipitation: Amount | None
    snow: Amount | None
    humidity: int | None
    wind_speed: float | None
    wind_direction: int | None
    min_temperature: float | None
    max_temperature: float | None
    raw: dict[str, str]
    """파싱 전 카테고리 → 값. 모르는 카테고리도 여기 남는다."""


def _to_float(raw: dict[str, str], *categories: str) -> float | None:
    """주어진 카테고리 중 먼저 있는 것을 실수로 읽는다. 못 읽으면 None."""
    for category in categories:
        if category in raw:
            try:
                return float(raw[category])
            except ValueError:
                return None
    return None


def _to_int(raw: dict[str, str], *categories: str) -> int | None:
    """주어진 카테고리 중 먼저 있는 것을 정수로 읽는다. 못 읽으면 None."""
    value = _to_float(raw, *categories)
    return None if value is None else int(value)


def _to_amount(raw: dict[str, str], *categories: str) -> Amount | None:
    """주어진 카테고리 중 먼저 있는 것을 강수량으로 읽는다."""
    for category in categories:
        if category in raw:
            return parse_amount(raw[category])
    return None


def _to_sky(raw: dict[str, str]) -> Sky | None:
    return parse_sky(raw["SKY"]) if "SKY" in raw else None


def _to_precipitation_type(raw: dict[str, str]) -> Precipitation | None:
    return parse_precipitation(raw["PTY"]) if "PTY" in raw else None


def _parse_when(date: str, time: str) -> datetime:
    """'20260907' + '1400' → datetime."""
    return datetime.strptime(f"{date}{time}", "%Y%m%d%H%M")


def build_observation(items: list[dict[str, str]]) -> Observation:
    """초단기실황 응답의 행들을 관측 하나로 묶는다."""
    if not items:
        raise ValueError("기상청 실황 응답에 자료가 없다.")

    raw = {item["category"]: item["obsrValue"] for item in items}
    first = items[0]

    return Observation(
        observed_at=_parse_when(first["baseDate"], first["baseTime"]),
        # 실황은 T1H만 쓰지만, 대응표를 한 곳에 모아 두기 위해 TMP도 받아 둔다.
        temperature=_to_float(raw, "T1H", "TMP"),
        humidity=_to_int(raw, "REH"),
        precipitation=_to_amount(raw, "RN1", "PCP"),
        precipitation_type=_to_precipitation_type(raw),
        wind_speed=_to_float(raw, "WSD"),
        wind_direction=_to_int(raw, "VEC"),
        raw=raw,
    )


def build_forecasts(items: list[dict[str, str]]) -> list[Forecast]:
    """예보 응답의 행들을 시간대별로 묶어 시간 순으로 돌려준다."""
    grouped: dict[tuple[str, str], dict[str, str]] = {}
    for item in items:
        key = (item["fcstDate"], item["fcstTime"])
        grouped.setdefault(key, {})[item["category"]] = item["fcstValue"]

    forecasts = [
        Forecast(
            at=_parse_when(date, time),
            # 단기예보는 TMP, 초단기예보는 T1H. 사용자에겐 같은 속성이다.
            temperature=_to_float(raw, "TMP", "T1H"),
            sky=_to_sky(raw),
            precipitation_type=_to_precipitation_type(raw),
            rain_probability=_to_int(raw, "POP"),
            # 단기예보는 PCP, 초단기예보는 RN1.
            precipitation=_to_amount(raw, "PCP", "RN1"),
            snow=_to_amount(raw, "SNO"),
            humidity=_to_int(raw, "REH"),
            wind_speed=_to_float(raw, "WSD"),
            wind_direction=_to_int(raw, "VEC"),
            min_temperature=_to_float(raw, "TMN"),
            max_temperature=_to_float(raw, "TMX"),
            raw=raw,
        )
        for (date, time), raw in grouped.items()
    ]

    return sorted(forecasts, key=lambda forecast: forecast.at)
