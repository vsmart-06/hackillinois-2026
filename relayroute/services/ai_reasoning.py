"""
OpenAI zone explanation generation. Uses httpx/OpenAI for GPT-4o mini.
"""
from __future__ import annotations

from openai import AsyncOpenAI

from relayroute.config import get_settings


async def generate_zone_reasoning(city_name: str, zones: list[dict]) -> str:
    """
    Call OpenAI GPT-4o mini to generate a short paragraph explaining the zone layout.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        return "Zone layout was generated from restaurant clustering. Add OPENAI_API_KEY for AI-generated explanation."
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    zones_desc = "\n".join(
        f"- Zone {z.get('id', '')} ({z.get('name', '')}): {z.get('restaurant_count', 0)} restaurants"
        for z in zones
    )
    prompt = (
        f"You are an urban logistics analyst. Given the following zone data for {city_name}, "
        "write a brief explanation (3-5 sentences) of why the city was divided this way "
        "and what each major zone represents geographically.\n\n"
        f"{zones_desc}"
    )
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        if resp.choices and resp.choices[0].message.content:
            return resp.choices[0].message.content.strip()
    except Exception:
        pass
    return "Zone layout was generated from restaurant clustering (DBSCAN)."
