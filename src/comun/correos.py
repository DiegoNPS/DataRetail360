"""Validación sintáctica de correos ASCII para el contrato académico.

No consulta DNS, no envía mensajes y no verifica la existencia del buzón.
Acepta dominios variados sin una lista de proveedores permitidos.
"""
import re

_LOCAL = re.compile(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+", re.ASCII)
_ETIQUETA = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", re.ASCII)
_TLD = re.compile(r"[A-Za-z]{2,63}", re.ASCII)


def correo_valido(valor):
    """Valida el subconjunto práctico documentado; no pretende cubrir todo RFC 5322."""
    if not isinstance(valor, str) or not valor or len(valor) > 254:
        return False
    if not valor.isascii() or any(c.isspace() for c in valor) or valor.count('@') != 1:
        return False
    local, dominio = valor.split('@')
    if not 1 <= len(local) <= 64 or not _LOCAL.fullmatch(local):
        return False
    if local.startswith('.') or local.endswith('.') or '..' in local:
        return False
    etiquetas = dominio.split('.')
    return (
        len(dominio) <= 253
        and len(etiquetas) >= 2
        and all(_ETIQUETA.fullmatch(e) is not None for e in etiquetas)
        and _TLD.fullmatch(etiquetas[-1]) is not None
    )
