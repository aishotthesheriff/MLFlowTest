"""Weather knowledge corpus and query cases for the F-006 RAG tracing experiment.

Shared by ``setup_rag_index.py`` (index seeding) and ``trace_rag.py`` (traced
queries) so the expected top document is defined in exactly one place.
"""

from __future__ import annotations

DOCS: tuple[dict[str, str], ...] = (
    {
        "doc_id": "sf-current",
        "title": "San Francisco current conditions",
        "content": (
            "San Francisco is currently cloudy with a temperature near 14C. "
            "Coastal humidity is high and the sky is mostly overcast."
        ),
    },
    {
        "doc_id": "sf-rain",
        "title": "San Francisco rain forecast",
        "content": (
            "Light rain is likely in San Francisco during the evening. "
            "Expect wet streets and reduced visibility near the waterfront."
        ),
    },
    {
        "doc_id": "sf-wind",
        "title": "San Francisco coastal winds",
        "content": (
            "Strong westerly winds develop along the San Francisco coast in the "
            "afternoon. Gusts can reach 40 km/h near the bridges."
        ),
    },
    {
        "doc_id": "nyc-current",
        "title": "New York City current conditions",
        "content": (
            "New York City is partly cloudy with a temperature near 22C. "
            "Conditions are mild across the metropolitan area."
        ),
    },
    {
        "doc_id": "nyc-snow",
        "title": "New York City overnight snow",
        "content": (
            "Snow showers are possible overnight in New York City. "
            "Accumulation is expected to stay below two centimeters."
        ),
    },
    {
        "doc_id": "seattle-rain",
        "title": "Seattle weekly forecast",
        "content": (
            "Seattle faces persistent rain through the week. "
            "Showers are likely each morning with brief afternoon breaks."
        ),
    },
    {
        "doc_id": "london-fog",
        "title": "London visibility",
        "content": (
            "London has foggy mornings and mild afternoons. "
            "Visibility improves after midday as the fog burns off."
        ),
    },
    {
        "doc_id": "tokyo-storms",
        "title": "Tokyo afternoon thunderstorms",
        "content": (
            "Tokyo is humid with afternoon thunderstorms. "
            "Heavy downpours are possible between 15:00 and 18:00 local time."
        ),
    },
    {
        "doc_id": "cloud-cover",
        "title": "How cloud cover is measured",
        "content": (
            "Cloud cover is reported in oktas, from zero for a clear sky to "
            "eight for complete overcast. Weather services round to phrases "
            "such as sunny, partly cloudy, and cloudy."
        ),
    },
    {
        "doc_id": "forecast-basics",
        "title": "What a weather forecast predicts",
        "content": (
            "A weather forecast predicts atmospheric conditions such as "
            "temperature, precipitation, wind, and cloud cover for a place "
            "and time range, using observations and numerical models."
        ),
    },
    {
        "doc_id": "temperature-units",
        "title": "Temperature units",
        "content": (
            "Temperature is commonly reported in Celsius or Fahrenheit. "
            "Weather services usually publish both scales for public reports."
        ),
    },
    {
        "doc_id": "observation-sources",
        "title": "Where weather observations come from",
        "content": (
            "Weather data is collected from satellites, radar, and ground "
            "stations. These observations feed numerical prediction models."
        ),
    },
)

QUERY_CASES: tuple[dict[str, str], ...] = (
    {
        "case": "sf_current",
        "query": "What is the current weather in San Francisco?",
        "expected_doc": "sf-current",
    },
    {
        "case": "nyc_snow",
        "query": "Will it snow in New York tonight?",
        "expected_doc": "nyc-snow",
    },
    {
        "case": "tokyo_weather",
        "query": "What is the weather like in Tokyo?",
        "expected_doc": "tokyo-storms",
    },
)
