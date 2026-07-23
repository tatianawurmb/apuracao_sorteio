@echo off
set "PORTA=8510"
set "ACHOU="
rem So encerra se o processo na porta for Python (o app), nunca outro programa.
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /c:":%PORTA%" ^| findstr /c:"LISTENING"') do (
    tasklist /fi "pid eq %%P" 2>nul | findstr /i "python.exe" >nul && taskkill /F /PID %%P >nul 2>nul && set "ACHOU=1"
)
if defined ACHOU (
    echo Apuracao de Sorteio encerrada.
) else (
    echo O app nao estava em execucao.
)
timeout /t 2 >nul
