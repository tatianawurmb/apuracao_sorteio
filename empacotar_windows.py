#!/usr/bin/env python3
"""Monta um pacote Windows autocontido do app de Apuração de Sorteio.

Rode este script UMA VEZ, numa máquina com acesso à internet (Mac, Linux ou Windows):

    python3 empacotar_windows.py

Ele produz `dist/ApuracaoSorteio.zip` contendo:
  - python/   -> Python embeddable (Windows 64 bits), sem instalação
  - wheels/   -> todas as dependências baixadas como wheels (instalação offline)
  - app/      -> o código do app (app.py, parsers.py, apuracao.py, config)
  - "Iniciar Apuracao.bat" -> primeira execução instala offline e abre o navegador
  - LEIA-ME.txt

O usuário final só precisa descompactar o zip e dar duplo clique no .bat —
não precisa de internet, de direitos de administrador nem de Python instalado.
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

PY_EMBED_VERSION = "3.12.8"
PY_EMBED_URL = (
    f"https://www.python.org/ftp/python/{PY_EMBED_VERSION}/"
    f"python-{PY_EMBED_VERSION}-embed-amd64.zip"
)
PY_TAG = "3.12"  # para o pip download (--python-version)

RAIZ = os.path.dirname(os.path.abspath(__file__))
APP_ORIGEM = os.path.join(RAIZ, "apuracao_app")
DIST = os.path.join(RAIZ, "dist")
PACOTE = os.path.join(DIST, "ApuracaoSorteio")

BAT_CONTEUDO = r"""@echo off
setlocal
cd /d "%~dp0"
set "PORTA=8510"
set "PY=%~dp0python\python.exe"

echo ============================================
echo   Apuracao de Sorteio
echo ============================================
echo.

if exist "python\Lib\site-packages\streamlit" goto :rodar

echo Primeira execucao: instalando componentes (nao precisa de internet)...
set "PIPWHL="
for %%W in ("wheels\pip-*.whl") do set "PIPWHL=%%~W"
if not defined PIPWHL (
    echo ERRO: wheel do pip nao encontrada na pasta wheels.
    pause
    exit /b 1
)
"%PY%" "%PIPWHL%\pip" install --no-index --find-links wheels --no-warn-script-location -r app\requirements.txt
if errorlevel 1 (
    echo ERRO na instalacao dos componentes. Veja a mensagem acima.
    pause
    exit /b 1
)
echo Instalacao concluida.
echo.

:rodar
echo Iniciando o app... O navegador abrira automaticamente quando estiver pronto.
echo Se nao abrir, acesse manualmente: http://localhost:%PORTA%
echo Para encerrar, feche esta janela (ou pressione Ctrl+C).
echo.
"%PY%" -m streamlit run app\app.py --server.port %PORTA%
pause
"""

LEIAME = """APURACAO DE SORTEIO - PACOTE AUTOCONTIDO PARA WINDOWS
======================================================

COMO USAR
1. Copie a pasta "ApuracaoSorteio" inteira para o computador. Prefira um
   caminho curto e sem acentos (ex: C:\\ApuracaoSorteio) para evitar o limite
   de tamanho de caminho do Windows.
2. De um duplo clique em "Iniciar Apuracao.bat".
   - Na primeira execucao, o app instala seus componentes (leva ~1 minuto,
     sem precisar de internet nem de administrador).
   - Se o Windows mostrar um aviso azul do "Windows protegeu o computador"
     (SmartScreen), clique em "Mais informacoes" e depois "Executar assim mesmo".
3. O navegador abre automaticamente em http://localhost:8510 com o app.
   Se nao abrir sozinho, digite esse endereco no navegador.
4. Para encerrar o app, feche a janela preta (prompt de comando).

OBSERVACOES
- O app roda 100% local: aceita conexoes apenas do proprio computador
  (localhost) e nao envia nenhum dado para fora.
- Os arquivos de sorteio/comercializados podem ser indicados por upload
  ou apontando a pasta onde eles estao.
- Se a porta 8510 estiver em uso por outro programa, edite a linha
  "set PORTA=8510" no arquivo .bat para outra porta (ex: 8511).
