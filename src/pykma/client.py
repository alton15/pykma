"""기상청 단기예보 조회서비스 호출.

이 파일만 네트워크를 안다. 나머지 모듈은 전부 순수 함수라 네트워크 없이
테스트된다.

여기서 흡수하는 함정 둘.

첫째, 포털이 인증키를 인코딩·디코딩 두 형태로 준다. 인코딩된 쪽을 그대로
쿼리에 넣으면 %가 다시 인코딩돼(%2B → %252B) 인증에 실패한다. 키에 %가
보이면 한 번 디코딩해서 보낸다.

둘째, 실패해도 HTTP는 200이다. 인증이 틀리면 JSON이 아니라 XML 에러가 오고,
그 외의 실패는 정상 봉투 안의 resultCode로 온다. 둘 다 예외로 올린다.
"""

import os
import re
from datetime import datetime
from typing import Any
from urllib.parse import unquote

import httpx

from .clock import Operation, base_for
from .errors import AuthError, ResponseError, raise_for_result
from .grid import to_grid
from .models import Forecast, Observation, build_forecasts, build_observation

__all__ = ["KMA"]

_BASE_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
_ENV_KEY = "KMA_SERVICE_KEY"

# 한 번에 받을 행 수. 단기예보 3일치가 대략 800행이라 넉넉히 잡는다.
_ROWS = {
    Operation.ULTRA_NCST: 100,
    Operation.ULTRA_FCST: 100,
    Operation.VILAGE_FCST: 1000,
}

# 인증 실패 시 오는 XML에서 코드와 사유를 뽑는다. 이 응답 하나를 위해
# XML 파서를 끌어들일 이유가 없다.
_XML_CODE = re.compile(r"<returnReasonCode>(\d+)</returnReasonCode>")
_XML_MSG = re.compile(r"<returnAuthMsg>([^<]*)</returnAuthMsg>")


class KMA:
    """기상청 단기예보 API 클라이언트."""

    def __init__(
        self,
        service_key: str | None = None,
        *,
        timeout: float = 10.0,
        transport: Any = None,
    ) -> None:
        """인증키를 받는다. 없으면 환경변수 KMA_SERVICE_KEY를 읽는다.

        transport는 테스트에서 httpx.MockTransport를 끼우기 위한 자리다.
        평소에는 넘기지 않는다.
        """
        self._key = service_key or os.environ.get(_ENV_KEY) or ""
        self._timeout = timeout
        self._transport = transport

    def now(self, lat: float, lon: float, *, at: datetime | None = None) -> Observation:
        """지금의 초단기실황."""
        return build_observation(self._get(Operation.ULTRA_NCST, lat, lon, at))

    def soon(self, lat: float, lon: float, *, at: datetime | None = None) -> list[Forecast]:
        """향후 6시간 초단기예보."""
        return build_forecasts(self._get(Operation.ULTRA_FCST, lat, lon, at))

    def forecast(self, lat: float, lon: float, *, at: datetime | None = None) -> list[Forecast]:
        """향후 3일 단기예보."""
        return build_forecasts(self._get(Operation.VILAGE_FCST, lat, lon, at))

    async def anow(self, lat: float, lon: float, *, at: datetime | None = None) -> Observation:
        """`now`의 비동기 판."""
        return build_observation(await self._aget(Operation.ULTRA_NCST, lat, lon, at))

    async def asoon(self, lat: float, lon: float, *, at: datetime | None = None) -> list[Forecast]:
        """`soon`의 비동기 판."""
        return build_forecasts(await self._aget(Operation.ULTRA_FCST, lat, lon, at))

    async def aforecast(
        self, lat: float, lon: float, *, at: datetime | None = None
    ) -> list[Forecast]:
        """`forecast`의 비동기 판."""
        return build_forecasts(await self._aget(Operation.VILAGE_FCST, lat, lon, at))

    def _params(
        self, operation: Operation, lat: float, lon: float, at: datetime | None
    ) -> dict[str, str | int]:
        if not self._key:
            raise AuthError(
                f"인증키가 없다. KMA(service_key=...)로 넘기거나 환경변수 {_ENV_KEY}에 둔다."
            )

        # 격자 밖 좌표면 to_grid가 여기서 ValueError를 던진다. 네트워크 전이다.
        grid = to_grid(lat, lon)
        base = base_for(operation, at or datetime.now())

        return {
            # 포털이 주는 인코딩된 키를 그대로 쓰면 %가 재인코딩된다.
            "serviceKey": unquote(self._key) if "%" in self._key else self._key,
            "pageNo": 1,
            "numOfRows": _ROWS[operation],
            "dataType": "JSON",
            "base_date": base.date,
            "base_time": base.time,
            "nx": grid.nx,
            "ny": grid.ny,
        }

    def _get(
        self, operation: Operation, lat: float, lon: float, at: datetime | None
    ) -> list[dict[str, Any]]:
        params = self._params(operation, lat, lon, at)
        with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
            response = client.get(f"{_BASE_URL}/{operation.value}", params=params)
        return _unwrap(response)

    async def _aget(
        self, operation: Operation, lat: float, lon: float, at: datetime | None
    ) -> list[dict[str, Any]]:
        params = self._params(operation, lat, lon, at)
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.get(f"{_BASE_URL}/{operation.value}", params=params)
        return _unwrap(response)


def _unwrap(response: httpx.Response) -> list[dict[str, Any]]:
    """봉투를 벗기고 행 목록을 꺼낸다. 실패는 예외로 올린다."""
    response.raise_for_status()
    text = response.text

    # 인증 실패는 JSON이 아니라 XML로 온다. HTTP는 200이다.
    if "<returnReasonCode>" in text:
        code = match.group(1) if (match := _XML_CODE.search(text)) else "99"
        message = match.group(1) if (match := _XML_MSG.search(text)) else "SERVICE ERROR"
        raise_for_result(code, message)

    try:
        body: Any = response.json()
        header = body["response"]["header"]
    except (ValueError, KeyError, TypeError) as error:
        # 본문을 예외에 싣지 않는다. 쿼리가 되울려 오면 인증키가 샌다.
        raise ResponseError("기상청 응답을 이해하지 못했다.") from error

    raise_for_result(str(header["resultCode"]), str(header.get("resultMsg", "")))

    try:
        return list(body["response"]["body"]["items"]["item"])
    except (KeyError, TypeError) as error:
        raise ResponseError("기상청 응답에 자료가 없다.") from error
