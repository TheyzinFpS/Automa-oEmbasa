# EMBASA App Organizado

Estrutura unificada criada a partir de:
- `programando-completo-2026-04-13.zip` -> base principal do app (front + backend mock/orquestração)
- `Automação.zip` -> automação SAP real ainda não integrada

## O que está pronto nesta pasta
- Front-end preservado em `interface/`
- API pywebview preservada em `interface.py`
- Orquestrador atual preservado em `backend/controller.py`
- Fluxos mock atuais preservados em `backend/flows/`
- Automação SAP extraída e separada em `sap_real/`

## Importante
Esta pasta está ORGANIZADA, mas não totalmente INTEGRADA.
Os arquivos em `sap_real/` ainda precisam ser adaptados para substituir os mocks de `backend/flows/`.

## Sugestão de integração
- `backend/flows/xd03.py` <-> `sap_real/buscar_cliente_final.py`
- `backend/flows/va01.py` <-> `sap_real/criar_pedido.py`
- `backend/flows/vf01.py` <-> `sap_real/criar_doc_faturamento.py`
- `backend/flows/vf02.py` <-> `sap_real/pos_faturamento.py`
- `backend/flows/f110.py` <-> `sap_real/f110.py`

## Limpeza feita
- `.venv` removido
- `__pycache__` removido
- arquivos empacotados/temporários não incluídos

## Próximo passo recomendado
Criar adaptadores em `backend/flows/` que chamem `sap_real/` e padronizar assinatura das funções para usar `session`, `dados` e `logger`.
