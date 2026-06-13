"""
Servicio LLM local que carga TinyLlama-1.1B-Chat + el adaptador LoRA
fine-tuneado en el dataset propio de itinerarios (punto 5 del enunciado).

Aislado del flujo principal (que usa Groq) para no afectar latencia/calidad
de producción. Se expone mediante un endpoint separado de demostración.

NOTA: la inferencia en CPU es lenta (puede tardar 1-3 minutos). Es normal.
"""
import json
from pathlib import Path

from app.domain.entities.itinerary import (
    Activity,
    ActivityType,
    BudgetType,
    DayPlan,
    Itinerary,
    PracticalInfo,
    TravelPreferences,
)

BASE_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
ADAPTER_PATH = Path(__file__).resolve().parents[3] / "ml" / "lora-itinerary-adapter"

SYSTEM_PROMPT = "Eres un planificador de viajes experto. Responde solo con JSON."


class LocalLoraLLMService:
    """Carga el modelo una sola vez (lazy) y genera itinerarios localmente."""

    _model = None
    _tokenizer = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        if not ADAPTER_PATH.exists():
            raise RuntimeError(
                f"No se encontró el adaptador LoRA en {ADAPTER_PATH}. "
                "Descomprime lora-itinerary-adapter.zip en backend/ml/."
            )

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from peft import PeftModel
        except ImportError as e:
            raise RuntimeError(
                "Dependencias de fine-tuning no instaladas. "
                "Instala con: pip install torch transformers peft"
            ) from e

        tokenizer = AutoTokenizer.from_pretrained(str(ADAPTER_PATH))
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            torch_dtype=torch.float32,  # CPU: float32 es más estable que float16
            device_map="cpu",
        )
        model = PeftModel.from_pretrained(base_model, str(ADAPTER_PATH))
        model.eval()

        type(self)._model = model
        type(self)._tokenizer = tokenizer

    def _build_prompt(self, preferences: TravelPreferences) -> str:
        return (
            f"<|system|>\n{SYSTEM_PROMPT}\n"
            f"<|user|>\nGenera un itinerario de viaje para {preferences.destination}, "
            f"{preferences.duration} días, presupuesto {preferences.budget} USD "
            f"({preferences.budget_type.value}), intereses: {', '.join(preferences.interests)}, "
            f"estilo {preferences.travel_style}, viajero(s): {preferences.group_type}.\n"
            f"<|assistant|>\n"
        )

    def generate_itinerary(self, preferences: TravelPreferences) -> Itinerary:
        self._ensure_loaded()
        import torch

        prompt = self._build_prompt(preferences)
        inputs = self._tokenizer(prompt, return_tensors="pt")

        with torch.no_grad():
            output = self._model.generate(
                **inputs,
                max_new_tokens=700,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        full_text = self._tokenizer.decode(output[0], skip_special_tokens=True)
        raw_json = self._extract_json(full_text, prompt)
        return self._parse_itinerary(raw_json, preferences)

    @staticmethod
    def _extract_json(full_text: str, prompt: str) -> str:
        # El texto generado incluye el prompt; nos quedamos solo con lo nuevo.
        generated = full_text[len(prompt):] if full_text.startswith(prompt) else full_text

        # Busca el primer bloque { ... } balanceado
        start = generated.find("{")
        if start == -1:
            raise ValueError(f"El modelo no generó JSON. Salida cruda:\n{generated[:500]}")

        depth = 0
        for i, ch in enumerate(generated[start:], start=start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return generated[start:i + 1]

        raise ValueError(f"JSON incompleto/truncado en la salida del modelo:\n{generated[:500]}")

    @staticmethod
    def _parse_itinerary(raw: str, preferences: TravelPreferences) -> Itinerary:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON inválido del modelo fine-tuneado: {e}\nRaw: {raw[:500]}")

        days = [
            DayPlan(
                day=d["day"],
                title=d["title"],
                theme=d["theme"],
                daily_budget=float(d["dailyBudget"]),
                activities=[
                    Activity(
                        time=a["time"],
                        title=a["title"],
                        description=a["description"],
                        type=ActivityType(a["type"]),
                        cost=float(a["cost"]),
                        tip=a.get("tip"),
                    )
                    for a in d["activities"]
                ],
            )
            for d in data["days"]
        ]

        practical = data["practicalInfo"]

        return Itinerary(
            id=None,
            user_id=None,
            destination=data["destination"],
            total_days=int(data["totalDays"]),
            total_estimated_cost=float(data["totalEstimatedCost"]),
            summary=data["summary"],
            highlights=data.get("highlights", []),
            days=days,
            practical_info=PracticalInfo(
                best_time_to_visit=practical["bestTimeToVisit"],
                currency=practical["currency"],
                language=practical["language"],
                transportation=practical["transportation"],
                accommodation=practical["accommodation"],
            ),
            preferences=preferences,
        )
