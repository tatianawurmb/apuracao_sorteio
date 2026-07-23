"""Encerra o processo do app sozinho quando a última aba do navegador fecha.

O Streamlit conta, em tempo real, quantas sessões têm uma conexão websocket
ativa (isto é, quantas abas do navegador estão de fato abertas nele) — a
contagem cai assim que uma aba fecha ou navega para outro endereço, sem
esperar nenhum timeout de reconexão. Rodamos uma thread em segundo plano que
observa essa contagem; quando ela chega a zero, aguardamos uma janela de
tolerância (para sobreviver a um F5, por exemplo) e, se continuar em zero,
encerramos o processo — dispensando o usuário de precisar rodar um script
separado para "desligar" o app.

Como a conexão é sempre localhost-localhost (nunca passa por rede/Wi-Fi/proxy),
o cenário de uma reconexão automática do Streamlit deixando uma sessão "órfã"
pendurada é bem improvável — esse mecanismo só existe para lidar com quedas de
rede, que não acontecem em loopback. Ainda assim, o `Encerrar Apuracao.bat`
continua disponível como forma manual de encerrar, caso a detecção automática
não dispare por algum motivo.
"""
from __future__ import annotations

import os
import threading
import time

_iniciado = False
_trava = threading.Lock()


def iniciar_se_necessario(tolerancia_s: int = 25, intervalo_s: int = 3) -> None:
    """Inicia a thread de vigia uma única vez por processo (idempotente —
    seguro de chamar a cada rerun do script, como o Streamlit faz)."""
    global _iniciado
    with _trava:
        if _iniciado:
            return
        _iniciado = True

    def _contar_sessoes_ativas() -> int:
        import streamlit.runtime as st_runtime

        if not st_runtime.exists():
            return 0
        runtime = st_runtime.get_instance()
        # num_active_sessions() vive no SessionManager interno do Runtime, não é
        # exposto como método público do próprio Runtime nesta versão do Streamlit.
        return runtime._session_mgr.num_active_sessions()

    def vigiar() -> None:
        viu_sessao = False
        tempo_sem_sessao = 0.0
        while True:
            time.sleep(intervalo_s)
            try:
                n = _contar_sessoes_ativas()
            except Exception:
                n = 0
            if n > 0:
                viu_sessao = True
                tempo_sem_sessao = 0.0
                continue
            if not viu_sessao:
                continue  # ainda esperando a primeira aba conectar — não conta como "fechou"
            tempo_sem_sessao += intervalo_s
            if tempo_sem_sessao >= tolerancia_s:
                os._exit(0)  # encerramento imediato do processo, sem cleanup

    threading.Thread(target=vigiar, name="apuracao-encerramento-auto", daemon=True).start()