"""


def baixar(url: str, destino: str) -> None:
    print(f"Baixando {url} ...")
    urllib.request.urlretrieve(url, destino)


def _dependencias_faltando_no_windows(wheels_dir: str) -> set:
    """`pip download` avalia marcadores de ambiente (platform_system, sys_platform,
    os_name) usando o Python que RODA o pip — não o alvo (win_amd64) — mesmo com
    --platform/--python-version. Por isso dependências condicionais por plataforma
    (ex: watchdog só fora do macOS, colorama só no Windows) somem silenciosamente
    ao empacotar a partir de um Mac. Esta função escaneia os .whl já baixados,
    procura esse tipo de marcador e retorna os nomes de pacote que provavelmente
    são necessários no Windows e ainda não foram baixados.
    """
    ja_baixados = {
        os.path.basename(w).split("-")[0].lower().replace("_", "-")
        for w in glob.glob(os.path.join(wheels_dir, "*.whl"))
    }
    faltando = set()
    for caminho in glob.glob(os.path.join(wheels_dir, "*.whl")):
        try:
            with zipfile.ZipFile(caminho) as z:
                meta_name = next((n for n in z.namelist() if n.endswith(".dist-info/METADATA")), None)
                if not meta_name:
                    continue
                conteudo = z.read(meta_name).decode("utf-8", errors="ignore")
        except (zipfile.BadZipFile, KeyError):
            continue
        for linha in conteudo.splitlines():
            if not linha.startswith("Requires-Dist:"):
                continue
            if "extra ==" in linha or "extra=='" in linha.replace(" ", ""):
                continue  # dependência de um "extra" opcional que não pedimos (ex: cudf)
            if not any(m in linha for m in ("platform_system", "sys_platform", "os_name")):
                continue
            # marcador que sugere "vale para Windows": menciona Windows/win32/nt,
            # ou exclui explicitamente outro SO (ex: != "Darwin", != "Linux")
            if not ("Windows" in linha or "win32" in linha or "'nt'" in linha or '"nt"' in linha or "!=" in linha):
                continue
            nome = linha[len("Requires-Dist:"):].split(";")[0].strip()
            nome = re.split(r"[\[<>=! ]", nome, maxsplit=1)[0].strip()
            nome_normalizado = nome.lower().replace("_", "-")
            if nome and nome_normalizado not in ja_baixados:
                faltando.add(nome)
    return faltando


def _garantir_dependencias_windows(wheels_dir: str) -> None:
    """Repete o escaneamento + download até nenhuma dependência condicional nova
    aparecer (uma dependência recém-baixada pode, por sua vez, ter as suas)."""
    for _ in range(5):
        faltando = _dependencias_faltando_no_windows(wheels_dir)
        if not faltando:
            return
        print(f"Dependências condicionais por plataforma encontradas: {sorted(faltando)}")
        subprocess.run(
            [
                sys.executable, "-m", "pip", "download", *sorted(faltando),
                "-d", wheels_dir,
                "--platform", "win_amd64",
                "--python-version", PY_TAG,
                "--only-binary=:all:",
            ],
            check=True,
        )
    raise RuntimeError("Muitas rodadas de dependências condicionais — verifique manualmente.")


def montar() -> None:
    if os.path.exists(PACOTE):
        shutil.rmtree(PACOTE)
    os.makedirs(PACOTE, exist_ok=True)

    # 1. Python embeddable
    py_dir = os.path.join(PACOTE, "python")
    os.makedirs(py_dir, exist_ok=True)
    zip_embed = os.path.join(DIST, f"python-{PY_EMBED_VERSION}-embed-amd64.zip")
    if not os.path.exists(zip_embed):
        baixar(PY_EMBED_URL, zip_embed)
    with zipfile.ZipFile(zip_embed) as z:
        z.extractall(py_dir)

    # 2. Habilitar site-packages no Python embeddable (descomentar 'import site' no ._pth)
    pth = next(f for f in os.listdir(py_dir) if f.endswith("._pth"))
    pth_path = os.path.join(py_dir, pth)
    with open(pth_path, encoding="utf-8") as f:
        conteudo = f.read()
    conteudo = conteudo.replace("#import site", "import site")
    with open(pth_path, "w", encoding="utf-8") as f:
        f.write(conteudo)
    print(f"site-packages habilitado em {pth}")

    # 3. Wheels das dependências (para Windows 64 bits) + o próprio pip
    wheels = os.path.join(PACOTE, "wheels")
    os.makedirs(wheels, exist_ok=True)
    requirements = os.path.join(APP_ORIGEM, "requirements.txt")
    subprocess.run(
        [
            sys.executable, "-m", "pip", "download",
            "-r", requirements,
            "-d", wheels,
            "--platform", "win_amd64",
            "--python-version", PY_TAG,
            "--only-binary=:all:",
        ],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "download", "pip", "-d", wheels, "--only-binary=:all:"],
        check=True,
    )

    _garantir_dependencias_windows(wheels)

    # 4. Código do app (sem caches/estado local)
    app_destino = os.path.join(PACOTE, "app")
    shutil.copytree(
        APP_ORIGEM,
        app_destino,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".last_folder.json"),
    )

    # 5. Launcher e LEIA-ME (CRLF para o Windows)
    with open(os.path.join(PACOTE, "Iniciar Apuracao.bat"), "w", encoding="ascii", newline="\r\n") as f:
        f.write(BAT_CONTEUDO)
    with open(os.path.join(PACOTE, "LEIA-ME.txt"), "w", encoding="ascii", newline="\r\n") as f:
        f.write(LEIAME)

    # 6. Zip final
    zip_final = os.path.join(DIST, "ApuracaoSorteio.zip")
    if os.path.exists(zip_final):
        os.remove(zip_final)
    with zipfile.ZipFile(zip_final, "w", zipfile.ZIP_DEFLATED) as z:
        for pasta, _dirs, arquivos in os.walk(PACOTE):
            for nome in arquivos:
                caminho = os.path.join(pasta, nome)
                z.write(caminho, os.path.relpath(caminho, DIST))

    tamanho_mb = os.path.getsize(zip_final) / 1024 / 1024
    print(f"\nPacote pronto: {zip_final} ({tamanho_mb:.0f} MB)")
    print("Distribua o zip; o usuario descompacta e da duplo clique em 'Iniciar Apuracao.bat'.")


if __name__ == "__main__":
    montar()
