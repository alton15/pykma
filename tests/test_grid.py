import csv
from pathlib import Path

import pytest

from pykma.grid import Grid, to_grid, to_latlon

TABLE = Path(__file__).parent / "fixtures" / "kma_grid_table.csv"

# 기상청 공식 좌표표의 1단계(시·도) 17개 행. 표 전체에서 이 층은 100% 재현된다.
ANCHORS = [
    ("서울특별시", 37.563569, 126.980008, 60, 127),
    ("부산광역시", 35.177019, 129.076953, 98, 76),
    ("대구광역시", 35.868542, 128.603553, 89, 90),
    ("인천광역시", 37.453233, 126.707353, 55, 124),
    ("광주광역시", 35.156975, 126.853364, 58, 74),
    ("대전광역시", 36.347119, 127.386567, 67, 100),
    ("울산광역시", 35.535408, 129.313689, 102, 84),
    ("세종특별자치시", 36.480012, 127.289069, 66, 103),
    ("경기도", 37.271844, 127.011689, 60, 120),
    ("충청북도", 36.632500, 127.493586, 69, 107),
    ("충청남도", 36.323872, 127.422956, 68, 100),
    ("전라남도", 34.813044, 126.465000, 51, 67),
    ("경상북도", 36.575999, 128.505832, 87, 106),
    ("경상남도", 35.234736, 128.694167, 91, 77),
    ("제주특별자치도", 33.485694, 126.500333, 52, 38),
    ("강원특별자치도", 37.882692, 127.731975, 73, 134),
    ("전북특별자치도", 35.817275, 127.111053, 63, 89),
]


def _table() -> list[tuple[str, int, float, float, int, int]]:
    """공식 좌표표 픽스처. 주석 줄(#)은 건너뛴다."""
    with TABLE.open(encoding="utf-8") as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        return [
            (
                r["name"],
                int(r["level"]),
                float(r["lat"]),
                float(r["lon"]),
                int(r["nx"]),
                int(r["ny"]),
            )
            for r in rows
        ]


@pytest.mark.parametrize(("name", "lat", "lon", "nx", "ny"), ANCHORS)
def test_공식_좌표표의_시도_기준점을_재현한다(name, lat, lon, nx, ny):
    # given / when
    grid = to_grid(lat, lon)

    # then
    assert (grid.nx, grid.ny) == (nx, ny), name


def test_공식_좌표표_전체가_한_칸_이내로_일치한다():
    # given — 3,829행 전체. 여기가 틀리면 나머지가 전부 옳아도 남의 동네 날씨를 준다.
    rows = _table()
    assert len(rows) > 3000, "픽스처가 잘렸다"

    # when
    off_by_more_than_one = []
    exact = 0
    for name, _level, lat, lon, nx, ny in rows:
        grid = to_grid(lat, lon)
        if (grid.nx, grid.ny) == (nx, ny):
            exact += 1
        elif abs(grid.nx - nx) > 1 or abs(grid.ny - ny) > 1:
            off_by_more_than_one.append((name, (nx, ny), (grid.nx, grid.ny)))

    # then — 두 칸 이상 어긋나면 투영이 깨진 것이다
    assert off_by_more_than_one == []

    # 그리고 대부분은 정확히 일치해야 한다. 나머지 ~1%는 읍면동 대표점이
    # 격자 경계에 걸려, 기상청이 면적 기준으로 배정한 칸과 갈리는 경우다.
    assert exact / len(rows) > 0.98


def test_시도_수준은_한_행도_어긋나지_않는다():
    # given — 대표점이 경계에 걸릴 여지가 가장 적은 층
    rows = [r for r in _table() if r[1] == 1]
    assert len(rows) == 17

    # when
    mismatched = [
        name
        for name, _l, lat, lon, nx, ny in rows
        if (to_grid(lat, lon).nx, to_grid(lat, lon).ny) != (nx, ny)
    ]

    # then
    assert mismatched == []


@pytest.mark.parametrize(("name", "lat", "lon", "nx", "ny"), ANCHORS)
def test_격자에서_되돌린_위경도가_같은_격자로_돌아온다(name, lat, lon, nx, ny):
    # given
    grid = Grid(nx, ny)

    # when — 칸 중심으로 되돌아오므로 원래 좌표와는 다르다
    back_lat, back_lon = to_latlon(grid)

    # then — 다시 변환하면 같은 칸이어야 한다
    assert to_grid(back_lat, back_lon) == grid, name


def test_되돌린_위경도가_한반도_범위_안에_있다():
    # given / when
    lat, lon = to_latlon(Grid(60, 127))

    # then
    assert 33.0 < lat < 39.0
    assert 124.0 < lon < 132.0


def test_격자는_불변이다():
    # given
    grid = to_grid(37.563569, 126.980008)

    # when / then
    with pytest.raises(AttributeError):
        grid.nx = 1  # ty: ignore[invalid-assignment]


@pytest.mark.parametrize(
    ("name", "lat", "lon"),
    [
        ("도쿄", 35.6762, 139.6503),
        ("뉴욕", 40.7128, -74.0060),
        ("적도 태평양", 0.0, 180.0),
        ("남극", -70.0, 126.0),
    ],
)
def test_격자_밖의_좌표는_거절한다(name, lat, lon):
    # given / when / then — 흘려보내면 남의 동네 날씨를 조용히 돌려준다
    with pytest.raises(ValueError, match="격자 밖"):
        to_grid(lat, lon)


def test_거절_메시지가_넘긴_좌표를_보여준다():
    # given / when
    with pytest.raises(ValueError) as caught:
        to_grid(35.6762, 139.6503)

    # then — 무엇을 넣어서 틀렸는지 메시지만 보고 알 수 있어야 한다
    assert "139.6503" in str(caught.value)
    assert "35.6762" in str(caught.value)


def test_격자의_서쪽_끝도_되돌릴_수_있다():
    # given — nx가 기준점과 같아 x 성분이 0이 되는 자리
    grid = Grid(43, 100)

    # when
    lat, lon = to_latlon(grid)

    # then — 기준 경도 위에 그대로 놓인다
    assert lon == pytest.approx(126.0)
    assert to_grid(lat, lon) == grid
