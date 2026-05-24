# Registro técnico de alterações

## Domingo, 24/05/2026 19:14:50 - Versão 1.4.3

**Problema identificado**

Quando uma etapa falhava, o log operacional da interface mostrava apenas mensagens genéricas como `Falha na etapa XD03` ou `Erro ao executar o fluxo`, sem explicar o ponto exato, o bloqueio técnico, os dados já capturados ou o que precisava ser conferido no SAP.

**O que foi alterado**

- Criado diagnóstico detalhado para falhas por etapa (`CONEXAO`, `XD03`, `VA01`, `VF01`, `FB03`, `VF02` e `F110`).
- O log público agora informa o que o sistema estava tentando fazer, a mensagem para o usuário, o bloqueio técnico retornado, os dados já conhecidos, o que faltou ou deve ser conferido e a retomada sugerida.
- Quando a sessão SAP está disponível, o diagnóstico tenta incluir a transação SAP detectada no momento da falha.
- O resumo final de erro na interface passou a apontar para o diagnóstico detalhado registrado acima.
- Corrigido o envio em tempo real do logger para a interface para usar a mensagem já mascarada pelo logger, evitando exibição de CPF/CNPJ bruto no balão de logs.
- Ajustado o CSS do log operacional para preservar quebras de linha e quebrar textos longos sem estourar o modal.
- Atualizada a versão do projeto de `1.4.2` para `1.4.3`.

**Arquivos alterados**

- `backend/controller.py`
- `backend/settings.py`
- `interface.py`
- `interface/app.js`
- `interface/index.html`
- `interface/style.css`
- `embasa_settings.json`
- `VERSAO.txt`
- `LEIA-ME_EMPRESA.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Ao ocorrer erro em qualquer etapa do fluxo SAP, o usuário deve conseguir abrir `Logs` e entender onde falhou, o que estava sendo feito, qual bloqueio técnico foi retornado, quais dados já tinham sido capturados e qual ponto de retomada usar.

**Validação realizada**

- `python -m py_compile backend\controller.py interface.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado do diagnóstico de falha em `XD03`, confirmando mensagem pública detalhada e CPF/CNPJ mascarado.
- Validação local do modal de logs pelo navegador interno.

## Domingo, 24/05/2026 18:56:17 - Versão 1.4.2

**Problema identificado**

O fluxo `Água + Esgoto` precisava respeitar a ordem operacional real do SAP: primeiro criar os dois pedidos até `VF02`, guardando separadamente `doc_fat_agua` e `doc_fat_esgoto`, e somente depois executar as duas F110. A versão anterior iniciava a F110 logo após a criação da Água, o que não correspondia ao processo correto.

Também era necessário manter o registro de versão após os ajustes de interface e fluxo feitos em 24/05/2026.

**O que foi alterado**

- Reordenado o fluxo composto para criar Água até `VF02`, guardar o `doc_fat` da Água, voltar para `VA01`, criar Esgoto até `VF02` e guardar o `doc_fat` do Esgoto.
- A F110 passa a ser executada apenas depois da criação dos dois `doc_fat`, usando primeiro o documento da Água e depois o documento do Esgoto.
- O fluxo composto não abre SP02 ao final de cada F110; a SP02 é aberta somente após completar os dois meios de pagamento.
- A seleção final na SP02 passa a tratar a primeira linha `BOLETO` como Esgoto e a próxima linha `BOLETO` como Água, seguindo a ordem decrescente da tela.
- Após o modal de cópia do boleto de Esgoto, o sistema aguarda 7 segundos, desmarca a linha e segue para o boleto de Água.
- Removido o seletor `Sistema informado` do card de status da base e mantida apenas a mensagem centralizada de status.
- Removidos da guia `Sobre` os caminhos técnicos de executável, runtime, histórico, configuração e log.
- Adicionada proteção para não versionar o arquivo local `.nube`.
- Atualizada a versão do projeto de `1.4.1` para `1.4.2`.

**Arquivos alterados**

- `.gitignore`
- `LEIA-ME_EMPRESA.txt`
- `backend/controller.py`
- `backend/flows/f110.py`
- `backend/flows/f110_boleto.py`
- `backend/settings.py`
- `interface.py`
- `interface/index.html`
- `interface/app.js`
- `interface/style.css`
- `embasa_settings.json`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Ao selecionar `Água + Esgoto`, o sistema deve gerar os dois pedidos e os dois documentos de faturamento antes de entrar na F110. Depois deve executar a F110 da Água, executar a F110 do Esgoto e abrir a SP02 apenas no final, copiando primeiro o nome do boleto de Esgoto e depois o de Água.

