from typing import Any
import httpx
import os
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
port = int(os.getenv("PORT", 8085))
mcp = FastMCP("weather", host="0.0.0.0", port=port)

# Open-Meteo is a live public weather API and does not require an API key.
FORECAST_API = "https://api.open-meteo.com/v1/forecast"
GEOCODING_API = "https://geocoding-api.open-meteo.com/v1/search"
USER_AGENT = "weather-app/1.0"

WMO_DESCRIPTIONS = {
    0: "trời quang",
    1: "trời quang nhẹ",
    2: "mây rải rác",
    3: "nhiều mây",
    45: "sương mù",
    48: "sương muối",
    51: "mưa phùn nhẹ",
    53: "mưa phùn",
    55: "mưa phùn dày",
    61: "mưa nhẹ",
    63: "mưa vừa",
    65: "mưa to",
    71: "tuyết nhẹ",
    73: "tuyết vừa",
    75: "tuyết to",
    80: "mưa rào nhẹ",
    81: "mưa rào vừa",
    82: "mưa rào to",
    95: "dông",
    96: "dông kèm mưa đá nhẹ",
    99: "dông kèm mưa đá mạnh",
}


async def make_request(url: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """Call an Open-Meteo endpoint with consistent error handling."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT},
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error {e.response.status_code}: {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"Request Error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None


async def geocode_city(city: str) -> dict[str, Any] | None:
    """Resolve a city name to coordinates using Open-Meteo Geocoding API."""
    data = await make_request(
        GEOCODING_API,
        {"name": city, "count": 1, "language": "en", "format": "json"},
    )
    results = data.get("results", []) if data else []
    return results[0] if results else None


def weather_description(code: int | None) -> str:
    return WMO_DESCRIPTIONS.get(code or -1, f"mã thời tiết WMO {code}")

@mcp.tool()
async def get_current_weather(city: str) -> str:
    """Get current weather conditions for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney")
    """
    location = await geocode_city(city)
    if not location:
        return f"Không tìm thấy thành phố: {city}."

    data = await make_request(
        FORECAST_API,
        {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,weather_code,wind_speed_10m,wind_direction_10m"
            ),
            "timezone": "auto",
        },
    )

    if not data:
        return f"Không thể lấy dữ liệu thời tiết cho {city} từ Open-Meteo."

    current = data["current"]
    current_units = data.get("current_units", {})
    return f"""
Thời tiết hiện tại tại {location['name']}, {location.get('country', '')}:

Nhiệt độ: {current['temperature_2m']} {current_units.get('temperature_2m', '°C')}
Cảm giác: {current['apparent_temperature']} {current_units.get('apparent_temperature', '°C')}
Tình trạng: {weather_description(current.get('weather_code'))}
Độ ẩm: {current['relative_humidity_2m']}%
Mưa: {current['precipitation']} mm
Gió: {current['wind_speed_10m']} {current_units.get('wind_speed_10m', 'km/h')}
Hướng gió: {current['wind_direction_10m']}°

Thời điểm dữ liệu: {current['time']}
Nguồn: Open-Meteo
"""

@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney", "Melbourne")
        days: Number of days to forecast (1-3 for free tier, max 10 for paid)
    """
    # Limit days to 3 for free tier
    days = min(days, 3)
    
    location = await geocode_city(city)
    if not location:
        return f"Không tìm thấy thành phố: {city}."

    data = await make_request(
        FORECAST_API,
        {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "daily": (
                "temperature_2m_max,temperature_2m_min,weather_code,"
                "precipitation_probability_max,wind_speed_10m_max"
            ),
            "forecast_days": days,
            "timezone": "auto",
        },
    )

    if not data:
        return f"Không thể lấy dự báo thời tiết cho {city} từ Open-Meteo."

    daily = data["daily"]

    forecasts = []
    forecasts.append(f"Dự báo thời tiết {days} ngày tại {location['name']}, {location.get('country', '')}:")

    for index, date in enumerate(daily["time"]):
        code = daily["weather_code"][index]

        forecast = f"""
{date}:
Cao nhất: {daily['temperature_2m_max'][index]}°C
Thấp nhất: {daily['temperature_2m_min'][index]}°C
Tình trạng: {weather_description(code)}
Khả năng mưa: {daily['precipitation_probability_max'][index]}%
Gió tối đa: {daily['wind_speed_10m_max'][index]} km/h
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

@mcp.tool()
async def health_check() -> str:
    """Health check endpoint for deployment verification."""
    return "✅ Weather MCP Server is running! Using live Open-Meteo data; no API key required."

print("✅ MCP server initialized with Streamable HTTP transport")
print("🔧 Available tools: get_current_weather, get_forecast, health_check")

if __name__ == "__main__":
    import sys
    
    is_cloud_run = bool(os.getenv("PORT"))
    is_standalone = len(sys.argv) == 1 and sys.stdin.isatty()
    
    if is_cloud_run or is_standalone:
        print(f"🚀 Starting MCP server on http://0.0.0.0:{port}/mcp")
        mcp.run(transport="streamable-http")
    else:
        print("Starting FastMCP server in stdio mode for local client", file=sys.stderr)
        mcp.run()
