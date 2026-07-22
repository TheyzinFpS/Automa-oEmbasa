# Registro técnico de alterações

## Quarta-feira, 22/07/2026 - Versao 1.4.46

**Ajuste aplicado**

- A rotina de extratos deixou de depender primeiro do acesso direto pela URL `extrato-individualizado`.
- Quando o usuario ja esta logado e a Caixa fica no dashboard, o sistema agora navega pelo menu real: `Saldo e Extratos` -> `Extrato Individualizado de Contas`.
- A URL direta continua existindo apenas como fallback, caso o clique pelo menu nao encontre o item.
- A espera pela tela do extrato foi separada em uma funcao propria, permitindo retentativas sem deixar a automacao parada silenciosamente na tela inicial.

**Validacao realizada**

- `python -m py_compile main.py interface.py backend\settings.py backend\flows\extratos_caixa_chrome.py`
- `node --check interface\app.js`
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.46`.

## Quarta-feira, 22/07/2026 - Versao 1.4.45

**Ajuste aplicado**

- O perfil controlavel do Opera/Chrome/Edge agora grava a geolocalizacao como bloqueada antes de abrir a Caixa.
- A abertura do navegador passou a usar `--deny-permission-prompts` e `--disable-geolocation`, evitando o popup `Saber sua localizacao`.
- A rotina CDP tambem aplica `Browser.setPermission` com geolocalizacao negada para `https://gerenciador.caixa.gov.br`.
- A navegacao ate `Extrato Individualizado` passou a usar `Page.navigate` e retentativas contra a falha `Runtime.evaluate: Inspected target navigated or closed`.

**Validacao realizada**

- `python -m py_compile main.py interface.py backend\settings.py backend\flows\extratos_caixa_chrome.py`
- `node --check interface\app.js`
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.45`.

## Quarta-feira, 22/07/2026 - Versao 1.4.44

**Ajuste aplicado**

- Corrigida a falha `Handshake status 403 Forbidden` ao controlar Opera/Chrome/Edge pela porta `9222`.
- O navegador controlavel agora e aberto com `--remote-allow-origins=http://127.0.0.1:9222`, permitindo a conexao WebSocket usada pela rotina de extratos.
- O diagnostico do navegador passou a testar a conexao WebSocket antes de considerar a janela pronta.
- Quando uma janela antiga estiver aberta sem permissao de controle, a interface passa a mostrar uma mensagem amigavel pedindo para fechar a janela controlavel e abrir novamente pelo botao do app.

**Validacao realizada**

- `python -m py_compile main.py interface.py backend\settings.py backend\flows\extratos_caixa_chrome.py`
- `node --check interface\app.js`
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.44`.

## Quarta-feira, 22/07/2026 - Versao 1.4.43

**Ajuste aplicado**

- A rotina `Baixar extratos` passou a usar a Area de Trabalho do usuario atual como destino padrao durante os testes locais.
- Quando nenhum destino e informado pela interface, o backend cria os PDFs em `Desktop\EXTRATOS_CAIXA\ANO\MES.SIGLA\CEF`.
- A interface continua sem exibir campo tecnico de pasta, mantendo a tela enxuta para operacao real.

**Validacao realizada**

- `python -m py_compile main.py interface.py backend\settings.py backend\flows\extratos_caixa_chrome.py`
- `node --check interface\app.js`
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.43`.

## Quarta-feira, 22/07/2026 - Versao 1.4.42

**Ajuste aplicado**

- A tela `Baixar extratos` foi simplificada para uso real, removendo os campos tecnicos `Conta no arquivo` e `Pasta base de destino`.
- Os botoes auxiliares `Testar conexao`, `Preparar roteiro` e `Limpar` foram retirados da area principal, mantendo apenas `Abrir navegador` e `Baixar extratos`.
- A pre-visualizacao passou a mostrar somente o periodo selecionado, deixando conta, arquivo e pasta para o resultado real da automacao.
- Adicionado o quadro `Resultados da baixa`, exibindo cada conta processada com status `OK` ou `ERRO`.
- O quadro de resultados passa a ser atualizado em tempo real a cada conta concluida, sem depender da abertura dos logs.
- Adicionado modal final minimalista com resumo das contas baixadas e eventuais falhas.
- O backend da rotina Caixa agora lista as contas do GovConta e executa a baixa em sequencia, devolvendo `itens` com conta, arquivo salvo ou erro.

**Validacao realizada**

- `python -m py_compile main.py interface.py backend\settings.py backend\flows\extratos_caixa_chrome.py`
- `node --check interface\app.js`
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.42`.

## Quarta-feira, 22/07/2026 - Ajuste visual da Versao 1.4.41

**Ajuste aplicado**

- A tela `Baixar extratos` foi enxugada, removendo o roteiro visual extenso e a exibicao completa da pasta destino.
- A pre-visualizacao passou a mostrar apenas `Periodo` e `Arquivo`, mantendo a pasta completa somente no payload/log operacional.
- Rebuild empresarial concluido e o atalho da area de trabalho continua apontando para `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`.

**Validacao realizada**

- `node --check interface\app.js`
- `python -m py_compile main.py interface.py backend\settings.py backend\flows\extratos_caixa_chrome.py`
- `git diff --check`
- Rebuild empresarial concluido.

## Quarta-feira, 22/07/2026 - Versao 1.4.41

**Ajuste aplicado**

- Removido o atalho externo `Abrir_Chrome_Caixa_Controlavel.cmd`; a abertura do navegador controlavel agora fica dentro da propria interface.
- A area `Baixar extratos` ganhou a selecao de navegador, com `Opera` como padrao e suporte adicional a `Chrome` e `Microsoft Edge`.
- Adicionado o botao `Abrir navegador`, que localiza o navegador escolhido, abre uma janela controlavel na porta `9222` com perfil local do EMBASA e direciona para a Caixa.
- Os textos da interface e do backend foram ajustados de `Chrome` para `navegador controlavel`, permitindo testes locais no Opera sem alterar o fluxo de download.
- Atualizada a versao do projeto de `1.4.40` para `1.4.41`.

**Validacao realizada**

- `python -m py_compile main.py interface.py backend\settings.py backend\flows\extratos_caixa_chrome.py`
- `node --check interface\app.js`
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.41`.

## Quarta-feira, 22/07/2026 - Versao 1.4.40

**Ajuste aplicado**

- Criada a primeira ponte de automacao Caixa GovConta por Chrome ja logado/controlavel via Chrome DevTools Protocol na porta `9222`.
- Adicionado o arquivo `Abrir_Chrome_Caixa_Controlavel.cmd`, que abre um Chrome separado com perfil local do EMBASA para login manual seguro na Caixa.
- A area `Baixar extratos` passou a ter o botao `Testar Chrome` para diagnosticar a conexao com o Chrome controlavel.
- A area `Baixar extratos` passou a ter o botao `Baixar conta atual no Chrome`, que abre a tela `Extrato Individualizado`, seleciona conta/mes/ano, pesquisa, exporta PDF e renomeia o arquivo baixado.
- O periodo padrao dos extratos agora usa o mes anterior ao mes atual, adequado para fechamento mensal.
- Adicionada a dependencia `websocket-client` para comunicacao direta com o Chrome sem armazenar login ou senha.
- Atualizada a versao do projeto de `1.4.39` para `1.4.40`.

**Validacao realizada**

- `python -m py_compile main.py interface.py backend\settings.py backend\flows\extratos_caixa_chrome.py`
- `node --check interface\app.js`
- `git diff --check`
- `build_empresarial.ps1` instalou `websocket-client==1.9.0` e gerou `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`.
- Diagnostico local da ponte Chrome confirmou a mensagem esperada quando nao ha Chrome controlavel aberto na porta `9222`.

## Sabado, 13/06/2026 - Versao 1.4.39

**Ajuste aplicado**