**Validação realizada**

- `python -m py_compile backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py interface.py`
- `node --check interface\app.js`
- Validação visual local da interface para o card de status e a guia `Sobre`.
- Rebuild com `powershell -ExecutionPolicy Bypass -File .\build_empresarial.ps1`.

## Sexta-feira, 22/05/2026 00:34:45 - Versão 1.4.1

**Problema identificado**

No fluxo `Água + Esgoto`, a SP02 precisava orientar o usuário em duas etapas separadas: primeiro a spool mais recente de Esgoto e depois a próxima spool de Água. Além disso, o backend já possuía o mecanismo de aviso operacional, mas o controller e a F110 ainda não repassavam esse callback até a etapa de meio de pagamento/SP02, fazendo o fluxo não aguardar corretamente o clique `Copiar nome e fechar`.

**O que foi alterado**

- Propagado `notice_callback` do `interface.py` para `SAPController.executar_fluxo`, para o fluxo composto `Água + Esgoto`, para `f110()` e para `finalizar_boleto_f110()`.
- A seleção final da SP02 agora usa o clique do modal como confirmação real antes de prosseguir para o próximo boleto.
- Mantida a ordem operacional do fluxo composto: primeiro a primeira linha visual de `BOLETO (CONTAS A RECEBER)` como `Projeto Esgoto`; depois, a busca continua a partir dessa linha até a próxima ocorrência, tratada como `Projeto Água`.
- Após cada clique em `Copiar nome e fechar`, o backend aguarda 7 segundos antes de prosseguir para a próxima etapa.
- O nome do arquivo de meio de pagamento também passa pelo mesmo aviso operacional, permitindo que a interface volte ao primeiro plano e aguarde o usuário copiar o padrão.
- Protegidos os modais operacionais contra fechamento acidental pelo `Esc` enquanto houver aviso pendente.
- Atualizada a versão do projeto de `1.4.0` para `1.4.1`.

**Arquivos alterados**

- `backend/controller.py`
- `backend/flows/f110.py`
- `backend/flows/f110_boleto.py`
- `backend/settings.py`
- `interface/index.html`
- `interface/app.js`
- `embasa_settings.json`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Ao selecionar `Água + Esgoto`, o sistema deve gerar as duas F110, abrir a SP02 no final, selecionar primeiro o boleto de Esgoto, trazer a interface para frente com o nome terminando em `Projeto Esgoto`, aguardar o clique do usuário, esperar 7 segundos, localizar o próximo boleto, repetir o aviso com nome terminando em `Projeto Água`, aguardar mais 7 segundos e retornar da SP02.

**Validação realizada**

- `python -m py_compile backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py backend\flows\xd03.py backend\history.py interface.py backend\settings.py`
- `node --check interface\app.js`

## Sexta-feira, 22/05/2026 00:13:29 - Versão 1.4.0

**Problema identificado**

Era necessário adicionar um tipo composto `Água + Esgoto`, sem duplicar preenchimento de cliente, e controlar duas F110 no mesmo fluxo mantendo os dois `doc_fat`. Também faltava orientar o usuário no momento de salvar o arquivo de meio de pagamento com um nome padronizado.

**O que foi alterado**

- Adicionado o tipo `Água + Esgoto` na seleção de pedido da interface.
- Adicionado suporte XD03 para validar, no mesmo cliente, os setores `AG` e `EG` quando o tipo composto for selecionado.
- Criada rota especial no controller para o fluxo composto:
  - valida cliente uma vez;
  - cria Água até o re-salvamento da VF02 e guarda o `doc_fat`;
  - cria Esgoto até o re-salvamento da VF02 e guarda o `doc_fat`;
  - executa F110 da Água sem abrir SP02;
  - executa F110 do Esgoto sem abrir SP02;
  - abre SP02 apenas no final e seleciona as duas linhas mais recentes de `BOLETO (CONTAS A RECEBER)`.
