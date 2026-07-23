"""Parsing dos arquivos de sorteio (largura fixa) e de comercializados (delimitado por ';')."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple, Union

Arquivo = Union[str, object]  # caminho (str) ou objeto tipo-arquivo (ex: UploadedFile do Streamlit)


class ParseError(ValueError):
    """Erro de formato em um dos arquivos de entrada, com mensagem amigável para exibição."""


def _ler_linhas(arquivo: Arquivo, encoding: str = "latin-1") -> Iterator[str]:
    if hasattr(arquivo, "read"):
        raw = arquivo.read()
        if isinstance(raw, bytes):
            raw = raw.decode(encoding)
        for linha in raw.splitlines():
            yield linha
    else:
        with open(arquivo, encoding=encoding) as f:
            for linha in f:
                yield linha.rstrip("\r\n")


def _parse_dezenas(raw: str) -> frozenset:
    raw = raw.strip()
    dezenas = set()
    for i in range(0, len(raw), 2):
        par = raw[i:i + 2]
        if not par.strip():
            continue
        if not par.isdigit():
            raise ParseError(f"dezena inválida '{par}' no bloco de dezenas")
        dezenas.add(int(par))
    return frozenset(dezenas)


def mask_de_dezenas(dezenas) -> int:
    """Converte uma coleção de dezenas (ints) em um bitmask (bit d ligado para cada dezena d)."""
    mask = 0
    for d in dezenas:
        mask |= 1 << d
    return mask


def dezenas_de_mask(mask: int) -> Tuple[int, ...]:
    """Inverso de mask_de_dezenas: retorna as dezenas em ordem crescente."""
    return tuple(d for d in range(100) if mask >> d & 1)


def _codigo_premio(premio_raw: str) -> Optional[str]:
    """'001' -> 'E001'; Rodada da Sorte ('R1') / Pifadinha ('F01') / lixo -> None (ignorados)."""
    premio_raw = premio_raw.strip()
    if not premio_raw or not premio_raw.isdigit():
        return None
    return f"E{int(premio_raw):03d}"


@dataclass
class Extracao:
    codigo: str
    dezenas: frozenset
    propostas_premiadas: int


@dataclass
class GabaritoItem:
    certificado: str
    numero_sorte: str
    dezenas: frozenset
    cpf: str = ""
    nome: str = ""


@dataclass
class SorteioData:
    header: dict
    extracoes: Dict[str, Extracao] = field(default_factory=dict)
    gabarito: Dict[str, List[GabaritoItem]] = field(default_factory=dict)
    avisos: List[str] = field(default_factory=list)

    def codigos_extracoes(self) -> List[str]:
        return sorted(self.extracoes.keys())


@dataclass
class ComercializadosData:
    # cada cartela: (certificado, numero_sorte, mask de dezenas)
    cartelas: List[Tuple[str, str, int]] = field(default_factory=list)
    total_titulos: int = 0
    versao_layout: str = ""  # versão informada no header do próprio arquivo, quando presente
    avisos: List[str] = field(default_factory=list)


def _detectar_layout(header_linha: str, linhas: List[str]) -> str:
    """Decide se o arquivo segue o layout '01' ou '02' (larguras diferentes do campo
    premio nos registros E/D). Prioriza o campo 'Versão do Layout' do header; como esse
    campo nem sempre vem preenchido na prática, cai para um 'sniff' no primeiro registro
    E do arquivo, testando qual largura de premio (3 ou 1) produz um campo de propostas
    premiadas (6 dígitos) totalmente numérico.
    """
    versao = header_linha[64:66].strip() if header_linha else ""
    if versao in ("01", "02"):
        return versao
    primeira_e = next((l for l in linhas if l and l[0] == "E"), "")
    if primeira_e:
        for largura in (3, 1):
            propostas = primeira_e[1 + largura:1 + largura + 6]
            if propostas.isdigit():
                return "02" if largura == 3 else "01"
    return "02"  # default: layout mais novo/completo


def parse_sorteio(arquivo: Arquivo) -> SorteioData:
    """Lê o arquivo de Ata de Sorteio (Arquivo 03 do manual, ex: 'prefixo.sorteio...') e
    separa header, extrações (registros E de prêmios principais) e gabarito (registros D
    de prêmios principais). Registros de Rodada da Sorte / Pifadinha (premio não numérico)
    são ignorados, conforme solicitado.

    Suporta os dois layouts documentados (versão '01' e '02' do manual): a diferença está
    na largura do campo 'premio' nos registros E/D (1 ou 3 caracteres) e na presença dos
    campos CPF/Nome do comprador no registro D (só existem na versão '02'). A versão é
    detectada automaticamente via `_detectar_layout`.

    Levanta ParseError com número da linha para arquivos malformados; problemas não
    fatais (versão ausente no header, trailer divergente) viram entradas em `avisos`.
    """
    linhas = list(_ler_linhas(arquivo))
    header_linha = next((l for l in linhas if l and l[0] == "H"), "")
    if not header_linha:
        raise ParseError("arquivo de Ata de Sorteio sem registro Header ('H') — o arquivo está no formato esperado?")
    layout = _detectar_layout(header_linha, linhas)
    largura_premio = 3 if layout == "02" else 1

    header: dict = {}
    extracoes: Dict[str, Extracao] = {}
    gabarito: Dict[str, List[GabaritoItem]] = {}
    avisos: List[str] = []
    trailer_qtd: Optional[int] = None
    total_registros = 0

    for num, linha in enumerate(linhas, start=1):
        if not linha:
            continue
        total_registros += 1
        tipo = linha[0]
        try:
            if tipo == "H":
                header = {
                    "nome_empresa": linha[1:16].strip(),
                    "cnpj": linha[16:31].strip(),
                    "data_gravacao": linha[31:39].strip(),
                    "data_sorteio": linha[39:47].strip(),
                    "codigo_susep": linha[47:64].strip(),
                    "versao_layout": linha[64:66].strip(),
                    "layout_detectado": layout,
                }
            elif tipo == "E":
                pos = 1 + largura_premio
                codigo = _codigo_premio(linha[1:pos])
                if codigo is None:
                    continue
                propostas = int(linha[pos:pos + 6].strip() or 0)
                dezenas = _parse_dezenas(linha[pos + 6:pos + 6 + 120])
                extracoes[codigo] = Extracao(codigo=codigo, dezenas=dezenas, propostas_premiadas=propostas)
            elif tipo == "D":
                pos = 1 + largura_premio
                codigo = _codigo_premio(linha[1:pos])
                if codigo is None:
                    continue
                certificado = linha[pos:pos + 8].strip()
                pos += 8
                numero_sorte = linha[pos:pos + 8].strip()
                pos += 8
                dezenas = _parse_dezenas(linha[pos:pos + 40])
                pos += 40
                cpf = nome = ""
                if layout == "02":
                    cpf = linha[pos:pos + 11].strip()
                    nome = linha[pos + 11:pos + 11 + 70].strip()
                gabarito.setdefault(codigo, []).append(
                    GabaritoItem(certificado=certificado, numero_sorte=numero_sorte, dezenas=dezenas, cpf=cpf, nome=nome)
                )
            elif tipo == "T":
                qtd_raw = linha[1:10].strip()
                if qtd_raw.isdigit():
                    trailer_qtd = int(qtd_raw)
        except ParseError as e:
            raise ParseError(f"Ata de Sorteio, linha {num}: {e}") from e
        except ValueError as e:
            raise ParseError(f"Ata de Sorteio, linha {num}: valor numérico inválido ({e})") from e

    versao_header = header.get("versao_layout", "")
    if not versao_header:
        avisos.append(f"O header da Ata de Sorteio não informa a versão do layout — versão {layout} detectada automaticamente pela estrutura dos registros.")
    elif versao_header not in ("01", "02"):
        avisos.append(f"Versão de layout '{versao_header}' não reconhecida no header da Ata de Sorteio — usando detecção automática (layout {layout}). Confira os resultados.")

    if trailer_qtd is not None and trailer_qtd != total_registros:
        avisos.append(
            f"O trailer da Ata de Sorteio indica {trailer_qtd} registros, mas o arquivo tem {total_registros} — o arquivo pode estar truncado ou corrompido."
        )
    elif trailer_qtd is None:
        avisos.append("A Ata de Sorteio não tem registro Trailer ('T') — não foi possível conferir a integridade do arquivo.")

    return SorteioData(header=header, extracoes=extracoes, gabarito=gabarito, avisos=avisos)


def parse_comercializados(arquivo: Arquivo) -> ComercializadosData:
    """Lê o arquivo de comercializados e retorna cartelas + totais + avisos de integridade.

    cartelas: lista de (certificado, numero_sorte, mask) — uma entrada por cartela, onde
    mask é um bitmask das 20 dezenas (bit d ligado para cada dezena d).

    Layout dos campos (delimitados por ';'), verificado com dados reais:
    - campo 3 (índice 2) = Título/Número Certificado — o que corresponde ao 'certificado'
      da Ata de Sorteio;
    - cada cartela é um campo de exatamente 40 dígitos (20 dezenas); o campo imediatamente
      antes de cada cartela é o Número da Sorte / Proposta daquela cartela;
    - um título pode ter 1 ou mais cartelas, e o número/posição dos campos varia entre
      versões do arquivo.

    (Obs.: em alguns arquivos o certificado e o número da sorte coincidem; em outros
    diferem — por isso é essencial ler cada um do seu campo próprio.)

    total_titulos: quantidade de registros de detalhe ('D'), ou seja, títulos
    comercializados. Valida contagens do header (campo 5, quando preenchido) e do
    trailer ('T;<total>;') contra o que foi lido, gerando avisos em divergência.
    """
    dados = ComercializadosData()
    header_qtd: Optional[int] = None
    trailer_qtd: Optional[int] = None
    total_registros = 0

    for linha in _ler_linhas(arquivo):
        if not linha:
            continue
        total_registros += 1
        tipo = linha[0]
        if tipo == "H":
            campos = linha.split(";")
            if len(campos) > 4 and campos[4].strip().isdigit():
                header_qtd = int(campos[4].strip())
            if len(campos) > 7:
                dados.versao_layout = campos[7].strip()
        elif tipo == "D":
            dados.total_titulos += 1
            campos = linha.split(";")
            if len(campos) < 8:
                continue
            certificado = campos[2].strip()  # Título/Número Certificado
            for i in range(7, len(campos), 2):
                bloco = campos[i].strip()
                if len(bloco) != 40 or not bloco.isdigit():
                    continue  # não é um bloco de dezenas válido (cartela ausente, ou outro campo do layout)
                numero_sorte = campos[i - 1].strip()  # campo imediatamente antes da cartela
                mask = 0
                for j in range(0, 40, 2):
                    mask |= 1 << int(bloco[j:j + 2])
                dados.cartelas.append((certificado, numero_sorte, mask))
        elif tipo == "T":
            campos = linha.split(";")
            if len(campos) > 1 and campos[1].strip().isdigit():
                trailer_qtd = int(campos[1].strip())

    if header_qtd and header_qtd != dados.total_titulos:
        dados.avisos.append(
            f"O header do arquivo de Comercializados indica {header_qtd:,} títulos, mas foram lidos {dados.total_titulos:,} — o arquivo pode estar truncado.".replace(",", ".")
        )
    if trailer_qtd is not None and trailer_qtd != total_registros:
        dados.avisos.append(
            f"O trailer do arquivo de Comercializados indica {trailer_qtd:,} registros, mas o arquivo tem {total_registros:,} — o arquivo pode estar truncado.".replace(",", ".")
        )

    return dados


_EDICAO_RE = re.compile(r"^([^.\s]+)\.[^.\s]+\.(\d{5})\.")


def extrair_edicao(nome_arquivo: str) -> Optional[str]:
    """Extrai a edição do sorteio a partir do nome do arquivo, no formato
    PREFIXO.SÉRIE (ex: 'trica.comercializadas.00393.100526.txt' -> 'TRICA.00393').
    A série tem sempre 5 dígitos (Nomenclatura 2/3 do manual). Nomes sem série
    (Nomenclatura 1, ex: 'prefixo.sorteio.ddmmaa.txt') não têm edição extraível
    daqui — retorna None, e quem chama deve cair em outro dado (ex: data do sorteio).
    """
    if not nome_arquivo:
        return None
    base = nome_arquivo.replace("\\", "/").rsplit("/", 1)[-1]
    m = _EDICAO_RE.match(base)
    if not m:
        return None
    prefixo, serie = m.groups()
    return f"{prefixo.upper()}.{serie}"
