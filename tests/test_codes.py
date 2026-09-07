import pytest

from pykma.codes import Amount, Precipitation, Sky, parse_amount, parse_precipitation, parse_sky


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        # 없음을 뜻하는 문자열들 — 0.0이지 None이 아니다.
        ("강수없음", 0.0),
        ("적설없음", 0.0),
        ("-", 0.0),
        ("", 0.0),
        # 하한을 뜻하는 문자열 — 범주의 아래끝을 값으로 삼는다.
        ("1.0mm 미만", 0.0),
        ("1mm 미만", 0.0),
        ("1.0cm 미만", 0.0),
        ("0.1mm미만", 0.0),
        # 범위 — 아래끝을 값으로 삼는다.
        ("30.0~50.0mm", 30.0),
        ("1.0~4.9cm", 1.0),
        ("5.0~9.9cm", 5.0),
        # 이상 — 그 값을 그대로 쓴다.
        ("50.0mm 이상", 50.0),
        ("5.0cm 이상", 5.0),
        # 평범한 숫자
        ("10.0mm", 10.0),
        ("3.5", 3.5),
        ("0", 0.0),
    ],
)
def test_강수_문자열을_숫자로_읽는다(raw, value):
    # given / when
    amount = parse_amount(raw)

    # then
    assert amount.value == value
    assert amount.raw == raw


def test_공백이_섞여도_읽는다():
    # given / when
    amount = parse_amount("  30.0 ~ 50.0 mm  ")

    # then
    assert amount.value == 30.0
    assert amount.raw == "  30.0 ~ 50.0 mm  "


def test_모르는_형식은_값을_비우되_원문은_남긴다():
    # given — 기상청이 새 범주 문구를 내놓아도 데이터를 삼키면 안 된다
    raw = "폭우 예상"

    # when
    amount = parse_amount(raw)

    # then
    assert amount.value is None
    assert amount.raw == raw


def test_없음은_0이고_모름은_None이라_서로_구별된다():
    # given / when
    none = parse_amount("강수없음")
    unknown = parse_amount("???")

    # then — 이 둘을 섞으면 "비가 안 온다"와 "모른다"가 같아진다
    assert none.value == 0.0
    assert unknown.value is None
    assert none == Amount(raw="강수없음", value=0.0)


def test_강수량은_불변이다():
    # given
    amount = parse_amount("10.0mm")

    # when / then
    with pytest.raises(AttributeError):
        amount.value = 1.0  # ty: ignore[invalid-assignment]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", Sky.CLEAR), ("3", Sky.PARTLY_CLOUDY), ("4", Sky.CLOUDY)],
)
def test_하늘상태_코드를_읽는다(raw, expected):
    # given / when / then
    assert parse_sky(raw) is expected


@pytest.mark.parametrize("raw", ["2", "9", "", "맑음", "1.5"])
def test_모르는_하늘상태는_비운다(raw):
    # given / when / then — SKY에 2는 없다(결번)
    assert parse_sky(raw) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", Precipitation.NONE),
        ("1", Precipitation.RAIN),
        ("2", Precipitation.RAIN_SNOW),
        ("3", Precipitation.SNOW),
        ("4", Precipitation.SHOWER),
        ("5", Precipitation.DRIZZLE),
        ("6", Precipitation.DRIZZLE_SNOW),
        ("7", Precipitation.SNOW_FLURRY),
    ],
)
def test_강수형태_코드를_읽는다(raw, expected):
    # given / when / then
    assert parse_precipitation(raw) is expected


@pytest.mark.parametrize("raw", ["8", "", "비", "-1"])
def test_모르는_강수형태는_비운다(raw):
    # given / when / then
    assert parse_precipitation(raw) is None
