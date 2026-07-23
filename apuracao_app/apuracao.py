"""Lógica de apuração: cruza as dezenas sorteadas de uma extração com as cartelas
comercializadas, e valida o resultado contra o gabarito da própria Ata de Sorteio."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from parsers import dezenas_de_mask, mask_de_dezenas


@dataclass
class CartelaVencedora:
    certificado: str
    dezenas: Tuple[int, ...]  # ordenadas


def apurar_extracao(
    dezenas_sorteadas: frozenset, cartelas: Iterable[Tuple[str, int]]
) -> List[CartelaVencedora]:
    """cartelas: iterável de (certificado, mask_de_dezenas_da_cartela).
    Uma cartela é vencedora quando TODAS as suas dezenas estão nas dezenas sorteadas —
    em bitmask, quando `mask & sorteadas == mask`.
    """
    mask_sorteadas = mask_de_dezenas(dezenas_sorteadas)
    vencedoras = []
    for certificado, mask in cartelas:
        if mask & mask_sorteadas == mask:
            vencedoras.append(CartelaVencedora(certificado=certificado, dezenas=dezenas_de_mask(mask)))
    return vencedoras


def validar_extracao(vencedoras: List[CartelaVencedora], gabarito: list) -> dict:
    """Compara os certificados calculados com os registros D (prêmios principais) da
    própria Ata de Sorteio, usados como gabarito.

    Cada registro do gabarito traz dois identificadores (certificado e proposta/número
    da sorte) que, dependendo do arquivo, podem ser iguais ou diferentes — o que bate
    com o certificado do arquivo de comercializados varia. Por isso um registro do
    gabarito conta como "encontrado" se QUALQUER um dos dois aparecer entre os
    certificados calculados.
    """
    calculados = {v.certificado for v in vencedoras}
    esperados = {g.certificado for g in gabarito} | {g.numero_sorte for g in gabarito}
    nao_encontrados = [g for g in gabarito if g.certificado not in calculados and g.numero_sorte not in calculados]
    faltando = sorted({g.certificado for g in nao_encontrados})
    extras = sorted(calculados - esperados)
    return {
        "ok": not faltando and not extras,
        "faltando": faltando,
        "extras": extras,
        "qtd_esperada": len(gabarito),
        "qtd_calculada": len(calculados),
    }