- A area `Baixar extratos` foi atualizada com o roteiro visual do site da Caixa enviado nos prints: `Saldo e Extratos`, `Extrato Individualizado de Contas`, selecao da conta, mes/ano, pesquisa, exportacao em PDF e salvamento em `CEF`.
- A interface agora calcula a pasta destino no padrao usado pelo setor, como `...\EXTRATOS\2026\05.MAI\CEF`.
- Adicionado campo `Conta no arquivo` para montar o nome sugerido no padrao `CEF 8512-3_MAI-26.pdf`.
- O botao `Preparar baixa de extratos` passou a registrar no log os passos mapeados, a pasta destino e o nome sugerido.
- Atualizada a versao do projeto de `1.4.38` para `1.4.39`, incluindo `VERSAO.txt`, `embasa_settings.json`, `backend/settings.py`, rodape da interface e constante JS.

**Validacao realizada**

- `node --check interface\app.js`
- `python -m py_compile main.py interface.py backend\settings.py`
- `git diff --check`
- Checagem pelo Browser interno em `http://127.0.0.1:8790/index.html`: painel `Baixar extratos` abriu pela sidebar, a conta `8512-3` gerou o preview `CEF 8512-3_JUN-26.pdf`, a pasta destino ficou no padrao `...\EXTRATOS\2026\06.JUN\CEF` e o botao de preparacao registrou pasta/nome/roteiro no log operacional.
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.39`.

## Quinta-feira, 11/06/2026 - Versao 1.4.38

**Ajuste aplicado**

- Adicionada a nova area `Baixar extratos` na sidebar, com icone `BE`.
- Criada a base visual da rotina de extratos bancarios para a Caixa, com campos de banco, mes e ano.
- O painel de andamento ganhou o modo `BE - Baixar extratos`, usado para validar a base antes da automacao real do site.
- O botao `Preparar baixa de extratos` valida o periodo, atualiza o monitor e registra log operacional, deixando o fluxo pronto para receber os prints do passo a passo.
- Atualizada a versao do projeto de `1.4.37` para `1.4.38`.

**Validacao realizada**

- `python -m py_compile main.py interface.py backend\settings.py`
- `node --check interface\app.js`
- `git diff --check`
- Checagem pelo Browser interno em `http://127.0.0.1:8790/index.html`: painel `Baixar extratos` abriu pela sidebar e o botao `Preparar baixa de extratos` atualizou o monitor para `BE - Baixar extratos`.
- A captura de screenshot pelo Browser interno travou em `Page.captureScreenshot`, mas a validacao DOM confirmou painel visivel, preview `Junho/2026`, status `Base pronta` e log operacional gerado.

## Quinta-feira, 11/06/2026 - Versao 1.4.37

**Ajuste aplicado**

- No fluxo `Agua + Esgoto`, o primeiro aviso de PDF da SP02 passou a exigir confirmacao do usuario antes de desmarcar o boleto atual e seguir para o proximo.
- O modal especial do PDF usa o botao `Prosseguir para Agua` e exibe aviso amarelo orientando a clicar somente depois de gerar o boleto no PDFCreator.
- O aviso padrao de PDF continua apenas informativo nos demais fluxos, preservando o comportamento sem bloqueio.
- Corrigida a criacao de cliente CPF na aba `Dados de controle`: o sistema preenche o campo fiscal de CPF e marca a opcao `Pessoa fisica` antes de seguir para dados de empresa e vendas.
- Atualizada a versao do projeto de `1.4.36` para `1.4.37`.

**Validacao realizada**

- `python -m py_compile main.py interface.py backend\settings.py backend\controller.py backend\flows\f110_boleto.py backend\flows\cliente_cadastro.py`
- `node --check interface\app.js`
- `git diff --check`
- Tentativa de checagem visual pelo Browser interno: `http://127.0.0.1:8765/` foi bloqueado por `net::ERR_BLOCKED_BY_CLIENT` e `file:///` foi bloqueado pela politica do Browser.
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.37`.

## Terca-feira, 09/06/2026 - Versao 1.4.36

**Ajuste aplicado**

- As filas de empreendimentos e de CPF/CNPJ agora removem visualmente cada item concluido durante o processamento, mantendo na tela apenas o que ainda esta pendente.
- Corrigido o empilhamento dos modais operacionais quando o aviso do PDF e a confirmacao de proximo item aparecem juntos: PDF fica acima, confirmacao fica abaixo, os cards permanecem nitidos e apenas a tela principal fica desfocada.
- Ao fechar o aviso do PDF enquanto a confirmacao do proximo item esta aberta, o modal de confirmacao sobe para o centro com animacao fluida.
- Reforcada a selecao do campo de tratamento na criacao de cliente CPF no SAP: o sistema tenta selecionar por chave, texto visivel e lista interna do combobox, evitando travamento em `Sr`/`Sra`.
- Otimizada a preparacao do runtime local quando o sistema e aberto pela rede, usando `robocopy` multithread antes do fallback Python.
- A publicacao na rede passou a gerar `Abrir_EMBASA_Rapido.cmd`, um launcher que abre a copia local da mesma versao quando ela ja existe, reduzindo o tempo de abertura para os usuarios apos a primeira execucao da versao.
- Atualizada a versao do projeto de `1.4.35` para `1.4.36`.

**Validacao realizada**

- `node --check interface\app.js`
- `python -m py_compile main.py interface.py backend\settings.py backend\flows\cliente_cadastro.py`
- Checagem de IDs duplicados no HTML.
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- Checagem local da interface confirmando versao `1.4.36`, ausencia de erros no console e carregamento das regras de empilhamento/animacao dos modais PDF + confirmacao.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.36`.
- Publicacao de teste em pasta temporaria local confirmando criacao do `Abrir_EMBASA_Rapido.cmd`.
- Smoke test do executavel empacotado: processo iniciou e permaneceu em execucao ate o encerramento do teste.

## Terca-feira, 09/06/2026 - Versao 1.4.35

**Ajuste aplicado**

- Adicionada a selecao `Data de Validade` no fluxo de Multa Contratual, com opcoes de 30 e 60 dias uteis.
- A Multa Contratual passou a enviar `validade_dias_uteis` no payload e a VA01 aplica `C030` para 30 dias uteis ou `C060` para 60 dias uteis.
- O backend passou a validar a validade da Multa Contratual antes de iniciar o fluxo SAP.
- Corrigida a retomada da fila de CPF/CNPJ apos criacao de cliente: quando um cliente inexistente e criado no meio da fila, o fluxo retoma a partir do CPF/CNPJ e empreendimento pendentes, sem reiniciar pelos itens anteriores.
- Atualizada a versao do projeto de `1.4.34` para `1.4.35`.

**Validacao realizada**

- `node --check interface\app.js`
- `python -m py_compile interface.py backend\settings.py backend\validators.py backend\flows\va01.py`
- Teste direto do validador confirmando boleto comum sem exigencia de validade, multa aceita em 30/60 dias uteis e bloqueio de valor invalido.
- Teste direto da regra da VA01 confirmando `C030` para 30 dias uteis e `C060` para 60 dias uteis.
- Checagem de IDs duplicados no HTML.
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- Checagem visual local do seletor de validade da Multa Contratual.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.35`.
- Smoke test do executavel empacotado: processo iniciou e permaneceu em execucao ate o encerramento do teste.

## Segunda-feira, 08/06/2026 - Versao 1.4.34

**Ajuste aplicado**

- Restaurado o layout anterior das filas dentro da seção `Dados do empreendimento`.
- Removido o dock compacto que havia sido colocado no bloco superior `Automacao SAP Desktop`.
- As caixas `Fila de empreendimentos` e `Fila de CPF/CNPJ` voltaram a exibir os textos, botões e listas no mesmo formato da versão `1.4.32`.
- Mantidas as funcoes de fila de CPF/CNPJ, rascunhos, edicao, exclusao e processamento sequencial.
- Atualizada a versao do projeto de `1.4.33` para `1.4.34`.

**Validacao realizada**

- `node --check interface\app.js`
- `python -m py_compile interface.py backend\settings.py backend\drafts.py`
- Checagem de IDs duplicados no HTML.
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- `git diff --check`
- Renderizacao local em viewport estreita, confirmando ausencia do dock no topo, duas caixas novamente dentro de `Dados do empreendimento`, textos vazios restaurados e versao `1.4.34`.
- Console do navegador sem erros ou avisos durante a validacao visual.
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.34` no codigo e no `embasa_settings.json` distribuido.
- Smoke test do executavel empacotado: processo iniciou em modo frozen, carregou `interface\index.html`, respeitou `require_sap_session=false` e permaneceu em execucao ate o encerramento do teste.

