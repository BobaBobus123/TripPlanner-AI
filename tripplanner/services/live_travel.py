import asyncio
from datetime import date

import httpx

from tripplanner.models import (
    LivePlace,
    LiveTravelInfo,
    PlanRequest,
    WeatherDay,
)


class LiveTravelService:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def collect(self, request: PlanRequest) -> LiveTravelInfo:
        try:
            async with asyncio.timeout(2.0):
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(1.5),
                    transport=self._transport,
                    headers={"User-Agent": "TripPlanner-AI/1.0"},
                ) as client:
                    location = await self._geocode(client, request.destination)
                    if location is None:
                        return LiveTravelInfo()

                    latitude = location["latitude"]
                    longitude = location["longitude"]
                    weather_task = self._weather(
                        client, latitude, longitude, request.start_date, request.end_date
                    )
                    attractions_task = self._overpass(
                        client, latitude, longitude,
                        '[tourism~"attraction|museum|gallery|viewpoint|zoo"]',
                        "Перлина",
                    )
                    accommodations_task = self._overpass(
                        client, latitude, longitude,
                        '[tourism~"hotel|hostel|guest_house|apartment"]',
                        "Житло",
                    )
                    (weather, weather_ok), attractions, accommodations = await asyncio.gather(
                        weather_task,
                        attractions_task,
                        accommodations_task,
                    )
        except TimeoutError:
            return LiveTravelInfo()

        sources: list[str] = []
        if weather_ok:
            sources.append("Open-Meteo")
        if attractions or accommodations:
            sources.append("OpenStreetMap")

        return LiveTravelInfo(
            latitude=latitude,
            longitude=longitude,
            weather=weather,
            attractions=attractions,
            accommodations=accommodations,
            sources=sources,
        )

    async def _geocode(
        self, client: httpx.AsyncClient, destination: str
    ) -> dict[str, float] | None:
        try:
            response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": destination, "count": 1, "language": "uk", "format": "json"},
            )
            response.raise_for_status()
            result = response.json().get("results") or []
            if not result:
                return None
            return {
                "latitude": float(result[0]["latitude"]),
                "longitude": float(result[0]["longitude"]),
            }
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return None

    async def _weather(
        self,
        client: httpx.AsyncClient,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
    ) -> tuple[list[WeatherDay], bool]:
        try:
            today = date.today()
            if start_date < today or (start_date - today).days > 16:
                return [], False
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                    "timezone": "auto",
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )
            response.raise_for_status()
            daily = response.json().get("daily") or {}
            dates = daily.get("time") or []
            weather: list[WeatherDay] = []
            for index, day in enumerate(dates):
                weather.append(
                    WeatherDay(
                        date=day,
                        temperature_min=self._optional_float(daily.get("temperature_2m_min"), index),
                        temperature_max=self._optional_float(daily.get("temperature_2m_max"), index),
                        precipitation_probability=self._optional_int(
                            daily.get("precipitation_probability_max"), index
                        ),
                        weather_code=self._optional_int(daily.get("weather_code"), index),
                    )
                )
            return weather, bool(weather)
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return [], False

    async def _overpass(
        self,
        client: httpx.AsyncClient,
        latitude: float,
        longitude: float,
        tourism_filter: str,
        fallback_category: str,
    ) -> list[LivePlace]:
        query = (
            "[out:json][timeout:8];"
            f"(nwr{tourism_filter}(around:5000,{latitude},{longitude}););"
            "out center 10;"
        )
        try:
            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
            )
            response.raise_for_status()
            elements = response.json().get("elements") or []
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return []

        places: list[LivePlace] = []
        for element in elements:
            tags = element.get("tags") or {}
            name = tags.get("name:uk") or tags.get("name") or tags.get("int_name")
            if not name:
                continue
            address_parts = [
                tags.get("addr:street"),
                tags.get("addr:housenumber"),
                tags.get("addr:city"),
            ]
            address = ", ".join(part for part in address_parts if part) or None
            places.append(
                LivePlace(
                    name=str(name),
                    category=tags.get("tourism") or fallback_category,
                    address=address,
                    latitude=self._element_latitude(element),
                    longitude=self._element_longitude(element),
                )
            )
            if len(places) >= 8:
                break
        return places

    @staticmethod
    def _optional_float(values: object, index: int) -> float | None:
        if not isinstance(values, list) or index >= len(values):
            return None
        value = values[index]
        return float(value) if value is not None else None

    @staticmethod
    def _optional_int(values: object, index: int) -> int | None:
        if not isinstance(values, list) or index >= len(values):
            return None
        value = values[index]
        return int(value) if value is not None else None

    @staticmethod
    def _element_latitude(element: dict[str, object]) -> float | None:
        if isinstance(element.get("lat"), (int, float)):
            return float(element["lat"])
        center = element.get("center")
        if isinstance(center, dict) and isinstance(center.get("lat"), (int, float)):
            return float(center["lat"])
        return None

    @staticmethod
    def _element_longitude(element: dict[str, object]) -> float | None:
        if isinstance(element.get("lon"), (int, float)):
            return float(element["lon"])
        center = element.get("center")
        if isinstance(center, dict) and isinstance(center.get("lon"), (int, float)):
            return float(center["lon"])
        return None
