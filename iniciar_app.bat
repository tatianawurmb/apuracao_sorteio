@echo off
setlocal
cd /d "%~dp0"
set "PORTA=8510"
set "VENV=%~dp0.venv"

rem ---- Se o app ja esta rodando, apenas abre o navegador e sai ----
netstat -ano | findstr /c:":%PORTA%" | findstr /c:"LISTENING" >nul 2>nul
if not errorlevel 1 (
    start "" http://localhost:%PORTA%
    exit /b 0
)

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

rem ---- Inicia o servidor OCULTO (sem janela) via VBScript e fecha esta janela ----
rem Gera o VBScript ao lado do .bat (usa o Python do ambiente virtual).
echo Iniciando o app... aguarde alguns segundos.
set "VBS=%~dp0_servidor_dev.vbs"
> "%VBS%" echo Set sh = CreateObject("WScript.Shell")
>> "%VBS%" echo sh.CurrentDirectory = "%~dp0"
>> "%VBS%" echo sh.Run "cmd /c "".venv\Scripts\python.exe"" -m streamlit run apuracao_app\app.py --server.port %PORTA% ^> app_ultimo_log.txt 2^>^&1", 0, False
start "" "%VBS%"

rem ---- Aguarda o servidor responder (ate ~20s) ----
set /a TENT=0
:esperar
timeout /t 1 /nobreak >nul 2>nul
netstat -ano | findstr /c:":%PORTA%" | findstr /c:"LISTENING" >nul 2>nul
if not errorlevel 1 exit /b 0
set /a TENT+=1
if %TENT% LSS 20 goto :esperar

rem ---- Nao subiu (scripts .vbs podem estar bloqueados). Fallback: janela minimizada ----
start "Apuracao de Sorteio" /min "%VPY%" -m streamlit run apuracao_app\app.py --server.port %PORTA%
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
