# Registro técnico de alterações

## Segunda-feira, 18/05/2026 20:58:11 - Versão 1.1.4

**Problema identificado**

Após validar a spool do boleto com F2, não era necessário voltar para a lista da SP02 antes de imprimir. A impressão deve ocorrer diretamente na tela de detalhes do boleto, logo após a validação.

**O que foi alterado**

- Ajustada a validação da spool para permitir permanecer na tela de detalhes quando necessário.
- A validação da nota continua voltando com F12 após o F2.
- A validação do boleto permanece na tela de detalhes após o F2.
- Removido o foco extra na linha do boleto antes da impressão, pois o comando agora é enviado diretamente na tela de detalhes do boleto.
- Mantida a impressão por `Ctrl + Shift + F8` (`sendVKey(44)`) logo após copiar o nome sugerido do PDF.
- Atualizada a versão do projeto de `1.1.3` para `1.1.4` em backend, frontend, JSON de configuração e arquivo de versão.

**Arquivos alterados**

- `backend/flows/f110_boleto.py`
- `backend/settings.py`
- `embasa_settings.json`
- `interface/app.js`
- `interface/index.html`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

O sistema deve validar a nota, voltar para a lista, validar o boleto e imprimir diretamente da própria tela de detalhes do boleto, evitando um retorno desnecessário e reduzindo risco de perder o foco correto.

**Validação realizada**

- `python -m py_compile backend\flows\f110_boleto.py backend\flows\f110.py backend\settings.py`
- Importação local de `finalizar_boleto_f110`, `montar_nome_pdf_sugerido` e leitura da versão `1.1.4`.

## Segunda-feira, 18/05/2026 20:49:01 - Versão 1.1.3

**Problema identificado**

O fluxo de impressão da SP02 precisava validar o par completo do boleto antes do comando de impressão: primeiro a spool `Nota acompanh.ISD &` e depois a spool `BOLETO (CONTAS A RECEBER)`. Também não deveria marcar checkbox na lista antes de imprimir.

**O que foi alterado**

- Ajustada a localização da SP02 para retornar o par `Nota acompanh.ISD &` seguido imediatamente por `BOLETO (CONTAS A RECEBER)`.
- A validação com F2 agora ocorre primeiro na nota e depois no boleto.
- Removida a etapa de marcar/desmarcar checkbox da linha na lista da SP02.
- Após validar o boleto, o script apenas foca a linha do boleto e executa `Ctrl + Shift + F8` (`sendVKey(44)`).
- Mantida a cópia automática do nome sugerido do PDF antes da impressão.
- Atualizada a versão do projeto de `1.1.2` para `1.1.3` em backend, frontend, JSON de configuração e arquivo de versão.

**Arquivos alterados**

- `backend/flows/f110_boleto.py`
- `backend/settings.py`
- `embasa_settings.json`
- `interface/app.js`
- `interface/index.html`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

O sistema deve conferir a nota e o boleto em sequência, garantir que o boleto pertence ao par correto mais recente e imprimir sem alterar checkboxes da lista da SP02.

**Validação realizada**

- `python -m py_compile backend\flows\f110_boleto.py backend\flows\f110.py backend\settings.py`
- Importação local de `finalizar_boleto_f110`, `montar_nome_pdf_sugerido` e leitura da versão `1.1.3`.

## Segunda-feira, 18/05/2026 20:37:39 - Versão 1.1.2

**Problema identificado**

A identificação da spool correta na SP02 precisava deixar explícito que a verificação deve ocorrer em ordem decrescente, priorizando a spool mais recente/maior número antes de qualquer registro antigo.

**O que foi alterado**

- Ajustada a coleta de linhas da SP02 para ordenar as linhas válidas pelo número da spool em ordem decrescente.
- Ajustada a lista de candidatas `BOLETO (CONTAS A RECEBER)` para também seguir ordem decrescente antes da validação do par `Nota acompanh.ISD &` → boleto.
- Atualizada a versão do projeto de `1.1.1` para `1.1.2` em backend, frontend, JSON de configuração e arquivo de versão.

**Arquivos alterados**

- `backend/flows/f110_boleto.py`
- `backend/settings.py`
- `embasa_settings.json`
- `interface/app.js`
- `interface/index.html`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Ao abrir a SP02, o sistema deve avaliar primeiro as spools mais recentes, reduzindo o risco de selecionar um boleto antigo caso existam várias linhas semelhantes na lista.

**Validação realizada**

