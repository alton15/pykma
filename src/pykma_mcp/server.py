"""기상청 날씨를 에이전트가 쓸 수 있게 내보내는 MCP 서버.

pykma에만 의존한다. 반대 방향 의존은 없다 — 라이브러리는 MCP를 모른다.

값을 JSON으로 던지지 않고 사람이 읽는 문장으로 만드는 이유: 모델이 읽을
것이라 단위와 시각이 글자로 붙어 있는 편이 오해가 적고 토큰도 적게 든다.
비어 있는 값은 아예 적지 않는다 — "None"을 적으면 모델이 그걸 값으로 읽는다.
"""

from mcp.server.mcpserver import MCPServer

from pykma import KMA, Forecast, Observation, Precipitation, Sky, __version__

__all__ = ["format_forecasts", "format_observation", "main", "mcp"]

# 버전을 넘겨야 클라이언트의 서버 목록에 뭘 붙였는지가 뜬다. 기본값은 빈 문자열이다.
mcp = MCPServer("pykma", version=__version__)

_SKY_LABEL = {
    Sky.CLEAR: "맑음",
    Sky.PARTLY_CLOUDY: "구름많음",
    Sky.CLOUDY: "흐림",
}

_PTY_LABEL = {
    Precipitation.RAIN: "비",
    Precipitation.RAIN_SNOW: "비/눈",
    Precipitation.SNOW: "눈",
    Precipitation.SHOWER: "소나기",
    Precipitation.DRIZZLE: "빗방울",
    Precipitation.DRIZZLE_SNOW: "빗방울눈날림",
    Precipitation.SNOW_FLURRY: "눈날림",
}


def format_observation(observation: Observation) -> str:
    """관측 하나를 한 줄로."""
    parts = [observation.observed_at.strftime("%Y-%m-%d %H:%M") + " 실황"]

    if observation.temperature is not None:
        parts.append(f"기온 {observation.temperature}도")
    if observation.humidity is not None:
        parts.append(f"습도 {observation.humidity}%")
    if (label := _PTY_LABEL.get(observation.precipitation_type)) is not None:
        parts.append(f"강수 {label}")
    if observation.precipitation is not None:
        parts.append(f"강수량 {observation.precipitation.raw}")
    if observation.wind_speed is not None:
        parts.append(f"풍속 {observation.wind_speed}m/s")

    return ", ".join(parts)


def format_forecasts(forecasts: list[Forecast]) -> str:
    """예보 목록을 시간대별 한 줄씩."""
    if not forecasts:
        return "해당 시각의 예보 자료가 없다."

    lines = []
    for forecast in forecasts:
        parts = [forecast.at.strftime("%m-%d %H:%M")]
        if forecast.temperature is not None:
            parts.append(f"{forecast.temperature}도")
        if (sky := _SKY_LABEL.get(forecast.sky)) is not None:
            parts.append(sky)
        # 강수 "없음"은 매 줄에 붙으면 시끄럽기만 하다. _PTY_LABEL에 NONE이 없다.
        if (pty := _PTY_LABEL.get(forecast.precipitation_type)) is not None:
            parts.append(pty)
        if forecast.rain_probability is not None:
            parts.append(f"강수확률 {forecast.rain_probability}%")
        if forecast.precipitation is not None and forecast.precipitation.value:
            parts.append(f"강수량 {forecast.precipitation.raw}")
        if forecast.min_temperature is not None:
            parts.append(f"최저 {forecast.min_temperature}도")
        if forecast.max_temperature is not None:
            parts.append(f"최고 {forecast.max_temperature}도")
        lines.append("  ".join(parts))

    return "\n".join(lines)


@mcp.tool()
def weather_now(latitude: float, longitude: float) -> str:
    """주어진 위경도의 현재 기상 실황. 기온·습도·강수·풍속."""
    return format_observation(KMA().now(latitude, longitude))


@mcp.tool()
def weather_soon(latitude: float, longitude: float) -> str:
    """주어진 위경도의 향후 6시간 예보. 한 시간 단위."""
    return format_forecasts(KMA().soon(latitude, longitude))


@mcp.tool()
def weather_forecast(latitude: float, longitude: float) -> str:
    """주어진 위경도의 향후 3일 예보. 기온·하늘상태·강수확률."""
    return format_forecasts(KMA().forecast(latitude, longitude))


def main() -> None:
    """콘솔 스크립트 진입점."""
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
