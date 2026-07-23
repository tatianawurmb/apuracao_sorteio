# Manual do Usuário — Apuração de Sorteio (Windows)

Aplicativo para apurar sorteios de títulos de capitalização: a partir das dezenas
sorteadas de cada prêmio (arquivo **Ata de Sorteio**), ele identifica no arquivo de
**Comercializados** quais cartelas foram contempladas — prêmio por prêmio — e ainda
confere o resultado contra o gabarito da própria Ata.

O app roda **100% no seu computador** (localhost), não envia dados para fora e não
precisa de internet para funcionar.

---

## 1. Instalação

### Opção recomendada: pacote autocontido (sem instalar Python)

1. Copie a pasta **`ApuracaoSorteio`** (descompactada do arquivo `ApuracaoSorteio.zip`)
   para o computador. Prefira um caminho **curto e sem acentos**, por exemplo
   `C:\ApuracaoSorteio`, para evitar o limite de tamanho de caminho do Windows.
2. Dê um **duplo clique** em **`Iniciar Apuracao.bat`**.
3. Na **primeira execução**, o app instala seus componentes automaticamente
   (leva cerca de 1 minuto, **sem precisar de internet nem de administrador**).
   - Se o Windows exibir o aviso azul **"O Windows protegeu o computador"**
     (SmartScreen), clique em **"Mais informações"** e depois em **"Executar assim mesmo"**.
4. O navegador abre sozinho em **http://localhost:8510** com o aplicativo.
   Se não abrir, digite esse endereço manualmente no navegador.
5. Para **encerrar** o app, feche a janela preta (prompt de comando).

Nas próximas vezes, basta dar duplo clique no `Iniciar Apuracao.bat` de novo —
a instalação só acontece uma vez.

### Opção alternativa: a partir do código-fonte (requer Python)

Para quem tem Python instalado e acesso à internet corporativa liberado (PyPI):

1. Instale o Python de [python.org](https://www.python.org/downloads/), marcando
   **"Add python.exe to PATH"** durante a instalação.
2. Baixe o projeto e execute o **`iniciar_app.bat`** da raiz — ele cria um ambiente
   isolado, instala as dependências e abre o app.

---

## 2. Como usar — passo a passo

### Passo 1 — Indicar os arquivos

Na seção **"1. Arquivos de entrada"**, escolha como indicar os dois arquivos do sorteio:

- **Apontar pasta** *(recomendado)*: informe o caminho da pasta onde estão os arquivos.
  O app lista automaticamente os arquivos de **Ata de Sorteio** (`*.sorteio.*`) e de
  **Comercializados** (`*.comercializadas.*`) encontrados nela; basta selecionar o par
  correto nos menus suspensos. A última pasta usada fica lembrada para a próxima vez.
- **Upload manual**: envie os dois arquivos `.txt` diretamente pela tela.

> O app reconhece automaticamente os **dois layouts** de arquivo de Ata de Sorteio
> (versão 01 e versão 02) — você não precisa informar qual é.

### Passo 2 — Processar

Clique em **"▶️ Processar apuração"**. O app lê os arquivos (o de Comercializados pode
ser grande, então pode levar alguns segundos) e apura **todos os prêmios principais**
em sequência (1º, 2º, 3º, 4º prêmio...).

> Os resultados só aparecem **depois** de clicar no botão. Se você trocar a pasta ou o
> arquivo selecionado, clique em "Processar apuração" novamente para atualizar.

### Passo 3 — Ler o resultado

Na seção **"2. Resultado da apuração"** aparece primeiro um resumo com:

| Card | O que significa |
|------|-----------------|
| **Edição** | Identificação do sorteio (série, ou a data quando não há série no nome) |
| **Empresa** | Nome da entidade do produto |
| **Data do sorteio** | Data em que o sorteio ocorreu |
| **Versão do layout** | Layout do arquivo (`01`, `02`, ou detectado automaticamente) |
| **Títulos comercializados** | Quantidade de títulos no arquivo de Comercializados |
| **Cartelas comercializadas lidas** | Total de cartelas analisadas (um título pode ter mais de uma cartela) |

Em seguida, **um bloco para cada prêmio** mostra:

- A quantidade de **dezenas sorteadas** e a lista completa delas;
- Quantas **propostas premiadas** o arquivo indicava e quantas **cartelas vencedoras**
  o programa calculou;
- A **tabela dos certificados contemplados**, com o número do certificado e as
  20 dezenas de cada cartela vencedora;
- O resultado da **validação cruzada** (veja abaixo).

### Passo 4 — Exportar

Na seção **"3. Exportar"**, clique em **"⬇️ Baixar relatório em Excel"** para salvar um
relatório formatado (`apuracao_<edição>.xlsx`) com todas as informações e os
certificados contemplados de cada prêmio.

---

## 3. Entendendo a validação cruzada

Para cada prêmio, o app compara os certificados que **ele calculou** com os que constam
oficialmente na **Ata de Sorteio**:

- ✅ **Verde — "bate com o gabarito"**: o cálculo do programa coincide exatamente com a
  Ata. Resultado confiável.
- ⚠️ **Amarelo — "Divergência"**: o cálculo do programa **não** coincide com a Ata. O app
  mostra quais certificados estavam esperados (na Ata) e não foram encontrados, e quais
  foram encontrados mas não constam na Ata.

Uma divergência **não significa necessariamente erro do programa** — ela serve para
chamar a atenção. Causas comuns: diferença de digitação entre o certificado da Ata e o
do arquivo de Comercializados, arquivos de edições diferentes, ou arquivo incompleto.
Sempre que aparecer ⚠️, confira os dois arquivos.

O app também exibe **avisos** (faixa amarela no topo) quando detecta que um arquivo pode
estar truncado (contagem do rodapé não bate) ou quando a versão do layout foi detectada
automaticamente.

---

## 4. Problemas comuns

| Situação | O que fazer |
|----------|-------------|
| Aviso azul do SmartScreen ao abrir o `.bat` | Clique em "Mais informações" → "Executar assim mesmo". |
| O navegador não abriu sozinho | Abra o navegador e acesse `http://localhost:8510`. |
| "A porta 8510 já está em uso" | Feche outras janelas do app, ou edite a linha `set PORTA=8510` no `.bat` para outra porta (ex: 8511). |
| Nenhum arquivo aparece nos menus | Confirme que o caminho da pasta está correto e que os arquivos terminam em `.txt` com "sorteio" / "comercializad" no nome. |
| A instalação falhou na primeira execução | Use o **pacote autocontido** (não depende da internet corporativa). Se persistir, envie o texto da janela preta para o suporte. |

---

*Este app processa dados que podem conter informações pessoais (CPF, nome). Ele não
exibe esses dados na tela nem os inclui no relatório Excel, e não envia nada para fora
do computador.*
