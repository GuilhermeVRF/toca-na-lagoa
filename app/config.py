"""Application-wide constants and environment-driven settings."""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_DIR / "data"))
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", PROJECT_DIR / "frontend" / "dist"))
DATABASE_URL = f"sqlite:///{DATA_DIR / 'apto-pampulha.db'}"

TIMEZONE = ZoneInfo(os.environ.get("TZ", "America/Sao_Paulo"))
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
REQUEST_TIMEOUT_SECONDS = 30.0
SECONDS_BETWEEN_REQUESTS = 1.5

DEFAULT_NEIGHBORHOODS = [
    "Pampulha",
    "São Luiz",
    "Ouro Preto",
    "Castelo",
    "Itapoã",
    "Santa Amélia",
    "Jaraguá",
    "Liberdade",
    "São José",
    "Bandeirantes",
    "Santa Rosa",
    "Dona Clara",
    "Santa Terezinha",
    "Universitário",
    "Aeroporto",
    "Indaiá",
    "Garças",
    "Braúnas",
    "Trevo",
    "Paquetá",
    "Engenho Nogueira",
    "Santa Branca",
    "Itatiaia",
    "Manacás",
    "Jardim Atlântico",
]

SOURCE_LABELS: dict[str, str] = {
    "quintoandar": "QuintoAndar",
    "zap": "ZAP",
    "vivareal": "VivaReal",
    "netimoveis": "Netimóveis",
}

KIND_LABELS: dict[str, str] = {
    "apartment": "Apartamento",
    "studio": "Studio/Kitnet",
    "loft": "Loft",
    "flat": "Flat",
    "penthouse": "Cobertura",
}