## Domingo, 07/06/2026 - Versao 1.4.33

**Ajuste aplicado**

- Reposicionados os controles de `Fila de empreendimentos` e `Fila de CPF/CNPJ` para o bloco superior `Automacao SAP Desktop`.
- Removidas as caixas grandes que ficavam dentro dos dados do empreendimento, reduzindo a altura ocupada no formulario principal.
- Criado dock minimalista com botoes compactos para adicionar empreendimento, adicionar cliente, salvar rascunho e limpar filas.
- As mensagens vazias das filas no dock ficam ocultas para preservar espaco; quando houver itens, a lista aparece de forma compacta e com rolagem limitada.
- Mantidas as mesmas funcoes e IDs dos botoes, preservando a logica de fila, rascunho, edicao e remocao.
- Atualizada a versao do projeto de `1.4.32` para `1.4.33`.

**Validacao realizada**

- `node --check interface\app.js`
- `python -m py_compile interface.py backend\settings.py backend\drafts.py`
- Checagem de IDs duplicados no HTML.
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- `git diff --check`
- Renderizacao local em viewport estreita, confirmando dock em `Automacao SAP Desktop`, remocao das caixas antigas no formulario, mensagens vazias ocultas e versao `1.4.33`.
- Console do navegador sem erros ou avisos durante a validacao visual.
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.33` no codigo e no `embasa_settings.json` distribuido.
- Smoke test do executavel empacotado: processo iniciou em modo frozen, carregou `interface\index.html`, respeitou `require_sap_session=false` e permaneceu em execucao ate o encerramento do teste.

## Domingo, 07/06/2026 - Versao 1.4.32

**Ajuste aplicado**

- Adicionada fila de CPF/CNPJ para processar varios clientes em sequencia, cada um com seu proprio tipo, valor e lista de empreendimentos.
- A fila de empreendimentos existente foi preservada dentro de cada cliente, reaproveitando o checkpoint apenas enquanto o fluxo continua no mesmo CPF/CNPJ.
- Criado recurso de rascunhos de clientes para salvar dados incompletos e completar depois, com persistencia em `dados_compartilhados/rascunhos/rascunhos_clientes.json` e fallback local.
- Incluidos botoes `Adicionar cliente`, `Salvar rascunho` e `Limpar fila` na area de dados do empreendimento.
- Ao carregar um rascunho, a interface volta para criacao de boletos com CPF/CNPJ, tipo, valor e enderecos preenchidos para revisao.
- A validacao de execucao continua exigindo CPF/CNPJ, tipo, valor e endereco completo antes de colocar o cliente na fila pronta.
- Corrigido texto do botao de cancelamento da Multa Contratual quando o fluxo esta em execucao.
- Atualizada a versao do projeto de `1.4.31` para `1.4.32`.

**Validacao realizada**

- `python -m py_compile interface.py backend\settings.py backend\drafts.py`
- `node --check interface\app.js`
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- `git diff --check`
- Renderizacao local em `http://127.0.0.1:8767`, validando exibicao da fila de CPF/CNPJ, adicao de cliente pronto, salvamento de rascunho incompleto, carregamento do rascunho e bloqueio de execucao quando faltam dados obrigatorios.
- Console do navegador sem erros ou avisos durante os testes da nova fila.
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.32` no codigo e no `embasa_settings.json` distribuido.
- Smoke test do executavel empacotado: processo iniciou em modo frozen, carregou `interface\index.html`, respeitou `require_sap_session=false` e permaneceu em execucao ate o encerramento do teste.

## Quarta-feira, 03/06/2026 - Versao 1.4.31

**Ajuste aplicado**

- Adicionada a nova modalidade `Multa Contratual`, isolada dos boletos comuns de Viabilidade, Agua, Esgoto e Agua + Esgoto.
- Criada tela propria `Boleto de Multa Contratual` na sidebar, com validacao de CPF/CNPJ, valor sem limite maximo artificial e contrato numerico limitado a 9 digitos.
- Incluida API pywebview especifica `gerar_boleto_multa_contratual`, com validacao backend dedicada e retorno no mesmo padrao `{ok, etapa, mensagem, dados, erro_tecnico}`.
- Adicionado cadastro de cliente especifico para multa com canal/setor `MC`, escritorio `1010` e equipe `CAB`, preservando o cadastro normal dos boletos comuns.
- O XD03 passa a validar tambem o setor `MC`; quando ausente, o fluxo cria o setor necessario e retoma a multa pela entrada correta.
- A VA01 passou a ler canal, centro e condicao de pagamento por configuracao de tipo, permitindo a ordem `ZMTC`, canal/setor `MC`, condicao `C030`, material `900000000052` e centro de lucro `030002010L`.
- O texto padrao da Multa Contratual agora e montado dinamicamente com valor, valor por extenso, nome do cliente e CPF/CNPJ.
- O nome sugerido do PDF da multa segue o padrao `doc.fat - nome cliente - MULTA CONTRATUAL - contrato - valor.pdf`.
- O historico passou a registrar `Multa Contratual`, contrato e texto VA01 especifico, sem alterar os registros dos boletos comuns.
- Atualizada a versao do projeto de `1.4.30` para `1.4.31`.

**Validacao realizada**

- `python -m py_compile interface.py main.py backend\settings.py backend\controller.py backend\validators.py backend\valores.py backend\history.py backend\flows\cliente_cadastro.py backend\flows\xd03.py backend\flows\va01.py backend\flows\f110_boleto.py backend\flows\multa_contratual.py`
- `node --check interface\app.js`
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- `git diff --check`
- Renderizacao local em `http://127.0.0.1:8766`, validando abertura da tela `Multa Contratual`, mascara de CNPJ, valor alto `R$ 16.510,03`, contrato numerico `460018395` e validacao local de contrato obrigatorio.
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.31` confirmada no pacote.
- Smoke test do executavel empacotado: processo iniciado, permaneceu responsivo e encerrou normalmente apos a verificacao.

## Terça-feira, 02/06/2026 - Versao 1.4.30

**Ajuste aplicado**

- Corrigida a sobreposicao entre o modal `PDFCreator` e a confirmacao de continuidade da fila de empreendimentos.
- Quando os dois avisos estao abertos ao mesmo tempo, a interface ativa automaticamente um layout operacional compartilhado.
- Em telas largas, o nome do PDF fica visivel a esquerda e a confirmacao do proximo empreendimento a direita.
- Em janelas estreitas, os modais ficam separados entre a metade superior e inferior da tela, com rolagem interna quando necessaria.
- Os dois cards permanecem clicaveis de forma independente, sem alterar a execucao SAP, a fila ou a espera de confirmacao do usuario.
- Atualizada a versao do projeto de `1.4.29` para `1.4.30`.

**Validacao realizada**

- `node --check interface\app.js`
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- `git diff --check`
- Renderizacao local dos dois modais simultaneos em largura ampla e reduzida.
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.30` confirmada no pacote.
- Smoke test do executavel empacotado: processo iniciado, permaneceu responsivo e encerrou normalmente apos a verificacao.

## Terça-feira, 02/06/2026 - Versao 1.4.29

**Ajuste aplicado**

