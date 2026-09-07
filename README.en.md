# pykma

[![PyPI](https://img.shields.io/pypi/v/pykma)](https://pypi.org/project/pykma/)
[![Downloads](https://static.pepy.tech/badge/pykma/month)](https://pepy.tech/project/pykma)
[![CI](https://github.com/alton15/pykma/actions/workflows/ci.yml/badge.svg)](https://github.com/alton15/pykma/actions)

*[한국어](README.md)*

Python SDK for the Korea Meteorological Administration (KMA) short-term
forecast API. **Latitude and longitude are all you need.**

No more copy-pasting Lambert projection code, computing `base_time` release
schedules, or looking up category tables.

```python
from pykma import KMA

kma = KMA()  # or KMA(service_key="...")

now = kma.now(37.5665, 126.9780)
print(now.temperature, now.humidity)  # 23.4 65

for f in kma.forecast(37.5665, 126.9780):
    print(f.at, f.temperature, f.sky, f.rain_probability)
```

## What it takes off your plate

| | By hand | pykma |
|---|---|---|
| Coordinates | Paste a Lambert conversion off a blog post | `lat, lon` |
| Release times | Per-operation schedule + delay + midnight rollover | Automatic |
| Response | Pivot 800 `category`/`fcstValue` rows yourself | Objects per timestamp |
| Codes | `TMP`? `T1H`? What is `PTY` 5? | `.temperature`, `.precipitation_type` |
| Rainfall | `float("30.0~50.0mm")` blows up | `.precipitation.value == 30.0` |
| Errors | HTTP 200 with an XML error inside | Exceptions |

## Install

```bash
pip install pykma
```

Python 3.11+. `httpx` is the only runtime dependency.

## API key

Get one from the [Korean public data portal](https://www.data.go.kr/data/15084084/openapi.do)
by applying to 단기예보 조회서비스. Approval takes about a day.

```bash
export KMA_SERVICE_KEY="your key"
```

The portal issues both an encoded and a decoded form of the key.
**Either one works here.**

## API

| Method | What | Returns |
|---|---|---|
| `now(lat, lon)` | Current observation | `Observation` |
| `soon(lat, lon)` | Next 6 hours | `list[Forecast]` |
| `forecast(lat, lon)` | Next 3 days | `list[Forecast]` |

`anow` / `asoon` / `aforecast` are the async equivalents.

```python
import asyncio
from pykma import KMA


async def main():
    kma = KMA()
    print((await kma.anow(37.5665, 126.9780)).temperature)


asyncio.run(main())
```

### Errors

Everything subclasses `KMAError`. KMA answers auth failures with HTTP 200,
so `raise_for_status()` alone will not catch them.

| Exception | When |
|---|---|
| `AuthError` | Key missing, unregistered, or expired |
| `QuotaError` | Daily call limit exceeded |
| `RequestError` | Bad parameters |
| `ResponseError` | Response was not the shape we expect |

### Grid

`to_grid(lat, lon)` and `to_latlon(grid)` are usable on their own.
Coordinates outside the forecast grid (149 cells east-west, 253 north-south)
raise `ValueError` — send them through and KMA returns 200 with some other
neighborhood's forecast.

## MCP server

Usable directly from Claude and other agents.

```json
{
  "mcpServers": {
    "pykma": {
      "command": "uvx",
      "args": ["--from", "pykma[mcp]", "pykma-mcp"],
      "env": { "KMA_SERVICE_KEY": "your key" }
    }
  }
}
```

Three tools — `weather_now`, `weather_soon`, `weather_forecast`. Each takes a
latitude and longitude and returns a human-readable line.

## Scope

Covers the short-term forecast service (`VilageFcstInfoService_2.0`) only.
Mid-term forecasts, weather warnings, and living-weather indices are not here yet.

## License

MIT
