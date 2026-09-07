from datetime import datetime, timedelta

import pytest

from pykma.clock import BaseTime, Operation, base_for


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        # 14시 발표는 14:10부터 제공된다. 그 전에는 11시 발표가 최신이다.
        (datetime(2026, 9, 7, 14, 9), BaseTime("20260907", "1100")),
        (datetime(2026, 9, 7, 14, 10), BaseTime("20260907", "1400")),
        (datetime(2026, 9, 7, 14, 11), BaseTime("20260907", "1400")),
        # 자정 넘김: 23시 발표가 다음 날 02:10까지 최신이다.
        (datetime(2026, 9, 8, 0, 0), BaseTime("20260907", "2300")),
        (datetime(2026, 9, 8, 2, 9), BaseTime("20260907", "2300")),
        (datetime(2026, 9, 8, 2, 10), BaseTime("20260908", "0200")),
        # 발표 직후 경계 전부
        (datetime(2026, 9, 7, 5, 10), BaseTime("20260907", "0500")),
        (datetime(2026, 9, 7, 8, 10), BaseTime("20260907", "0800")),
        (datetime(2026, 9, 7, 11, 10), BaseTime("20260907", "1100")),
        (datetime(2026, 9, 7, 17, 10), BaseTime("20260907", "1700")),
        (datetime(2026, 9, 7, 20, 10), BaseTime("20260907", "2000")),
        (datetime(2026, 9, 7, 23, 10), BaseTime("20260907", "2300")),
    ],
)
def test_단기예보는_8회_발표에_10분_지연을_더한다(now, expected):
    # given / when
    result = base_for(Operation.VILAGE_FCST, now)

    # then
    assert result == expected


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        # 정시 발표 + 40분 제공.
        (datetime(2026, 9, 7, 14, 39), BaseTime("20260907", "1300")),
        (datetime(2026, 9, 7, 14, 40), BaseTime("20260907", "1400")),
        # 자정 넘김
        (datetime(2026, 9, 8, 0, 0), BaseTime("20260907", "2300")),
        (datetime(2026, 9, 8, 0, 39), BaseTime("20260907", "2300")),
        (datetime(2026, 9, 8, 0, 40), BaseTime("20260908", "0000")),
    ],
)
def test_초단기실황은_정시_발표에_40분_지연을_더한다(now, expected):
    # given / when
    result = base_for(Operation.ULTRA_NCST, now)

    # then
    assert result == expected


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        # 매시 30분 발표 + 45분 제공 = 매시 15분부터 직전 시각의 30분 발표가 유효.
        (datetime(2026, 9, 7, 14, 14), BaseTime("20260907", "1230")),
        (datetime(2026, 9, 7, 14, 15), BaseTime("20260907", "1330")),
        (datetime(2026, 9, 7, 15, 14), BaseTime("20260907", "1330")),
        # 자정 넘김
        (datetime(2026, 9, 8, 0, 14), BaseTime("20260907", "2230")),
        (datetime(2026, 9, 8, 0, 15), BaseTime("20260907", "2330")),
    ],
)
def test_초단기예보는_30분_발표에_45분_지연을_더한다(now, expected):
    # given / when
    result = base_for(Operation.ULTRA_FCST, now)

    # then
    assert result == expected


def _issued_at(operation: Operation, now: datetime) -> datetime:
    """base_for가 고른 발표 시각을 datetime으로 되읽는다."""
    base = base_for(operation, now)
    assert len(base.date) == 8, (operation, now, base)
    assert len(base.time) == 4, (operation, now, base)
    return datetime.strptime(base.date + base.time, "%Y%m%d%H%M")


@pytest.mark.parametrize("operation", list(Operation))
def test_하루_전체를_분_단위로_돌려도_과거_하루_안의_발표를_고른다(operation):
    # given — 1,440분 전수. 자정 근처에서 날짜가 어긋나는 버그를 여기서 잡는다.
    start = datetime(2026, 9, 8, 0, 0)

    # when / then
    for minute in range(24 * 60):
        now = start + timedelta(minutes=minute)
        issued = _issued_at(operation, now)
        # 아직 발표되지 않은 시각을 고르면 API가 자료 없음을 준다
        assert issued <= now, (operation, now, issued)
        # 하루 넘게 묵은 발표를 고르면 최신 예보를 버리는 것이다
        assert now - issued < timedelta(days=1), (operation, now, issued)


@pytest.mark.parametrize("operation", list(Operation))
def test_시각이_흐르면_발표시각은_뒤로_가지_않는다(operation):
    # given — 36시간을 7분 간격으로. 자정에서 하루 뒤로 튀면 여기서 걸린다.
    start = datetime(2026, 9, 7, 12, 0)
    previous = _issued_at(operation, start)

    # when / then
    for minute in range(7, 36 * 60, 7):
        issued = _issued_at(operation, start + timedelta(minutes=minute))
        assert issued >= previous, (operation, minute, issued, previous)
        previous = issued


def test_오퍼레이션_값은_API_경로와_같다():
    # given / when / then — client가 이 값을 URL에 그대로 붙인다
    assert Operation.VILAGE_FCST == "getVilageFcst"
    assert Operation.ULTRA_NCST == "getUltraSrtNcst"
    assert Operation.ULTRA_FCST == "getUltraSrtFcst"


def test_발표시각은_불변이다():
    # given
    base = base_for(Operation.VILAGE_FCST, datetime(2026, 9, 7, 14, 30))

    # when / then
    with pytest.raises(AttributeError):
        base.date = "x"  # ty: ignore[invalid-assignment]
