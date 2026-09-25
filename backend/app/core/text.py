import re
import unicodedata

# Caractères que la décomposition Unicode ne sait pas ramener à des lettres simples.
_TRANSLITERATIONS = str.maketrans({"ß": "ss", "æ": "ae", "œ": "oe", "ø": "o", "đ": "d", "ł": "l"})

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def slugify(value: str, max_length: int = 160) -> str:
    """Transforme un texte en slug d'URL : « Chambre Vue Mer » → « chambre-vue-mer »."""
    text = value.lower().translate(_TRANSLITERATIONS)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    slug = _NON_ALPHANUMERIC.sub("-", text).strip("-")
    return slug[:max_length].rstrip("-")