- Ativado o envio funcional do formulario `Fale Conosco` para `augusto.cruz@embasa.ba.gov.br`.
- O canal padrao passou a ser `outlook_desktop`: a aplicacao usa o perfil corporativo ja autenticado no Outlook classico do Windows, evitando armazenar senha no executavel ou no arquivo de configuracao.
- Mantido o canal `smtp` como alternativa configuravel para ambientes que possuam servidor, remetente e credenciais proprias.
- Imagens JPG, JPEG e PNG anexadas pelo usuario agora sao gravadas em pasta temporaria, inseridas no e-mail do Outlook e removidas automaticamente depois do envio.
- Adicionada validacao do conteudo base64 e da consistencia do tamanho dos anexos antes da entrega.
- Se o Outlook nao estiver disponivel ou conectado, a interface informa ao usuario que deve abrir o Outlook corporativo e tentar novamente.
- A confirmacao de sucesso agora apresenta o protocolo `FAFTA-AAAAMMDD-HHMMSS` do atendimento.
- Mantido o snapshot local em `%LOCALAPPDATA%\EMBASA\atendimentos` para rastreio do pedido.
- Atualizada a versao do projeto de `1.4.28` para `1.4.29`.

**Validacao realizada**

- `python -m py_compile interface.py main.py backend\settings.py backend\support_mail.py`
- `node --check interface\app.js`
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- Teste isolado com Outlook simulado, validando destino, assunto, corpo, anexos, envio e remocao da pasta temporaria.
- Teste isolado do canal SMTP preservado.
- Teste de rejeicao de anexo base64 invalido.
- Renderizacao local do modal `Fale Conosco` em `http://127.0.0.1:8765`, com abertura pelo botao, campos obrigatorios, anexos, botao de envio e console sem erros ou avisos.
- Validacao visual do formulario vazio: a interface exibiu `Informe a matricula.` sem fechar ou travar o modal.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.29`, canal `outlook_desktop` e destino `augusto.cruz@embasa.ba.gov.br` confirmados no pacote.
- Smoke test do executavel empacotado: processo iniciado, permaneceu responsivo e encerrou normalmente apos a verificacao.

## Segunda-feira, 01/06/2026 - Versao 1.4.28

**Ajuste aplicado**

- Restaurada na sidebar a entrada manual `Criar cliente`, mantendo o formulario cadastral dentro da interface.
- O cadastro manual aceita CPF/CNPJ e tipo de solicitacao editaveis; apos sucesso, retorna automaticamente para a criacao de boletos com esses dois campos reaproveitados.
- Mantida a retomada automatica ja existente quando o cadastro de cliente foi iniciado por um boleto pendente: depois do XD01, o fluxo volta ao boleto original e pesquisa o codigo pelo CPF/CNPJ no XD03.
- A captura do nome no XD03 deixou de usar a varredura recursiva de textos visiveis da tela.
- Toda leitura de nome agora envia `CTRL + F1` por `sendVKey(25)` e repete o comando ate os campos oficiais `DATA-NAME1` e `DATA-NAME2` estarem disponiveis, aguardando a renderizacao entre tentativas e mantendo limite de seguranca para telas SAP inesperadas.
- `DATA-NAME1` e `DATA-NAME2` passaram a ser a unica fonte utilizada para montar o nome do cliente, tanto para clientes existentes quanto para clientes recem-criados localizados novamente no XD03.
- Removida a maximizacao paralela da janela SAP que existia dentro do antigo fallback de captura do nome.
- Atualizada a versao do projeto de `1.4.27` para `1.4.28`.

**Validacao realizada**

- `python -m py_compile interface.py main.py backend\settings.py backend\controller.py backend\flows\cliente_cadastro.py backend\flows\xd03.py backend\utils\sap_waits.py`
- `node --check interface\app.js`
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- Teste isolado do XD03 com sessao SAP simulada, validando repeticao de `CTRL + F1` ate `DATA-NAME1` e `DATA-NAME2`.
- Teste estrutural da sidebar e da navegacao manual para `Criar cliente`.
- `git diff --check`
- Renderizacao local da interface em `http://127.0.0.1:8765`: sidebar com a nova acao `CL`, rodape `1.4.28` e console sem erros ou avisos.
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.28` confirmada no pacote.
- Smoke test do executavel empacotado: processo iniciado, permaneceu responsivo e encerrou normalmente apos a verificacao.

## Segunda-feira, 01/06/2026 - Versao 1.4.27

**Ajuste aplicado**

- Corrigido o preenchimento fiscal de clientes pessoa fisica no XD01.
- CPF e CNPJ agora usam o mesmo campo fiscal SAP `KNA1-STCD1`, conforme o layout EMBASA gravado.
- A inscricao estadual `KNA1-STCD3 = ISENTO` volta a ser preenchida obrigatoriamente tambem para CPF.
- Removida a tentativa paralela de preencher `KNA1-STCD2` e marcar `KNA1-STKZN`, pois esses controles nao pertencem ao roteiro EMBASA utilizado pelo aplicativo.
- O grupo de contas `PF01` ou `PJ01` passou a ser obrigatorio na primeira tela da criacao do cliente; se o SAP rejeitar o valor, o fluxo informa a falha em vez de seguir silenciosamente com campos vazios.
- Mantida a flexibilidade do grupo de contas na extensao posterior de setores para clientes ja existentes.
- Atualizada a versao do projeto de `1.4.26` para `1.4.27`.

**Validacao realizada**

- `python -m py_compile backend\flows\cliente_cadastro.py interface.py backend\controller.py backend\flows\xd03.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado do preenchimento fiscal com CPF e CNPJ, validando `STCD1`, `STCD3 = ISENTO` e ausencia de chamadas a `STCD2/STKZN`.
- Teste isolado da primeira tela do XD01, validando envio de `PF01`.
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.27` confirmada no pacote.
- Smoke test do executavel empacotado: processo iniciado, permaneceu responsivo e encerrou normalmente apos a verificacao.

## Segunda-feira, 01/06/2026 - Versao 1.4.26

**Ajuste aplicado**

- Removida a tentativa de capturar o codigo do cliente pela barra de status logo apos salvar o cadastro no XD01.
- O cadastro inicial agora cria somente o cliente com o setor padrao de Viabilidade (`AE`) e conclui sem depender de um numero SAP ainda indisponivel.
- Depois do cadastro, a interface retorna automaticamente ao boleto original e reinicia o fluxo pelo XD03 usando o CPF/CNPJ informado.
- A retomada usa a mesma entrada da criacao de boletos para preservar tambem lotes com varios empreendimentos.
- O XD03 passa a ser o ponto unico para localizar o codigo real do novo cliente.
- Quando o tipo solicitado exigir outro setor, a verificacao existente do XD03 identifica a ausencia, cria os setores necessarios com o codigo localizado e retoma o boleto automaticamente.
- Acoes cadastrais intermediarias deixaram de preencher o card de resultado final antes da criacao efetiva do boleto.
- Removidos da sidebar a criacao manual isolada de cliente e o modal intermediario de confirmacao, pois o cadastro agora nasce exclusivamente de um boleto com cliente nao localizado.
- Atualizada a versao do projeto de `1.4.25` para `1.4.26`.

**Validacao realizada**

- `python -m py_compile interface.py backend\flows\cliente_cadastro.py backend\flows\xd03.py backend\controller.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado do encerramento do XD01 sem codigo na barra de status.
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- Revisao por busca de referencias antigas do modal e da criacao manual isolada.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.26` confirmada no pacote.
- Smoke test do executavel empacotado: processo iniciado, permaneceu responsivo e encerrou normalmente apos a verificacao.

## Segunda-feira, 01/06/2026 - Versao 1.4.25

**Ajuste aplicado**

- Integradas as alteracoes recebidas para manter a sessao SAP ativa enquanto o aplicativo permanece aberto e ocioso.
- Criada a classe `SapKeepAlive`, com ping silencioso a cada 60 segundos e descarte automatico de referencias antigas da sessao SAP.
- O keep-alive agora inicializa e finaliza COM dentro da propria thread, seguindo o requisito do Windows para acesso COM por thread.
- Adicionado bloqueio nao concorrente para impedir que o keep-alive dispute a sessao com geracao de boletos, cadastro de cliente ou criacao de setores.
- O ping ignora sessoes SAP ocupadas (`Busy`) para evitar chamadas que poderiam bloquear a thread em comunicacoes pendentes com o servidor.
- Ao fechar a interface, o aplicativo solicita explicitamente a parada da thread de keep-alive.
- Ao abrir o modal final do PDFCreator, o frontend reforca a copia automatica do nome do boleto sem chamar o backend e sem bloquear o fluxo SAP.
- Incluido `pythoncom` nos imports empacotados do PyInstaller.
- Atualizada a versao do projeto de `1.4.24` para `1.4.25`.

**Validacao realizada**

- `python -m py_compile interface.py main.py backend\utils\sap_waits.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado de `SapKeepAlive` com sessao SAP simulada, cobrindo ping permitido, sessao ocupada e bloqueio durante fluxo principal.
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com versao `1.4.25`, `pythoncom311.dll` e `pywintypes311.dll` confirmados no pacote.
- Smoke test do executavel empacotado: processo iniciado, permaneceu responsivo e encerrou normalmente apos a verificacao.

