from typing import List
from config import load_config
cfg = load_config()

def suggest_hashtags(title: str, genre: str | None = None) -> List[str]:
    if not cfg.OPENAI_API_KEY:
        # fallback defaults
        base = ["#etronics", "#новыйтрек", "#newmusic"]
        if genre:
            base.append(f"#{genre}")
        return base + ["#music", "#release"]
    try:
        from openai import OpenAI
        client = OpenAI(api_key=cfg.OPENAI_API_KEY)
        prompt = f"Подбери 8 коротких хэштегов для музыкального релиза. Название: {title}. Жанр: {genre or 'unknown'}. Пиши без чисел, латиница/кириллица вперемешку, без пробелов, 1 слово в теге."
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], temperature=0.7)
        text = resp.choices[0].message.content
        tags = [t.strip() for t in text.replace("\n"," ").split() if t.startswith("#")]
        return tags[:8] or ["#music"]
    except Exception:
        return ["#etronics", "#music"]
