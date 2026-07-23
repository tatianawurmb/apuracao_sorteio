"""Lógica de apuração: cruza as dezenas sorteadas de uma extração com as cartelas
comercializadas, e valida o resultado contra o gabarito da própria Ata de Sorteio."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from parsers import dezenas_de_mask, mask_de_dezenas


@dataclass
class CartelaVencedora:
    certificado: str
    numero_sorte: str
    dezenas: Tuple[int, ...]  # ordenadas


def apurar_extracao(
    dezenas_sorteadas: frozenset, cartelas: Iterable[Tuple[str, str, int]]
) -> List[CartelaVencedora]:
    """cartelas: iterável de (certificado, numero_sorte, mask_de_dezenas_da_cartela).
    Uma cartela é vencedora quando TODAS as suas dezenas estão nas dezenas sorteadas —
    em bitmask, quando `mask & sorteadas == mask`.
    """
    mask_sorteadas = mask_de_dezenas(dezenas_sorteadas)
    vencedoras = []
    for certificado, numero_sorte, mask in cartelas:
        if mask & mask_sorteadas == mask:
            vencedoras.append(
                CartelaVencedora(certificado=certificado, numero_sorte=numero_sorte,
                                 dezenas=dezenas_de_mask(mask))
            )
    return vencedoras


def validar_extracao(vencedoras: List[CartelaVencedora], gabarito: list) -> dict:
    """Compara os CERTIFICADOS apurados pelo programa com os certificados que constam
    oficialmente nos registros D (prêmios principais) da Ata de Sorteio.

    Comparação estrita certificado ↔ certificado: um certificado do gabarito é
    considerado "encontrado" somente se o mesmo certificado aparecer entre as cartelas
    vencedoras calculadas. (O número da sorte é apenas exibido nos resultados, não entra
    nesta validação — decidido assim porque a Ata pode apontar um giro diferente do que
    vence pela regra das dezenas.)
    """
    certs_calc = {v.certificado for v in vencedoras}
    certs_ata = {g.certificado for g in gabarito}
    cert_faltando = sorted(certs_ata - certs_calc)   # certificado da Ata sem ganhador apurado
    cert_extra = sorted(certs_calc - certs_ata)      # ganhador apurado fora da Ata
    return {
        "ok": not cert_faltando and not cert_extra,
        "cert_faltando": cert_faltando,
        "cert_extra": cert_extra,
        "qtd_esperada": len(certs_ata),
        "qtd_calculada": len(certs_calc),
    }