- Ajustada a F110 para aceitar execução sem seleção imediata da spool, permitindo o fluxo composto.
- Criada função `selecionar_boletos_sp02` para seleção final de múltiplas spools de boleto.
- Criado padrão de nome do arquivo de meio de pagamento: `ano.mês.dia - doc.fat`, exemplo `2026.05.22 - 10031261`.
- Adicionado evento `PAYMENT_FILE_READY::` para abrir modal na interface com botão `Copiar nome e fechar` ao chegar no salvamento do meio de pagamento.
- A interface tenta voltar ao primeiro plano quando recebe eventos de nome de PDF ou arquivo de meio de pagamento.
- Atualizado o histórico para reconhecer o tipo `Projeto Água + Esgoto`.
- Atualizada a versão do projeto de `1.3.0` para `1.4.0`.

**Arquivos alterados**

- `backend/controller.py`
- `backend/flows/f110.py`
- `backend/flows/f110_boleto.py`
- `backend/flows/xd03.py`
- `backend/history.py`
- `backend/settings.py`
- `interface.py`
- `interface/index.html`
- `interface/app.js`
- `interface/style.css`
- `embasa_settings.json`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Ao selecionar `Água + Esgoto`, o sistema deve gerar os dois pedidos/faturamentos em sequência, executar duas F110 com BOLs diferentes, abrir o meio de pagamento para cada `doc_fat` com nome padronizado para copiar e, no final, deixar as duas linhas de boleto selecionadas na SP02 para impressão manual.

**Validação realizada**

- `python -m py_compile backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py backend\flows\xd03.py backend\history.py interface.py backend\settings.py`
- `node --check interface\app.js`
- Teste local de importação do controller e geração dos nomes padrão de PDF/meio de pagamento.

## Terça-feira, 19/05/2026 20:13:21 - Versão 1.3.0

**Problema identificado**

O sistema precisava de uma base confiável para retomada e auditoria: quando uma etapa parava, o checkpoint não carregava todo o contexto útil, e os pedidos concluídos não ficavam registrados em uma consulta central para o setor.

**O que foi alterado**

- Criado o módulo `backend/history.py` para registrar cada pedido concluído em duas camadas: banco JSON pesquisável em `dados_compartilhados/historico/historico_pedidos.json` e arquivo TXT legível por data, usuário Windows e nome do cliente.
- Adicionado texto padrão VA01 no histórico, com cliente, documento, tipo de pessoa, número do cliente, número do pedido, doc.fat, boleto/BOL, valor e endereço do empreendimento.
- Integrada a gravação automática do histórico ao sucesso de `gerar_boleto`.
- Criadas APIs pywebview `listar_historico` e `obter_historico` para consulta pela interface.
- Adicionado botão `Histórico` no painel de monitoramento.
- Criado modal de histórico com busca por data, pedido, cliente, CPF/CNPJ ou empreendimento e detalhe completo do registro selecionado.
- Corrigida a sincronização visual da retomada, removendo um retorno prematuro que marcava apenas a primeira etapa anterior.
- Enriquecido o checkpoint com pedido, tipo, endereço, data de criação e orientação de retomada.
- Adicionada captura tentativa do número do pedido a partir do retorno SAP da VA01 quando disponível.
- Atualizada a versão do projeto de `1.2.1` para `1.3.0` em backend, frontend, JSON de configuração, HTML e arquivo de versão.

**Arquivos alterados**

- `backend/history.py`
- `backend/controller.py`
- `backend/settings.py`
- `interface.py`
- `interface/index.html`
- `interface/app.js`
- `interface/style.css`
- `embasa_settings.json`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Cada boleto concluído passa a gerar registro compartilhado para consulta futura. O usuário consegue abrir `Histórico`, pesquisar por pedido/data/cliente e visualizar os dados essenciais sem abrir arquivos manualmente. Em paralelo, a pasta da rede mantém TXT organizado para auditoria ou conferência fora da interface.

**Validação realizada**

- `python -m py_compile backend\history.py backend\controller.py interface.py backend\settings.py`
- `node --check interface\app.js`
- Teste local do gerador de texto padrão e leitura da lista de histórico.

## Terça-feira, 19/05/2026 18:01:59 - Versão 1.2.1

**Problema identificado**

O modal final de impressão manual tinha dois botões de fechamento: `Copiar nome e fechar` e `Fechar`. Como a ação esperada é copiar o nome padrão e encerrar o aviso, o botão `Fechar` era redundante e podia confundir o usuário.

**O que foi alterado**

