# Wanderlust Backend — Setup rápido (sin Docker)

## 1. Entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y pon tu API key de Groq (consigue una gratis en https://console.groq.com → API Keys):

```
GROQ_API_KEY=gsk_tu-clave-real
```

No necesitas tocar `DATABASE_URL` — usa SQLite por defecto (`wanderlust.db`, se crea solo).

## 3. (Opcional) Poblar RAG con datos de ejemplo

```bash
python -m scripts.seed_rag
```

Esto crea las tablas y agrega información de Tokio, París y Cartagena para que RAG tenga contexto real.

## 4. Levantar el servidor

```bash
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Docs interactivas: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

Las tablas se crean automáticamente al iniciar (no se requiere Alembic).

## 5. Probar generación de itinerario desde /docs

1. Abre `/docs`
2. Expande `POST /api/v1/itineraries/generate`
3. "Try it out" con un body como:

```json
{
  "preferences": {
    "destination": "Tokio, Japón",
    "duration": 3,
    "budget": 1500,
    "budgetType": "moderate",
    "interests": ["cultural", "food"],
    "restrictions": "",
    "travelStyle": "balanced",
    "groupType": "solo"
  }
}
```

Si responde con un JSON de itinerario completo, Groq está conectado correctamente.

## Notas
- SQLite es solo para desarrollo. El archivo `wanderlust.db` se crea en la raíz del proyecto.
- Si necesitas borrar/reiniciar la base, simplemente elimina `wanderlust.db` y reinicia el servidor.
