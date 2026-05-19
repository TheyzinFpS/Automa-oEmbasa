# Registro técnico de alterações

## Terça-feira, 19/05/2026 17:15:40 - Versão 1.1.7

**Problema identificado**

Os testes reais da F110 apontaram dois pontos principais: a identificação BOL podia parar/travar por volta de `BOL10/BOL11`, e a rotina da SP02 ainda sofria com foco/seleção ao tentar validar nota e boleto em sequência antes da impressão/exportação.

**O que foi alterado**

- Substituído `backend/flows/f110.py` pelo novo arquivo validado `f110_padrao_final.py`.
- Substituído `backend/flows/f110_boleto.py` pelo novo arquivo validado `f110_boleto_final.py`.
- A busca de identificação da F110 agora testa `BOL01` até `BOL100` e considera a BOL ocupada quando já existe cliente preenchido na aba Parâmetro.
- A validação da próxima data de lançamento passou a comparar somente dígitos, aceitando equivalência entre `31052026` e `31.05.2026`.
- A seleção livre passou a forçar a troca de aba e validar o preenchimento do documento formatado com `00 + doc_fat`.
- A SP02 deixou de depender do par nota/boleto e agora localiza diretamente o primeiro `BOLETO (CONTAS A RECEBER)` em ordem decrescente.
- A validação da spool normaliza números com zeros à esquerda, evitando divergência entre lista e detalhe.
- A checkbox `Encerrado, já não é possível anexar` passou a ser apenas informativa no fluxo.
- O fluxo da SP02 agora valida o boleto, volta para a lista, marca a checkbox da linha correta e aciona impressão/exportação pelo menu `wnd[0]/mbar/menu[0]/menu[0]/menu[0]`.
- Mantido o aviso visual interno da interface via `PDF_NAME_READY::`, exibido após o comando de impressão/exportação, sem popup externo bloqueante.
- Atualizada a versão do projeto de `1.1.6` para `1.1.7` em backend, frontend, JSON de configuração e arquivo de versão.

**Arquivos alterados**

- `backend/flows/f110.py`
- `backend/flows/f110_boleto.py`
- `interface/app.js`
- `interface/index.html`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

A F110 deve conseguir avançar com identificações acima de `BOL10/BOL11`, preencher e validar parâmetros/seleção livre com mais segurança, localizar o boleto correto na SP02, marcar a checkbox adequada, tentar abrir o PDFCreator pelo menu de impressão/exportação e seguir automaticamente para F110/meio de pagamento.

**Problema atual conhecido**

Se o menu `wnd[0]/mbar/menu[0]/menu[0]/menu[0]` também não abrir o PDFCreator no ambiente SAP, a alternativa segura indicada no resumo técnico é manter a checkbox correta já marcada e transformar somente o clique de impressão/exportação em uma ação manual, preservando o restante do fluxo automático.

**Validação realizada**

- `python -m py_compile C:\Users\Taylor\Desktop\f110_padrao_final.py C:\Users\Taylor\Desktop\f110_boleto_final.py`
- `python -m py_compile backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`

## Terça-feira, 19/05/2026 07:29:09 - Versão 1.1.6

**Problema identificado**

Após remover o popup bloqueante do PDFCreator, o usuário ainda precisava de um aviso claro na interface informando que o nome padrão do PDF já estava copiado e disponível para colar no PDFCreator.

**O que foi alterado**

- Adicionado evento interno `PDF_NAME_READY::` no fluxo `F110/SP02` logo após copiar o nome sugerido do PDF.
- O log público agora envia o nome sugerido completo, mas a interface exibe a mensagem resumida para não poluir os logs operacionais.
- Criado modal interno na interface com fundo desfocado, título, instrução e o nome padrão do PDF.
- Adicionado botão `Copiar nome e fechar`, que copia novamente o nome sugerido e fecha o aviso.
- O modal não usa `MessageBoxW` nem janela Tkinter, evitando o travamento que acontecia com popups externos durante o controle SAP/PDFCreator.
- Atualizada a versão do projeto de `1.1.5` para `1.1.6` em backend, frontend, JSON de configuração e arquivo de versão.

**Arquivos alterados**

- `backend/flows/f110_boleto.py`
- `interface/app.js`
- `interface/index.html`
- `interface/style.css`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Quando o sistema entrar na spool do boleto e disparar a impressão, a interface exibirá um aviso visual com o nome do PDF. O usuário poderá clicar em `Copiar nome e fechar`, colar no PDFCreator e seguir sem bloquear o fluxo SAP com popup externo.

**Validação realizada**

- `python -m py_compile backend\flows\f110_boleto.py backend\flows\f110.py backend\settings.py`
- Validação estática dos IDs `pdfNameModal`, `pdfNameValue`, `copyPdfNameAndClose` e do evento `PDF_NAME_READY::` no frontend.

## Segunda-feira, 18/05/2026 21:35:54 - Versão 1.1.5

**Problema identificado**

O acesso aos detalhes da spool por `F2` podia depender do ponto de foco da linha na SP02. O foco no título da linha pode não ser suficiente em todos os ambientes SAP.

**O que foi alterado**

- Adicionado fallback de foco por checkbox da mesma linha quando o foco pelo título não abrir/validar os detalhes corretamente.
- O fallback usa o checkbox apenas como ponto de foco/seleção da linha, sem marcar ou desmarcar manualmente.
- A validação tenta primeiro o título da linha e, em caso de falha, volta para a lista e tenta o checkbox.
- Mantida a regra de imprimir diretamente da tela de detalhes do boleto após validação.
- Atualizada a versão do projeto de `1.1.4` para `1.1.5` em backend, frontend, JSON de configuração e arquivo de versão.

**Arquivos alterados**

- `backend/flows/f110_boleto.py`
- `backend/settings.py`
- `embasa_settings.json`
- `interface/app.js`
- `interface/index.html`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

O sistema deve conseguir entrar com F2 nos detalhes da nota e do boleto mesmo se o SAP não aceitar o foco no título da linha, usando o checkbox como fallback de foco sem alterar sua marcação.

**Validação realizada**

- `python -m py_compile backend\flows\f110_boleto.py backend\flows\f110.py backend\settings.py`
- Importação local de `finalizar_boleto_f110`, `montar_nome_pdf_sugerido` e leitura da versão `1.1.5`.

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