**Validacao operacional recomendada**

- Manter uma sessao SAP real ociosa por um periodo superior ao timeout configurado no servidor para confirmar o efeito do ping no ambiente corporativo.

## Quinta-feira, 28/05/2026 - Versao 1.4.24

**Ajuste aplicado**

- Ao concluir o fluxo de boleto com sucesso na F110, a tela agora limpa os campos preenchidos da criacao de boleto sem apagar o resultado final, logs ou status de conclusao.
- Em lotes de empreendimentos, a limpeza dos campos acontece apenas depois que todos os itens terminam, preservando os payloads ja montados durante a execucao.
- Na criacao de cliente aberta a partir da criacao de boleto, o cadastro passou a reaproveitar apenas CPF/CNPJ, nome quando enviado no payload, e tipo de solicitacao.
- Removido o reaproveitamento automatico do endereco do empreendimento na tela de criacao de cliente.
- Atualizada a versao do projeto de `1.4.23` para `1.4.24`.

**Validacao realizada**

- `python -m py_compile interface.py backend\settings.py`
- `node --check interface\app.js`
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- Revisao por busca dos novos pontos `limparFormularioCriacaoBoleto` e `preencherCadastroClienteComPayload`.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com arquivos do pacote confirmando a versao `1.4.24`.

## Quinta-feira, 28/05/2026 - Versao 1.4.23

**Ajuste aplicado**

- Revisado o fluxo do modal de boleto no processo `Agua + Esgoto`.
- Quando um novo nome de PDF chega enquanto o modal de boleto anterior ainda esta aberto, o frontend agora enfileira o proximo aviso em vez de trocar o texto do modal atual.
- A fila continua sem chamar `pywebview.api` e sem bloquear o backend SAP; o proximo nome aparece apenas depois que o usuario fecha o modal atual.
- Removida a funcao frontend morta `confirmarAvisoOperacional`, eliminando qualquer indicio de confirmacao backend no modal de boleto.
- Atualizada a versao do projeto de `1.4.22` para `1.4.23`.

**Validacao realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- Revisao por busca de chamadas antigas de modal do meio de pagamento e chamadas `pywebview.api` no modal de boleto.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com arquivos do pacote confirmando a versao `1.4.23`.

## Quinta-feira, 28/05/2026 - Versao 1.4.22

**Ajuste aplicado**

- Adicionada a box `Meio de pagamento` na area de resultado do andamento do processo.
- O backend agora envia o nome padrao do arquivo de meio de pagamento antes de abrir a etapa de salvamento, no formato `ano.mes.dia - doc.fat`.
- A box `Meio de pagamento` copia o texto apenas no clique do usuario, usando clipboard local no frontend e sem chamada `pywebview.api`.
- Removido o modal de meio de pagamento, evitando reentrada frontend/backend durante a etapa do Explorer.
- O resultado final passou a preservar `nome_arquivo_meio_pagamento`, inclusive no fluxo composto `Agua + Esgoto`.
- Atualizada a versao do projeto de `1.4.21` para `1.4.22`.

**Validacao realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- Teste isolado da montagem do nome do meio de pagamento e da preservacao do evento `PAYMENT_FILE_READY::` no fluxo composto.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com arquivos do pacote confirmando a versao `1.4.22`.

## Quinta-feira, 28/05/2026 - Versao 1.4.21

**Ajuste aplicado**

- A box final do andamento do processo foi simplificada para exibir apenas `Cliente` e `Doc. fat`, removendo `Pedido` e `Boleto`.
- O historico passou a gravar o campo `numero_bol` com a identificacao BOL real usada na F110, priorizando `BOL01`, `BOL02` ou a lista por tipo no fluxo `Agua + Esgoto`.
- A tela de detalhe do historico passou a exibir o campo como `Numero do BOL`, mantendo compatibilidade com registros antigos que ainda usam `identificacao_pagamento` ou `boleto`.
- A busca do historico agora considera tambem `numero_bol` e `identificacao_pagamento`.
- Atualizada a versao do projeto de `1.4.20` para `1.4.21`.

**Validacao realizada**

- `python -m py_compile interface.py backend\controller.py backend\history.py backend\flows\f110.py backend\settings.py`
- `node --check interface\app.js`
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com arquivos do pacote confirmando a versao `1.4.21`.

## Quinta-feira, 28/05/2026 - Versao 1.4.20

**Ajuste aplicado**

- No cadastro de cliente, `Tipo de solicitacao` e `Tratamento` passaram a usar dropdown visual no mesmo padrao da tela de criacao de boletos.
- Os campos `Telefone` e `E-mail` agora exibem o marcador discreto `Opcional` no canto direito do rotulo.
- Corrigido o estado minimizado da sidebar para manter os icones de Historico, tema e Sobre redondos, sem achatamento.
- Ao abrir o modal `Sobre`, a sidebar e recolhida e fica travada no estado compacto enquanto o modal estiver aberto.
- O log operacional deixou de exibir mensagens-resumo duplicadas como `Resumo da falha...` e o `msg` final quando ja existe diagnostico detalhado no painel.
- Atualizada a versao do projeto de `1.4.19` para `1.4.20`.

**Validacao realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\xd03.py backend\flows\cliente_cadastro.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com arquivos do pacote confirmando a versao `1.4.20`.

## Quinta-feira, 28/05/2026 - Versao 1.4.19

**Ajuste aplicado**

- Corrigido o modal do PDFCreator para nao executar mais copia nem chamada `pywebview.api` ao clicar; o backend ja copia o nome automaticamente e o botao agora apenas fecha o aviso.
- Removida a chamada frontend `preparar_janela_aviso_operacional`, evitando reentrada JavaScript -> Python durante a exibicao do modal.
- Centralizado o foco/maximizacao da interface em uma unica chamada do backend quando chega o evento `PDF_NAME_READY`.
- Simplificada a rotina `_trazer_interface_para_frente`, removendo a duplicidade de `show` e `maximize`.
- A emissao de JavaScript pelo backend passou a preferir `window.run_js`, sem retorno sincronizado, com fallback para `evaluate_js`.
- Atualizada a versao do projeto de `1.4.18` para `1.4.19`.

**Validacao realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\xd03.py backend\flows\cliente_cadastro.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Checagem de handlers declarados no HTML contra `interface\app.js`.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com arquivos do pacote confirmando a versao `1.4.19`.

## Quarta-feira, 27/05/2026 - Versao 1.4.18

**Ajuste aplicado**

