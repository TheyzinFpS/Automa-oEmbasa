# Notas de integração

## Situação atual
- `backend/controller.py` ainda usa `session = "fake_session"`
- `backend/flows/*.py` retornam valores simulados
- `sap_real/` contém scripts de automação SAP reais, mas em formato ainda manual/isolado

## Ajustes necessários antes de integrar
1. Extrair a conexão SAP de `sap_real/mainback.py` para um módulo próprio, ex.: `sap_real/conexao.py`
2. Remover `input()` dos scripts SAP e passar tudo por parâmetros
3. Padronizar nomes das funções e retornos
4. Corrigir e revisar `sap_real/pos_faturamento.py`, que aparenta estar incompleto e possivelmente com erro de indentação/sintaxe
5. Fazer `backend/controller.py` abrir a sessão real e repassar para os fluxos

## Assinatura alvo sugerida
- `buscar_cliente(session, dados, logger) -> str | None`
- `criar_pedido(session, dados, codigo_cliente, logger) -> str`
- `criar_doc_faturamento(session, pedido, logger) -> str`
- `pos_faturamento(session, faturamento, logger) -> str`
- `f110(session, doc_fat, dados, logger) -> dict`
