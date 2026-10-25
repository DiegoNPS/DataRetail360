"""Prueba pesada opcional: un fallo antes de publicar conserva Gold anterior."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.proceso import ejecutar_completo


BASE = RAIZ / "resultados" / "dataretail360.sqlite"


def huella(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


antes = huella(BASE)
try:
    ejecutar_completo(RAIZ, simular_fallo=True, informar=lambda mensaje: None)
except RuntimeError as error:
    assert "Fallo de prueba" in str(error)
else:
    raise AssertionError("No se produjo el fallo controlado")

despues = huella(BASE)
assert antes == despues, "La base Gold final cambió pese al fallo de publicación"
assert not (RAIZ / "resultados" / "carga_temporal.sqlite").exists()
print("RECUPERACION_OK")