- Removido o botão `Fechar` do modal de impressão manual.
- Mantido apenas o botão `Copiar nome e fechar`.
- Atualizada a versão do projeto de `1.2.0` para `1.2.1` em backend, frontend, JSON de configuração e arquivo de versão.

**Arquivos alterados**

- `interface/index.html`
- `interface/app.js`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

O usuário terá uma única ação clara no modal final: copiar o nome padrão do PDF e fechar o aviso.

**Validação realizada**

- `node --check interface\app.js`

## Terça-feira, 19/05/2026 17:56:11 - Versão 1.2.0

**Problema identificado**

Quando a linha do boleto já estava selecionada e o modal de impressão manual era exibido, a etapa F110 ainda podia permanecer visualmente como processamento, mesmo que a automação controlada pelo sistema já tivesse terminado.

**O que foi alterado**

- O evento `PDF_NAME_READY::` agora é enviado com status `concluido`.
- A barra de progresso da etapa F110 passa para 100% quando o modal de impressão manual aparece.
- O sistema considera concluída a parte automatizada assim que a SP02 fica com a linha correta do boleto selecionada e o nome padrão fica disponível para copiar.
- Atualizada a versão do projeto de `1.1.9` para `1.2.0` em backend, frontend, JSON de configuração e arquivo de versão.

**Arquivos alterados**

- `backend/flows/f110_boleto.py`
- `interface/app.js`
- `interface/index.html`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Ao aparecer o modal final de impressão manual, a etapa F110 ficará marcada como concluída no andamento em tempo real, deixando claro que o restante é apenas a ação manual do usuário no SAP/PDFCreator.

**Validação realizada**

- `python -m py_compile backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`

## Terça-feira, 19/05/2026 17:38:05 - Versão 1.1.9

**Problema identificado**

O texto do aviso final da SP02 separava `Shift + F5` e `Ctrl + Shift + F8` por vírgula, mas ambos representam comandos/opções de impressão. A orientação precisava deixar essa equivalência mais clara para o usuário.

**O que foi alterado**

- Ajustado o texto do modal de impressão manual para exibir `Shift + F5 / Ctrl + Shift + F8`.
- Mantida a opção de selecionar o ícone de impressão no SAP.
- Atualizada a versão do projeto de `1.1.8` para `1.1.9` em backend, frontend, JSON de configuração e arquivo de versão.

**Arquivos alterados**

- `interface/index.html`
- `interface/app.js`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

O usuário verá os dois atalhos de impressão como alternativas equivalentes, separados por barra, reduzindo ambiguidade na etapa manual final.

**Validação realizada**

- `node --check interface\app.js`

## Terça-feira, 19/05/2026 17:33:16 - Versão 1.1.8

**Problema identificado**

Os testes reais confirmaram que comandos SAP acionados pelo Python não executam de forma confiável ações que forçam a abertura de outro programa, como o PDFCreator. A impressão/exportação automática da spool, mesmo com linha correta selecionada, permanecia instável.

**O que foi alterado**

- Invertida a ordem final do fluxo F110: o meio de pagamento agora é executado antes da etapa SP02.
- Após concluir o meio de pagamento, o sistema abre a SP02, localiza o primeiro `BOLETO (CONTAS A RECEBER)` em ordem decrescente, valida a spool e marca a checkbox da linha correta.
- Removida a tentativa automática de abrir o PDFCreator pelo menu de impressão/exportação.
- O sistema agora mantém o SAP na SP02 com a linha do boleto selecionada para o usuário executar manualmente `Shift + F5`, `Ctrl + Shift + F8` ou clicar no ícone de impressão.
- O aviso interno da interface foi ajustado para informar que a linha do boleto foi selecionada e exibir o nome padrão do PDF com botão `Copiar nome e fechar`.
- O backend passa a retornar `pdf_boleto` e `spool_boleto` como `LINHA_SELECIONADA`, além de `impressao_manual=True`.
- Atualizada a versão do projeto de `1.1.7` para `1.1.8` em backend, frontend, JSON de configuração e arquivo de versão.

**Arquivos alterados**

- `backend/flows/f110_boleto.py`
- `interface/app.js`
- `interface/index.html`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

O fluxo deve concluir automaticamente a F110 e o meio de pagamento, depois deixar a SP02 pronta com a spool correta do boleto selecionada. A partir daí, o usuário executa apenas a impressão manual no SAP/PDFCreator e copia o nome padrão pelo aviso da interface.

**Validação realizada**

- `python -m py_compile backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`

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
