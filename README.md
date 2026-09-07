# pykma

[![PyPI](https://img.shields.io/pypi/v/pykma)](https://pypi.org/project/pykma/)
[![Downloads](https://static.pepy.tech/badge/pykma/month)](https://pepy.tech/project/pykma)
[![CI](https://github.com/alton15/pykma/actions/workflows/ci.yml/badge.svg)](https://github.com/alton15/pykma/actions)

*[English](README.en.md)*

기상청 단기예보 API Python SDK. **위경도만 넣으면 된다.**

격자 변환도, `base_time` 계산도, 카테고리 코드표도 더 안 찾아봐도 된다.

```python
from pykma import KMA

kma = KMA()  # 또는 KMA(service_key="...")

now = kma.now(37.5665, 126.9780)
print(now.temperature, now.humidity)  # 23.4 65

for f in kma.forecast(37.5665, 126.9780):
    print(f.at, f.temperature, f.sky, f.rain_probability)
```

## 이게 없애주는 것

| | 직접 하면 | pykma |
|---|---|---|
| 좌표 | Lambert 변환 함수를 블로그에서 복붙 | `lat, lon` |
| 발표 시각 | 오퍼레이션별 발표 주기 + 제공 지연 + 자정 넘김 처리 | 자동 |
| 응답 | `category`/`fcstValue` 행 800개를 직접 pivot | 시간대별 객체 |
| 코드 | `TMP`? `T1H`? `PTY` 5는 뭐지? | `.temperature`, `.precipitation_type` |
| 강수량 | `"30.0~50.0mm"`를 `float()`에 넣고 터짐 | `.precipitation.value == 30.0` |
| 오류 | HTTP 200인데 XML 에러 | 예외 |

## 설치

```bash
pip install pykma
```

Python 3.11 이상. 런타임 의존성은 `httpx` 하나다.

## 인증키

[공공데이터포털 — 단기예보 조회서비스](https://www.data.go.kr/data/15084084/openapi.do)에서
활용신청한다. 승인에 하루 정도 걸린다.

```bash
export KMA_SERVICE_KEY="발급받은 키"
```

인코딩된 키와 디코딩된 키 **어느 쪽을 넣어도 동작한다.**

## API

| 메서드 | 무엇 | 반환 |
|---|---|---|
| `now(lat, lon)` | 초단기실황 — 지금 관측값 | `Observation` |
| `soon(lat, lon)` | 초단기예보 — 향후 6시간 | `list[Forecast]` |
| `forecast(lat, lon)` | 단기예보 — 향후 3일 | `list[Forecast]` |

`anow` / `asoon` / `aforecast` 로 비동기 호출도 된다.

```python
import asyncio
from pykma import KMA


async def main():
    kma = KMA()
    print((await kma.anow(37.5665, 126.9780)).temperature)


asyncio.run(main())
```

### 오류

전부 `KMAError`를 상속한다. 기상청은 인증 실패에도 HTTP 200을 주기 때문에,
`raise_for_status()`만으로는 걸러지지 않는다.

| 예외 | 언제 |
|---|---|
| `AuthError` | 인증키가 없거나 등록되지 않았거나 만료됐다 |
| `QuotaError` | 일일 호출 한도를 넘었다 |
| `RequestError` | 파라미터가 잘못됐다 |
| `ResponseError` | 응답이 예상한 모양이 아니다 |

### 격자

`to_grid(lat, lon)` / `to_latlon(grid)`를 따로 쓸 수도 있다.
예보 격자(동서 149칸, 남북 253칸) 밖의 좌표는 `ValueError`로 막는다 —
그대로 보내면 기상청이 200과 함께 엉뚱한 칸의 예보를 준다.

## MCP 서버

Claude 등 에이전트에서 바로 쓸 수 있다.

```json
{
  "mcpServers": {
    "pykma": {
      "command": "uvx",
      "args": ["--from", "pykma[mcp]", "pykma-mcp"],
      "env": { "KMA_SERVICE_KEY": "발급받은 키" }
    }
  }
}
```

도구 세 개를 준다 — `weather_now`, `weather_soon`, `weather_forecast`.
전부 위경도를 받아 사람이 읽는 문장을 돌려준다.

## 범위

단기예보 조회서비스(`VilageFcstInfoService_2.0`)만 다룬다. 중기예보, 기상특보,
생활기상지수는 아직 없다.

## 라이선스

MIT