- Integrados os arquivos revisados enviados em `EMBASA_ARQUIVOS_ATUAIS_MODIFICADOS.zip` sobre a base `1.4.17`.
- O meio de pagamento na F110 voltou ao fluxo manual estavel: `Shift+F6` seguido imediatamente de `F4`, sem modal, copia, pausa ou controle do Explorer entre esses comandos.
- A automacao agora aguarda indefinidamente o usuario concluir o salvamento manual do arquivo no Explorer antes de confirmar o SAP e seguir para a SP02.
- O modal de nome do PDF na SP02 passou a ser apenas informativo; o botao copia e fecha localmente, sem chamada de confirmacao para o backend.
- A montagem do nome do PDF recebeu filtros para ignorar textos operacionais do SAP e priorizar o nome real do cliente.
- O cadastro de cliente diferencia CPF e CNPJ: pessoa juridica preenche CNPJ/ISENTO, enquanto pessoa fisica preenche CPF, marca a checkbox de pessoa fisica e nao envia ISENTO.
- Os dados financeiros do cliente agora incluem condicao de pagamento `0001`, meio de pagamento `A` e banco parceiro `BB100`.
- A XD03 recebeu fallback com `CTRL+F1` quando Nome 1/Nome 2 nao aparecem na primeira leitura.
- Atualizada a versao do projeto de `1.4.17` para `1.4.18`.

**Validacao realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\xd03.py backend\flows\cliente_cadastro.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- `node` check de handlers declarados no HTML contra `interface\app.js`.
- `git diff --check`
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com arquivos do pacote confirmando a versao `1.4.18`.

## Terça-feira, 26/05/2026 - Versão 1.4.17

**Ajuste aplicado**

- O rótulo `Documento` foi trocado por `Cliente` nas áreas de entrada CPF/CNPJ.
- Removido o campo visível `Complemento do nome` do cadastro; o backend continua dividindo automaticamente `Nome 1`, `Nome 2` e temas de pesquisa conforme os limites do SAP.
- `Tratamento` foi movido para o bloco superior junto de `Cliente` e `Tipo de solicitação`; quando o cliente é CNPJ, o campo trava automaticamente como `Empresa`.
- `Inscrição estadual` ficou travada como `ISENTO`.
- O cadastro de cliente agora valida os obrigatórios em sequência, destacando o primeiro campo pendente; apenas telefone e e-mail permanecem opcionais.
- O CEP do cadastro passou a consultar automaticamente o ViaCEP, preencher rua, bairro, cidade e UF quando disponível e bloquear CEP incompleto com 8 dígitos ausentes.
- Removido o atalho `Criar Setor` da sidebar; quando o fluxo de boleto detectar setor ausente, a criação do setor é acionada automaticamente pelo tipo de solicitação.
- O monitor de andamento agora troca as etapas conforme a seção: boleto usa o fluxo completo, cliente usa apenas `XD01 - Criar cliente` e setor automático usa apenas `XD01 - Criar setor`.
- Ao concluir criação de cliente, a interface mostra o modal `Cliente Criado: <número>` com os botões `Prosseguir para Criação de Boleto` e `Fechar`; ao prosseguir, CPF/CNPJ e tipo de solicitação são preenchidos na tela de boleto.
- Atualizada a versão do projeto de `1.4.16` para `1.4.17`.

**Validação realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\xd03.py backend\flows\cliente_cadastro.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Rebuild empresarial concluído em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com arquivos do pacote confirmando a versão `1.4.17`.

## Terça-feira, 26/05/2026 - Versão 1.4.16

**Ajuste aplicado**

- Removido o campo `Documento` da tela manual `Criar Setor`; agora o usuário informa apenas o número do cliente SAP e os setores desejados.
- A criação manual de setores passou a normalizar a ordem no backend: `AE`/Viabilidade primeiro, `AG`/Água em seguida e `EG`/Esgoto por último, mesmo que o usuário marque em outra sequência.
- Quando o SAP indicar que o setor selecionado já existe para o cliente, o fluxo trata como aviso operacional em amarelo, sem exibir falha vermelha para esse caso.
- Se o usuário selecionar `Água` e `Esgoto`, ou marcar os três setores, a execução segue sempre na ordem operacional definida.
- Atualizada a versão do projeto de `1.4.15` para `1.4.16`.

**Validação realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\xd03.py backend\flows\cliente_cadastro.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado da ordenação de setores confirmando `EG, AG, AE` como entrada e `AE, AG, EG` como saída.
- Rebuild empresarial concluído em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com arquivos do pacote confirmando a versão `1.4.16`.

## Terça-feira, 26/05/2026 - Versão 1.4.15

**Ajuste aplicado**

- Adicionada sidebar fixa à esquerda com menu de três barras, logo da EMBASA, atalhos para `Criação de boletos`, `Criar Cliente` e `Criar Setor`.
- Movidos `Histórico`, `Modo claro/escuro` e `Sobre` para o rodapé da sidebar, mantendo a paleta e os estados visuais da interface.
- Criada tela manual de `Criar Cliente`, usando as mesmas validações do cadastro SAP: CPF/CNPJ completo, tipo de solicitação, tratamento, endereço obrigatório, UF por sigla, telefone opcional e e-mail opcional.
- Criada tela manual de `Criar Setor`, com seleção de `AE`, `AG` e `EG` e exibição dos modelos operacionais: `AE/AG = 1055 + DM` e `EG = 1070 + ME`.
- As ações manuais de cliente e setor agora chamam diretamente as APIs `cadastrar_cliente_sap` e `adicionar_setores_cliente_sap`, exibindo retorno na própria tela e logs operacionais.
- Atualizada a versão do projeto de `1.4.14` para `1.4.15`.

**Validação realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\xd03.py backend\flows\cliente_cadastro.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Checagem estática da interface confirmando que todas as funções chamadas pelo HTML existem no `app.js` e que os IDs do HTML são únicos.
- Rebuild empresarial concluído em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`, com arquivos do pacote confirmando a versão `1.4.15`.

## Terça-feira, 26/05/2026 - Versão 1.4.14

**Ajuste aplicado**

- Cadastro de cliente passou a quebrar `Nome 1`, `Nome 2`, `Tema de pesquisa 1` e `Tema de pesquisa 2` em partes menores, respeitando o limite operacional de aproximadamente 15/17 caracteres.
- Para CNPJ, o tratamento do cliente é `Empresa`; para CPF, o tratamento é inferido por prefixos como `Sr`, `Sra`, `Senhor`, `Senhora` ou `Dona`.
- Adicionado campo de tratamento no cadastro (`Automático`, `Empresa`, `Sr`, `Sra`) para permitir ajuste manual quando necessario.
- CEP passou a ser normalizado obrigatoriamente no formato `00000-000`.
- Estado do cadastro passou a aceitar qualquer UF informada por sigla de 2 letras, não apenas `BA`.
- Telefone opcional passou a ser normalizado no formato `(00) 0000-0000` ou `(00) 00000-0000`.
- Documento fiscal mantém CNPJ/CPF sem máscara, e inscrição estadual `ISENTO` passa a ser enviada como campo obrigatório.
- Dados de empresa agora usam `C-OUTRECPJ` para CNPJ e `C-OUTRECPF` para CPF.
- Atualizada a versão do projeto de `1.4.13` para `1.4.14`.

**Validação realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\xd03.py backend\flows\cliente_cadastro.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado de normalização do cadastro com CNPJ e CPF, validando tratamento `Empresa/Sra`, quebra de nome, CEP, UF, telefone e `C-OUTRECPJ/C-OUTRECPF`.
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`.

## Terça-feira, 26/05/2026 - Versão 1.4.13

**Ajuste aplicado**

- A criação de cliente novo agora sempre inicia pelo setor de viabilidade `AE`, seguindo o fluxo do VBS `criacaocliente.vbs`.
- Quando o tipo solicitado for `Água`, `Esgoto` ou `Água + Esgoto`, o sistema cria primeiro o cliente em `AE` e depois adiciona automaticamente os setores necessários `AG` e/ou `EG`.
- Evita criar cliente novo diretamente em `AG` ou `EG`, mantendo o padrão operacional usado no SAP.
- Atualizada a versão do projeto de `1.4.12` para `1.4.13`.

