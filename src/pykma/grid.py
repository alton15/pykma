"""위경도와 기상청 예보 격자 사이의 변환.

기상청 API는 위경도를 받지 않는다. Lambert Conformal Conic 투영으로 만든
5km 격자의 정수 좌표 (nx, ny)만 받는다. 아래 상수는 기상청이 활용가이드와
함께 배포하는 변환 예제(dfs_xy_conv)의 값 그대로다.

`to_grid`는 **주어진 점이 속한 칸**을 준다. 기상청이 배포하는 좌표표와
대조하면 3,829행 중 98.9%가 정확히 일치하고, 시·도 17개 행은 100% 일치한다.
남는 약 1%는 읍면동 대표점이 격자 경계에 걸린 경우로, 기상청이 그 동에
배정한 칸(면적 기준)과 한 칸 갈린다. 계산이 틀린 것이 아니라 두 값이
서로 다른 질문의 답이다.

이 모듈은 math 말고는 아무것도 import하지 않는다. 네트워크도, 같은 패키지의
다른 모듈도 모른다. 사람들이 가장 많이 틀리는 곳이라 네트워크 없이
전수 테스트되어야 한다.
"""

import math
from dataclasses import dataclass

__all__ = ["Grid", "to_grid", "to_latlon"]

_RE = 6371.00877  # 지구 반경 (km)
_GRID = 5.0  # 격자 간격 (km)
_SLAT1 = 30.0  # 투영 위도 1 (도)
_SLAT2 = 60.0  # 투영 위도 2 (도)
_OLON = 126.0  # 기준점 경도 (도)
_OLAT = 38.0  # 기준점 위도 (도)
_XO = 43  # 기준점 X좌표 (격자)
_YO = 136  # 기준점 Y좌표 (격자)

# 예보 격자의 크기. 동서 149칸 남북 253칸으로 한반도를 덮는다.
_NX_MAX = 149
_NY_MAX = 253

_DEGRAD = math.pi / 180.0
_RADDEG = 180.0 / math.pi


@dataclass(frozen=True)
class Grid:
    """기상청 예보 격자의 한 칸."""

    nx: int
    ny: int


def _projection() -> tuple[float, float, float]:
    """투영 상수 (sn, sf, ro). 위경도와 무관하므로 한 번만 계산한다."""
    re = _RE / _GRID
    slat1 = _SLAT1 * _DEGRAD
    slat2 = _SLAT2 * _DEGRAD
    olat = _OLAT * _DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)

    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = sf**sn * math.cos(slat1) / sn

    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / ro**sn

    return sn, sf, ro


_SN, _SF, _RO = _projection()


def to_grid(lat: float, lon: float) -> Grid:
    """위경도를 그 점이 속한 격자 칸으로 옮긴다."""
    re = _RE / _GRID

    ra = math.tan(math.pi * 0.25 + lat * _DEGRAD * 0.5)
    ra = re * _SF / ra**_SN

    # 기상청 예제는 ±2π를 더하고 빼서 [-π, π]로 접는다. remainder가 그
    # 접기를 그대로 한다 — 분기가 없으니 한쪽만 도달 가능한 문제도 없다.
    theta = math.remainder((lon - _OLON) * _DEGRAD, 2.0 * math.pi) * _SN

    # +0.5 후 int()는 반올림이다. 기상청 예제 코드와 같은 방식으로 맞춘다.
    grid = Grid(
        nx=int(ra * math.sin(theta) + _XO + 0.5),
        ny=int(_RO - ra * math.cos(theta) + _YO + 0.5),
    )

    # 격자 밖의 좌표는 여기서 막는다. 그대로 흘려보내면 API가 200과 함께
    # 엉뚱한 칸의 예보를 주고, 그게 남의 동네 날씨인 줄 아무도 모른다.
    if not (1 <= grid.nx <= _NX_MAX and 1 <= grid.ny <= _NY_MAX):
        raise ValueError(
            f"기상청 예보 격자 밖의 좌표다: lat={lat}, lon={lon} "
            f"→ ({grid.nx}, {grid.ny}). nx는 1..{_NX_MAX}, ny는 1..{_NY_MAX}이다."
        )

    return grid


def to_latlon(grid: Grid) -> tuple[float, float]:
    """격자 칸을 그 칸의 중심 위경도로 되돌린다."""
    olon = _OLON * _DEGRAD

    xn = grid.nx - _XO
    yn = _RO - grid.ny + _YO
    ra = math.sqrt(xn * xn + yn * yn)

    alat = (_RE / _GRID * _SF / ra) ** (1.0 / _SN)
    alat = 2.0 * math.atan(alat) - math.pi * 0.5

    # 기상청 예제는 xn==0, yn==0을 따로 분기하지만 atan2가 그 셋을 그대로
    # 포섭한다. _SN은 양의 상수라 예제의 부호 뒤집기도 죽은 가지다.
    alon = math.atan2(xn, yn) / _SN + olon

    return alat * _RADDEG, alon * _RADDEG
