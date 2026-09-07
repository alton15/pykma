"""예외 계층과 포털 결과코드 매핑.

공공데이터포털은 실패해도 HTTP 200을 준다. 본문의 resultCode(또는 인증 실패
시 XML의 returnReasonCode)를 읽어야 실패를 안다. 그 코드를 뜻이 있는 예외로
올리는 것이 이 모듈의 일이다.

예외 메시지에 인증키를 절대 넣지 않는다. 로그와 스택트레이스로 키가 새는
가장 흔한 경로다.
"""

__all__ = [
    "AuthError",
    "KMAError",
    "QuotaError",
    "RequestError",
    "ResponseError",
    "raise_for_result",
]


class KMAError(Exception):
    """pykma가 던지는 모든 예외의 뿌리."""


class AuthError(KMAError):
    """인증키가 없거나, 등록되지 않았거나, 권한이 없다."""


class QuotaError(KMAError):
    """요청 한도를 넘었다."""


class RequestError(KMAError):
    """파라미터가 잘못됐거나 서비스가 없다."""


class ResponseError(KMAError):
    """응답을 이해하지 못했다."""


_SUCCESS = "00"

_AUTH_CODES = frozenset({"20", "21", "30", "31", "32", "33"})
_QUOTA_CODES = frozenset({"22"})
_REQUEST_CODES = frozenset({"10", "11", "12"})


def raise_for_result(code: str, message: str) -> None:
    """포털 결과코드를 예외로 올린다. 정상이면 아무것도 하지 않는다."""
    if code == _SUCCESS:
        return

    detail = f"기상청 API 오류 [{code}] {message}"

    if code in _AUTH_CODES:
        raise AuthError(detail)
    if code in _QUOTA_CODES:
        raise QuotaError(detail)
    if code in _REQUEST_CODES:
        raise RequestError(detail)

    # 03(NODATA)을 포함해 나머지 코드도 조용히 넘기지 않는다.
    raise KMAError(detail)
