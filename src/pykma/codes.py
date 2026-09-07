"""응답의 코드와 값을 뜻으로 옮긴다.

기상청 응답에는 두 종류의 함정이 있다.

첫째, 강수량(PCP)·신적설(SNO)·1시간강수량(RN1)이 숫자가 아니라 범주 문자열로
온다. "강수없음", "1.0mm 미만", "30.0~50.0mm", "50.0mm 이상" 같은 것들이다.
그대로 float()에 넣으면 터진다.

둘째, 같은 뜻인데 오퍼레이션마다 코드가 다르다. 기온은 단기예보에서 TMP,
초단기에서 T1H다. 강수량은 PCP와 RN1이다. models.py가 이 대응을 쓴다.

모르는 코드와 모르는 문자열은 버리지 않는다. 기상청이 범주를 추가해도
라이브러리가 데이터를 삼키면 안 된다.
"""

import re
from dataclasses import dataclass
from enum import IntEnum

__all__ = [
    "Amount",
    "Precipitation",
    "Sky",
    "parse_amount",
    "parse_precipitation",
    "parse_sky",
]


class Sky(IntEnum):
    """하늘상태(SKY). 2는 결번이다."""

    CLEAR = 1
    PARTLY_CLOUDY = 3
    CLOUDY = 4


class Precipitation(IntEnum):
    """강수형태(PTY).

    나오는 범위가 오퍼레이션마다 다르다. 단기예보는 0~4를, 초단기는 0~3과
    5~7을 쓴다. 라이브러리는 둘 다 받는다.
    """

    NONE = 0
    RAIN = 1
    RAIN_SNOW = 2
    SNOW = 3
    SHOWER = 4
    DRIZZLE = 5
    DRIZZLE_SNOW = 6
    SNOW_FLURRY = 7


@dataclass(frozen=True)
class Amount:
    """강수량 또는 적설량.

    value의 단위는 원본 카테고리를 따른다 — PCP·RN1은 mm, SNO는 cm다.
    범주 문자열이면 **범주의 아래끝**이 value가 된다. 읽지 못한 형식은
    value가 None이고, 그때도 raw는 원문 그대로 남는다.
    """

    raw: str
    value: float | None


# "없음"을 뜻하는 표기들. 0.0이지 None이 아니다 —
# "비가 안 온다"와 "모른다"를 섞으면 안 된다.
_NOTHING = frozenset({"강수없음", "적설없음", "-", ""})

# "1.0mm 미만", "1mm 미만", "0.1mm미만"
_BELOW = re.compile(r"^\d+(?:\.\d+)?\s*(?:mm|cm)?\s*미만$")

# "30.0~50.0mm", "1.0 ~ 4.9 cm" — 아래끝을 취한다.
_RANGE = re.compile(r"^(\d+(?:\.\d+)?)\s*~\s*\d+(?:\.\d+)?\s*(?:mm|cm)?$")

# "50.0mm 이상", "10.0mm", "3.5"
_SINGLE = re.compile(r"^(\d+(?:\.\d+)?)\s*(?:mm|cm)?(?:\s*이상)?$")


def parse_amount(raw: str) -> Amount:
    """강수·적설 범주 문자열을 숫자로 읽는다. 못 읽으면 value가 None이다."""
    # 기상청이 값 안에 공백을 섞어 보내는 경우가 있어 전부 지우고 맞춘다.
    text = re.sub(r"\s+", "", raw)

    if text in _NOTHING:
        return Amount(raw=raw, value=0.0)

    # "1.0mm 미만"의 하한은 0이다. 0.0~1.0 구간의 아래끝.
    if _BELOW.match(text):
        return Amount(raw=raw, value=0.0)

    if match := _RANGE.match(text):
        return Amount(raw=raw, value=float(match.group(1)))

    if match := _SINGLE.match(text):
        return Amount(raw=raw, value=float(match.group(1)))

    return Amount(raw=raw, value=None)


def parse_sky(raw: str) -> Sky | None:
    """하늘상태 코드. 모르는 값이면 None."""
    try:
        return Sky(int(raw))
    except ValueError:
        return None


def parse_precipitation(raw: str) -> Precipitation | None:
    """강수형태 코드. 모르는 값이면 None."""
    try:
        return Precipitation(int(raw))
    except ValueError:
        return None