**Validação realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\xd03.py backend\flows\cliente_cadastro.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado simulando cliente novo em `Água + Esgoto`, confirmando criação inicial em `AE` e adição posterior de `AG` e `EG`.
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`.

## Segunda-feira, 25/05/2026 18:13:15 - Versão 1.4.12

**Problema identificado**

Quando a `XD03` nao localizava o CPF/CNPJ ou encontrava o cliente sem o setor necessario, o fluxo parava apenas como falha operacional. O usuario precisava resolver manualmente no SAP e depois tentar novamente, mesmo existindo scripts VBS para criacao de cliente e extensao dos setores `AG`, `EG` e `AE`.

**O que foi alterado**

- Convertidos os VBS `criacaocliente.vbs` e `adicionandosetor.vbs` para um novo modulo Python isolado em `backend/flows/cliente_cadastro.py`.
- A `XD03` agora devolve pendencias estruturadas para a interface:
  - `cliente_nao_cadastrado`, quando o documento nao existe no SAP.
  - `setor_ausente`, quando o cliente existe, mas nao possui o setor necessario para o tipo selecionado.
- A interface passou a exibir um modal de decisao para criar cliente ou criar setores antes de continuar.
- Para cliente novo, foi adicionada uma aba de cadastro com os campos necessarios de nome, endereco, telefone, e-mail e inscricao estadual.
- Para setor ausente, a criacao usa dados padrao do SAP, sem exigir uma aba propria.
- Apos criar cliente ou setores, a interface retoma automaticamente o fluxo padrao a partir da validacao normal da `XD03`.
- Atualizada a versao do projeto de `1.4.11` para `1.4.12`.

**Arquivos alterados**

- `backend/flows/cliente_cadastro.py`
- `backend/flows/xd03.py`
- `backend/controller.py`
- `interface.py`
- `interface/app.js`
- `interface/index.html`
- `interface/style.css`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `LEIA-ME_EMPRESA.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Se o CPF/CNPJ nao existir, o usuario recebe a opcao de cadastrar o cliente pela interface. Depois do cadastro, o sistema volta ao fluxo normal. Se apenas faltar setor, o usuario confirma a criacao dos setores padrao e o fluxo tambem volta automaticamente para a validacao e criacao do boleto.

**Validação realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\xd03.py backend\flows\cliente_cadastro.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado de normalizacao do cadastro, validando CNPJ, grupo de conta `PJ01` e setores `AG/EG` para `agua_esgoto`.
- Rebuild empresarial concluido em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`.

## Segunda-feira, 25/05/2026 17:31:18 - Versão 1.4.11

**Problema identificado**

Após abrir o `Salvar como` do Windows no meio de pagamento, a automação ainda esperava o retorno do SAP com timeout curto. Se o usuário demorasse para escolher local/nome e salvar o arquivo, o código falhava antes de concluir o meio de pagamento e, por consequência, não chegava na `SP02`.

**O que foi alterado**

- Criada espera sem limite de tempo para o salvamento do arquivo de meio de pagamento.
- Depois do `F4`, o sistema aguarda o usuário fechar/salvar a janela do Explorer pelo tempo necessário, inclusive por horas.
- A automação só pressiona a confirmação do SAP e segue para `SP02` quando o SAP volta a disponibilizar o botão de confirmação.
- Adicionado aviso simples, sem clique, informando que o nome do meio de pagamento foi copiado para colar no campo `Nome do arquivo`.
- O aviso simples não traz a interface para frente; a interface só é trazida para frente nos avisos de `SP02/PDFCreator`.
- Atualizada a versão do projeto de `1.4.10` para `1.4.11`.

**Arquivos alterados**

- `backend/flows/f110_boleto.py`
- `interface.py`
- `interface/app.js`
- `interface/style.css`
- `interface/index.html`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `LEIA-ME_EMPRESA.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Ao abrir o Explorer para salvar o arquivo de meio de pagamento, o usuário pode demorar o tempo que precisar. Assim que salvar/fechar a janela, a automação continua normalmente e só então segue para a `SP02`.

**Validação realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado de `_aguardar_salvamento_meio_pagamento`, simulando o Explorer aberto antes do retorno do botão SAP.
- Rebuild empresarial concluído em `dist\EmbasaPedidosSAP\EmbasaPedidosSAP.exe`.

## Segunda-feira, 25/05/2026 17:22:03 - Versão 1.4.10

**Problema identificado**

O fluxo travava antes da `SP02`, ainda na etapa de meio de pagamento da `F110`. A causa provável era a espera de confirmação do aviso operacional entre backend Python e frontend pywebview: o backend pausava aguardando o modal, enquanto a interface precisava responder por `pywebview.api`, criando risco de deadlock e impedindo a abertura/continuidade da janela de salvamento do arquivo.

**O que foi alterado**

- O aviso de meio de pagamento deixou de abrir modal bloqueante e deixou de aguardar confirmação do frontend.
- O nome do arquivo de meio de pagamento continua sendo copiado para a área de transferência pelo backend antes da janela de salvamento.
- A automação segue imediatamente para o `F4/Explorer` e confirmação do arquivo, sem depender do botão `Copiar nome e fechar`.
- Protegido o backend para ignorar qualquer tentativa futura de aviso operacional bloqueante do tipo `payment`.
- O frontend passou a tratar eventos legados `PAYMENT_FILE_READY::` apenas copiando o texto, sem abrir o modal de meio de pagamento.
- Mantido o modal da `SP02/PDFCreator`, porque ele ocorre depois do meio de pagamento e faz parte da etapa de impressão/exportação do boleto.
- Atualizada a versão do projeto de `1.4.9` para `1.4.10`.

**Arquivos alterados**

- `backend/flows/f110_boleto.py`
- `interface.py`
- `interface/app.js`
- `interface/index.html`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `LEIA-ME_EMPRESA.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Ao chegar no meio de pagamento, o sistema deve copiar o nome `AAAA.MM.DD - DOC_FAT`, continuar o SAP sem esperar a interface e só depois avançar para a `SP02` quando o salvamento for concluído.

**Validação realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado confirmando que `_aguardar_copia_interface` no tipo `payment` não chama `notice_callback`, não emite `PAYMENT_FILE_READY::` e retorna imediatamente.
- Teste isolado confirmando que `_aguardar_aviso_operacional('payment')` retorna sem criar espera por confirmação.

## Segunda-feira, 25/05/2026 00:34:47 - Versão 1.4.9

**Problema identificado**

Quando o SAP ou outra aplicação estivesse em primeiro plano, os modais operacionais da interface poderiam não aparecer com destaque suficiente para o usuário copiar o nome do PDF ou do arquivo de meio de pagamento. No fluxo Água + Esgoto também era necessário evitar conflito entre avisos consecutivos de dois pedidos.

**O que foi alterado**

- A janela principal da interface agora é restaurada, maximizada e trazida para frente quando um aviso operacional é emitido.
- O backend expõe `preparar_janela_aviso_operacional` para reforçar o foco/maximização também quando o modal é aberto pelo JavaScript.
- Os modais de PDF/SP02 e meio de pagamento chamam a preparação da janela antes de abrir.
- Criada uma fila simples para avisos operacionais no frontend, evitando que um segundo aviso de Água + Esgoto substitua o modal que ainda está aberto.
- A fila de avisos é limpa ao reiniciar o painel para não reaproveitar avisos antigos.
- Atualizada a versão do projeto de `1.4.8` para `1.4.9`.

**Arquivos alterados**

- `interface.py`
- `interface/app.js`
- `interface/index.html`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `LEIA-ME_EMPRESA.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Ao chegar nos modais de SP02/PDFCreator ou meio de pagamento, a interface deve voltar para a frente da tela, maximizada, mesmo que o usuário esteja no SAP ou em outra aplicação. No fluxo Água + Esgoto, os avisos devem ser tratados em sequência.

**Validação realizada**

- `python -m py_compile interface.py backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py backend\settings.py`
- `node --check interface\app.js`
- Validação renderizada em `http://127.0.0.1:8768/index.html`, confirmando versão `1.4.9`, modal de meio de pagamento e botões de cópia sem erros de console.

