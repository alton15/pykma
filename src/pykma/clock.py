"""오퍼레이션별 base_date / base_time 계산.

기상청은 예보를 정해진 시각에 발표하고, 발표한 자료를 API로 내보내기까지
얼마간 지연이 있다. 발표 시각을 base_time으로 넣어야 하는데 아직 지연이
안 지났으면 자료가 없다. 그래서 "지금 부를 수 있는 가장 최근 발표"를
골라야 하고, 그 계산이 자정을 넘으면 날짜까지 하루 전으로 내려간다.

| 오퍼레이션 | 발표 | API 제공 |
|---|---|---|
| 초단기실황 | 매시 정시 | 발표 + 40분 |
| 초단기예보 | 매시 30분 | 발표 + 45분 |
| 단기예보 | 02·05·08·11·14·17·20·23시 | 발표 + 10분 |

이 모듈은 내부에서 datetime.now()를 부르지 않는다. 호출 시각을 항상 인자로
받으므로 경계를 네트워크도 시계 조작도 없이 전수 테스트할 수 있다.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

__all__ = ["BaseTime", "Operation", "base_for"]


class Operation(StrEnum):
    """단기예보 조회서비스의 오퍼레이션. 값이 곧 API 경로의 마지막 조각이다."""

    ULTRA_NCST = "getUltraSrtNcst"
    ULTRA_FCST = "getUltraSrtFcst"
    VILAGE_FCST = "getVilageFcst"


@dataclass(frozen=True)
class BaseTime:
    """API에 넘길 발표 시각."""

    date: str
    """YYYYMMDD"""

    time: str
    """HHMM"""


# 단기예보 발표 시각 (시)
_VILAGE_HOURS = (2, 5, 8, 11, 14, 17, 20, 23)

# 오퍼레이션별 제공 지연
_DELAY = {
    Operation.ULTRA_NCST: timedelta(minutes=40),
    Operation.ULTRA_FCST: timedelta(minutes=45),
    Operation.VILAGE_FCST: timedelta(minutes=10),
}


def base_for(operation: Operation, now: datetime) -> BaseTime:
    """`now` 시점에 부를 수 있는 가장 최근 발표 시각."""
    # 지연을 먼저 빼면 남는 것은 "이미 제공이 시작된 발표"들의 시간대가 된다.
    # 이렇게 하면 자정 넘김이 datetime 산술 하나로 처리된다.
    available = now - _DELAY[operation]

    if operation is Operation.ULTRA_NCST:
        issued = available.replace(minute=0, second=0, microsecond=0)
    elif operation is Operation.ULTRA_FCST:
        # 30분 발표라 available의 분이 30 미만이면 직전 시각의 30분이다.
        issued = available.replace(minute=30, second=0, microsecond=0)
        if available.minute < 30:
            issued -= timedelta(hours=1)
    else:
        issued = _latest_vilage(available)

    return BaseTime(date=issued.strftime("%Y%m%d"), time=issued.strftime("%H%M"))


def _latest_vilage(available: datetime) -> datetime:
    """`available` 이하의 가장 늦은 단기예보 발표 시각."""
    for hour in reversed(_VILAGE_HOURS):
        if hour <= available.hour:
            return available.replace(hour=hour, minute=0, second=0, microsecond=0)

    # 02시 이전이면 전날 23시 발표가 최신이다.
    previous = available - timedelta(days=1)
    return previous.replace(hour=_VILAGE_HOURS[-1], minute=0, second=0, microsecond=0)
