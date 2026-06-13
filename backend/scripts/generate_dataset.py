"""
Genera un dataset de fine-tuning (preferencias -> itinerario JSON) llamando
al backend local /api/v1/itineraries/generate repetidamente con distintas
combinaciones de preferencias.

Salida: dataset/itineraries_dataset.jsonl
Cada línea: {"prompt": "...", "completion": "...json..."}

Uso:
    python -m scripts.generate_dataset
"""
import asyncio
import itertools
import json
import os
from pathlib import Path

import httpx

API_URL = "http://127.0.0.1:8000/api/v1/itineraries/generate"

DESTINATIONS = [
    "Tokio, Japón",
    "París, Francia",
    "Cartagena, Colombia",
    "Barcelona, España",
    "Roma, Italia",
    "Ciudad de México, México",
    "Lisboa, Portugal",
    "Buenos Aires, Argentina",
]

DURATIONS = [2, 3, 5]
BUDGETS = [800, 1500, 3000]
BUDGET_TYPES = ["budget", "moderate", "luxury"]
INTERESTS_COMBOS = [
    ["culture", "food"],
    ["outdoor", "adventure"],
    ["food", "nightlife"],
    ["culture", "nature", "photography"],
    ["beach", "leisure"],
]
TRAVEL_STYLES = ["relaxed", "balanced", "intensive"]
GROUP_TYPES = ["solo", "couple", "family", "friends"]

OUTPUT_PATH = Path("dataset/itineraries_dataset.jsonl")
MAX_EXAMPLES = 60


def build_prompt(prefs: dict) -> str:
    return (
        f"Genera un itinerario de viaje para {prefs['destination']}, "
        f"{prefs['duration']} días, presupuesto {prefs['budget']} USD "
        f"({prefs['budgetType']}), intereses: {', '.join(prefs['interests'])}, "
        f"estilo {prefs['travelStyle']}, viajero(s): {prefs['groupType']}."
    )


async def generate_one(client: httpx.AsyncClient, prefs: dict) -> dict | None:
    try:
        resp = await client.post(API_URL, json={"preferences": prefs}, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error generando para {prefs['destination']}: {e}")
        return None


async def main():
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    combos = list(itertools.product(
        DESTINATIONS, DURATIONS, BUDGETS, BUDGET_TYPES, INTERESTS_COMBOS, TRAVEL_STYLES, GROUP_TYPES
    ))
    import random
    random.seed(42)
    random.shuffle(combos)
    combos = combos[:MAX_EXAMPLES]

    written = 0
    async with httpx.AsyncClient() as client:
        with OUTPUT_PATH.open("w", encoding="utf-8") as f:
            for dest, duration, budget, budget_type, interests, style, group in combos:
                prefs = {
                    "destination": dest,
                    "duration": duration,
                    "budget": budget,
                    "budgetType": budget_type,
                    "interests": interests,
                    "restrictions": "",
                    "travelStyle": style,
                    "groupType": group,
                }
                itinerary = await generate_one(client, prefs)
                if itinerary is None:
                    continue

                example = {
                    "prompt": build_prompt(prefs),
                    "completion": json.dumps(itinerary, ensure_ascii=False),
                }
                f.write(json.dumps(example, ensure_ascii=False) + "\n")
                written += 1
                print(f"[{written}/{MAX_EXAMPLES}] OK: {dest} ({duration}d, {budget_type})")

    print(f"\nDataset generado: {OUTPUT_PATH} ({written} ejemplos)")


if __name__ == "__main__":
    asyncio.run(main())