- `python -m py_compile backend\flows\f110_boleto.py backend\flows\f110.py backend\settings.py`
- Importação local de `finalizar_boleto_f110`, `montar_nome_pdf_sugerido` e leitura da versão `1.1.2`.

## Segunda-feira, 18/05/2026 20:32:44 - Versão 1.1.1

**Problema identificado**

O fluxo F110/SP02 ainda podia travar porque aguardava confirmação manual depois que o PDFCreator era aberto. A interação externa com o PDFCreator e o popup de confirmação fazia o SAP GUI Scripting perder estabilidade no controle da tela.

**O que foi alterado**

- Reescrito o arquivo `backend/flows/f110_boleto.py`.
- Removido o popup bloqueante de confirmação do PDF.
- Mantida a abertura da SP02 na mesma sessão SAP usando `/nSP02`.
- Adicionada leitura dinâmica das linhas visíveis da SP02 por componentes `lbl[x,y]`, `txt[x,y]` e `chk[x,y]`.
- Adicionada localização automática da spool correta pelo título `BOLETO (CONTAS A RECEBER)`, dando preferência ao par `Nota acompanh.ISD &` seguido de boleto.
- Adicionada validação por F2 da spool selecionada, conferindo número, título, data, hora e a marcação de encerramento/anexação quando disponível.
- Adicionada cópia automática do nome sugerido do PDF para a área de transferência.
- Adicionado disparo automático da impressão com `Ctrl + Shift + F8` (`sendVKey(44)`).
- Mantido o retorno para F110 no BOL correto e a execução do meio de pagamento.

**Arquivos alterados**

- `backend/flows/f110_boleto.py`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

O sistema deve abrir a SP02, identificar a spool correta do boleto, copiar o nome sugerido do PDF, disparar a impressão e continuar automaticamente para F110/meio de pagamento sem aguardar confirmação manual após o PDFCreator.

**Validação realizada**

- `python -m py_compile backend\flows\f110_boleto.py backend\flows\f110.py`
- Importação local de `finalizar_boleto_f110` e `montar_nome_pdf_sugerido`.
- Busca local confirmando remoção de `MessageBox`, `ctypes` e confirmação bloqueante.

## Domingo, 17/05/2026 21:43:46 - Versão 1.1.1

**Problema identificado**

Era necessário gerar um material técnico completo e portátil contendo o resumo da solução F110/SP02 e o código atual da função `f110_boleto.py`.

**O que foi alterado**

- Criado o arquivo `RESUMO_TECNICO_F110_BOLETO.txt`.
- O arquivo contém contexto técnico, problema identificado, solução aplicada, validações e o código completo atual do `backend/flows/f110_boleto.py`.
- Não houve alteração funcional no código nesta etapa; a versão permanece `1.1.1`.

**Arquivos alterados**

- `RESUMO_TECNICO_F110_BOLETO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Permitir que o resumo técnico e o código da F110 boleto sejam enviados, lidos ou reaplicados em outro ambiente sem depender do histórico do chat.

**Validação realizada**

- Conferência de existência do arquivo técnico.
- Manutenção da versão funcional `1.1.1`.

## Domingo, 17/05/2026 21:23:40 - Versão 1.1.1

**Problema identificado**

O fluxo F110/SP02 precisava manter a versão simples que funcionava, mas ainda faltava uma proteção caso o retorno da SP02 com `F3` não saísse da tela de spool após a confirmação do PDF no PDFCreator.

**O que foi alterado**

- Adicionada verificação leve para identificar se a sessão atual ainda está na SP02 após o `F3`.
- Adicionado fallback com foco reforçado na janela SAP e tentativa de saída com `F12`.
- Mantido o fluxo principal em uma única sessão SAP usando `/nSP02`, sem voltar à estratégia pesada de múltiplas sessões.
- Atualizada a versão do projeto de `1.1` para `1.1.1` em backend, frontend, JSON de configuração e arquivo de versão.

**Arquivos alterados**

- `backend/flows/f110_boleto.py`
- `backend/settings.py`
- `embasa_settings.json`
- `interface/app.js`
- `interface/index.html`
- `VERSAO.txt`

**Resultado esperado**

O sistema deve continuar usando o caminho simples que já funcionava. Se o `F3` não sair da SP02, o fallback entra automaticamente, tenta focar a tela correta e envia `F12` antes de reabrir a F110 no BOL correto.

**Validação realizada**

- `python -m py_compile backend\flows\f110_boleto.py backend\flows\f110.py`
- Importação local das funções principais do `f110_boleto`.