## Segunda-feira, 25/05/2026 00:25:53 - Versão 1.4.8

**Problema identificado**

Na etapa de meio de pagamento, o usuário precisa copiar um nome padrão para salvar o arquivo gerado pela F110. A interface já possuía a base do aviso, mas o texto do modal ainda indicava que o nome estava copiado antes da ação do usuário.

**O que foi alterado**

- Ajustado o modal de meio de pagamento para exibir `Nome do arquivo pronto`.
- A instrução do modal agora orienta copiar o nome e colar na janela de salvamento do arquivo.
- Mantido o padrão do nome do meio de pagamento como `ano.mês.dia - doc.fat`, por exemplo `2026.05.25 - 1234567890`.
- Mantido o comportamento sem etapa extra: ao clicar em `Copiar nome e fechar`, o nome é copiado, o modal fecha e a automação segue para a janela de salvamento.
- Atualizada a versão do projeto de `1.4.7` para `1.4.8`.

**Arquivos alterados**

- `interface/index.html`
- `interface/app.js`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `LEIA-ME_EMPRESA.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Quando a F110 chegar ao salvamento do arquivo de meio de pagamento, a interface deve abrir um modal no mesmo estilo do modal da SP02, exibindo o nome `AAAA.MM.DD - DOC_FAT` para copiar e fechar.

**Validação realizada**

- `python -m py_compile backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py interface.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado de `montar_nome_arquivo_meio_pagamento`, confirmando `2026.05.25 - 1234567890`.
- Validação renderizada em `http://127.0.0.1:8767/index.html`, confirmando modal de meio de pagamento, título, instrução, botão `Copiar nome e fechar` e versão `1.4.8`.

## Segunda-feira, 25/05/2026 00:14:11 - Versão 1.4.7

**Problema identificado**

O botão `Histórico` ficava separado na área inferior do painel de andamento, enquanto `Sobre` e `Modo` estavam agrupados na barra superior. Além disso, o histórico usava uma cor própria, diferente dos botões superiores.

**O que foi alterado**

- Movido o botão `Histórico` para a barra superior, ao lado de `Sobre` e `Modo`.
- O botão `Histórico` passou a usar o mesmo estilo visual dos botões superiores.
- Removido o botão `Histórico` da área inferior de ações do painel de andamento.
- Atualizada a versão do projeto de `1.4.6` para `1.4.7`.

**Arquivos alterados**

- `interface/index.html`
- `interface/app.js`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `LEIA-ME_EMPRESA.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Na barra superior, `Sobre`, `Histórico` e `Modo` devem aparecer juntos, com a mesma linguagem de cor, altura e borda.

**Validação realizada**

- `python -m py_compile backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py interface.py backend\settings.py`
- `node --check interface\app.js`
- Validação renderizada em `http://127.0.0.1:8766/index.html`, confirmando `Sobre`, `Histórico` e `Modo` na barra superior, sem botão de histórico na área inferior.
- Clique no botão `Histórico` validado, abrindo o modal correspondente.

## Segunda-feira, 25/05/2026 00:05:20 - Versão 1.4.6

**Problema identificado**

O card `Fluxo principal` estava com o conteúdo alinhado à esquerda dentro da box, deixando o bloco visualmente desequilibrado em relação aos demais cards da área superior.

**O que foi alterado**

- Adicionada uma classe própria para o card `Fluxo principal`.
- Centralizado o título e a sequência do fluxo dentro da box.
- Ajustada a quebra da sequência do fluxo para evitar estouro visual em larguras menores.
- Atualizada a versão do projeto de `1.4.5` para `1.4.6`.

**Arquivos alterados**

- `interface/index.html`
- `interface/style.css`
- `interface/app.js`
- `backend/settings.py`
- `embasa_settings.json`
- `VERSAO.txt`
- `LEIA-ME_EMPRESA.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

O card `Fluxo principal` deve aparecer com seu conteúdo centralizado horizontalmente dentro da própria box, mantendo o espaçamento e a leitura da sequência do processo.

**Validação realizada**

- `python -m py_compile backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py interface.py backend\settings.py`
- `node --check interface\app.js`
- Validação renderizada em `http://127.0.0.1:8765/index.html`, confirmando `align-items: center`, `text-align: center` e centralização horizontal do título e da sequência do fluxo.

## Domingo, 24/05/2026 19:36:23 - Versão 1.4.5

**Problema identificado**

O log curto ainda podia descrever a etapa inteira como se todas as ações tivessem sido tentadas. Em `XD03`, por exemplo, uma falha ao buscar o cliente não deve indicar captura de nome ou validação de setor, porque essas ações dependem da busca ter passado.

**O que foi alterado**

- A linha `Sistema tentou executar` agora é escolhida pela causa retornada no erro, não apenas pela etapa geral.
- `XD03` passou a diferenciar busca do cliente, captura do nome, abertura da ajuda de pesquisa e validação do setor de atividade.
- `VA01` passou a diferenciar criação do pedido, preenchimento de valor, endereço e salvamento.
- `F110` passou a diferenciar identificação BOL, seleção livre com `doc.fat`, geração do meio de pagamento e SP02/boleto.
- Falhas de sessão SAP no fluxo Água + Esgoto passam a ser diagnosticadas como `CONEXAO`, mantendo a marcação visual em `XD03` quando necessário porque a interface não possui etapa visual de conexão.
- Atualizada a versão do projeto de `1.4.4` para `1.4.5`.

**Arquivos alterados**

- `backend/controller.py`
- `backend/settings.py`
- `interface/app.js`
- `interface/index.html`
- `embasa_settings.json`
- `VERSAO.txt`
- `LEIA-ME_EMPRESA.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Ao ocorrer falha, o log deve mostrar somente a tarefa efetivamente tentada antes da parada, como `buscar o cliente pelo CPF/CNPJ`, `validar o setor de atividade do cliente` ou `conectar em uma sessão SAP logada`.

**Validação realizada**

- `python -m py_compile backend\controller.py backend\flows\f110.py backend\flows\f110_boleto.py interface.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado de falhas em `XD03` e `CONEXAO`, confirmando ação atômica e mascaramento do documento.

## Domingo, 24/05/2026 19:28:48 - Versão 1.4.4

**Problema identificado**

O diagnóstico da versão 1.4.3 ficou completo, mas grande demais para o balão de logs operacional. O usuário precisava de uma leitura mais direta, em tópicos, com ação tentada, erro, problema provável e solução.

**O que foi alterado**

- Reduzido o diagnóstico público de falha para tópicos objetivos.
- Cada etapa agora informa `Sistema tentou executar`, `Qual foi o erro`, `Possível problema`, `Possível solução` e `Retomada`.
- Ajustada a descrição da etapa `XD03` para explicar que ela busca o cliente, captura o nome e valida o setor de atividade.
- Adicionada classificação de causas comuns, como SAP sem sessão logada, SAP GUI Scripting, cliente não encontrado, setor ausente, tela/popup inesperado, doc.fat ausente, BOL ocupada, SP02/spool e modal de cópia não confirmado.
- Mantida a proteção de mascaramento de CPF/CNPJ nos logs públicos.
- Atualizada a versão do projeto de `1.4.3` para `1.4.4`.

**Arquivos alterados**

- `backend/controller.py`
- `backend/settings.py`
- `interface/app.js`
- `interface/index.html`
- `embasa_settings.json`
- `VERSAO.txt`
- `LEIA-ME_EMPRESA.txt`
- `CHANGELOG_TECNICO.md`

**Resultado esperado**

Ao ocorrer falha, o usuário deve abrir os logs e ver uma mensagem curta, em tópicos, suficiente para entender o que o sistema tentou fazer, por que parou e qual ação tomar.

**Validação realizada**

- `python -m py_compile backend\controller.py interface.py backend\settings.py`
- `node --check interface\app.js`
- Teste isolado de falha em `XD03` simulando sessão SAP ausente.
- Rebuild com `powershell -ExecutionPolicy Bypass -File .\build_empresarial.ps1`.

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
