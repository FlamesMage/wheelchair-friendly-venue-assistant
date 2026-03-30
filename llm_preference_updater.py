import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def update_preferences_with_llm(user_message: str, current_preferences: dict) -> dict:
    if not OPENROUTER_API_KEY:
        raise ValueError("Missing OPENROUTER_API_KEY in environment variables.")

    system_prompt = """
You are helping update search preferences for a Wheelchair-Friendly Venue Assistant.

Your job is to interpret the user's latest message and update the current preferences.

Rules:
1. Return ONLY valid JSON.
2. Do not include markdown or explanation.
3. Keep fields exactly as:
   - preferred_category
   - preferred_city
   - require_level_entry
   - require_accessible_toilet
   - require_wheelchair_space
   - require_accessible_parking
   - action
4. "action" must be one of:
   - "update_preferences"
   - "reset_search"
5. If the user wants to remove a requirement, set that field to false.
6. If the user does not mention a field, preserve the current value.
7. If the user changes category or city, update it.
8. If the user says reset/start over/new search, return action = "reset_search".
9. Do not invent new fields.

Example output:
{
  "preferred_category": "cafe",
  "preferred_city": "london",
  "require_level_entry": false,
  "require_accessible_toilet": false,
  "require_wheelchair_space": true,
  "require_accessible_parking": false,
  "action": "update_preferences"
}
""".strip()

    user_prompt = f"""
Current preferences:
{json.dumps(current_preferences)}

User message:
{user_message}
""".strip()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0
    }

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()

    # Try to parse JSON safely
    parsed = json.loads(content)
    return parsed