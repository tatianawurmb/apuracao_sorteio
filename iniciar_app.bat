@echo off
setlocal
cd /d "%~dp0"
set "PORTA=8510"
set "VENV=%~dp0.venv"

echo ============================================
echo   Apuracao de Sorteio - Iniciando o app
echo ============================================
echo.

rem ---- Localizar o Python (py launcher ou python no PATH) ----
set "PYTHON="
where py >nul 2>nul && set "PYTHON=py"
if not defined PYTHON where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON goto :sem_python

rem ---- Validar que nao e o alias falso da Microsoft Store ----
%PYTHON% --version >nul 2>nul
if errorlevel 1 goto :sem_python

rem ---- Criar ambiente virtual na primeira execucao ----
if exist "%VENV%\Scripts\python.exe" goto :venv_ok
echo Preparando o ambiente (apenas na primeira execucao)...
%PYTHON% -m venv "%VENV%"
if errorlevel 1 (
    echo ERRO: nao foi possivel criar o ambiente virtual.
    pause
    exit /b 1
)
:venv_ok
set "VPY=%VENV%\Scripts\python.exe"

rem ---- Instalar dependencias apenas se ainda nao instaladas ----
"%VPY%" -c "import streamlit, pandas, openpyxl" >nul 2>nul
if not errorlevel 1 goto :deps_ok
echo Instalando dependencias (streamlit, pandas, openpyxl)...
"%VPY%" -m pip install -r apuracao_app\requirements.txt
if errorlevel 1 (
    echo.
    echo ERRO ao instalar as dependencias. Se a rede corporativa bloqueia o PyPI,
    echo use o pacote autocontido (ver LEIA-ME) em vez deste script.
    pause
    exit /b 1
)
:deps_ok

echo.
echo Iniciando o app... O navegador abrira automaticamente em instantes.
echo Para encerrar, feche esta janela (ou pressione Ctrl+C).
echo.
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:%PORTA%"
"%VPY%" -m streamlit run apuracao_app\app.py --server.port %PORTA%
pause
exit /b 0

:sem_python
echo Python nao foi encontrado neste computador.
echo.
echo 1. Baixe e instale o Python em https://www.python.org/downloads/
echo    (a instalacao "para o usuario atual" nao exige administrador)
echo 2. IMPORTANTE: marque a opcao "Add python.exe to PATH" durante a instalacao.
echo 3. Depois de instalar, execute este arquivo novamente.
echo.
pause
exit /b 1
