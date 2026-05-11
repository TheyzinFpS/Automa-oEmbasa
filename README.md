# Embasa Pedidos SAP

Sistema desktop em Python + pywebview para automação assistida de pedidos, faturamento e geração de boleto no SAP GUI.

## Escopo atual

- Interface desktop HTML/CSS/JS embarcada no pywebview.
- Integração com SAP GUI Scripting.
- Fluxo operacional: XD03, VA01, VF01, FB03, VF02 e F110.
- Progresso em tempo real na interface.
- Cancelamento seguro do fluxo.
- Validação de CPF/CNPJ, tipo de solicitação, valores e dados do empreendimento.
- Autopreenchimento de endereço por CEP.
- Build empresarial em modo `onedir` para uso em pasta de rede.

## Requisitos de execução

- SAP GUI instalado e com scripting habilitado.
- Microsoft Edge WebView2 Runtime.
- .NET Desktop Runtime.
- Para desenvolvimento/build: Python 3.11.

## Build empresarial

No computador de manutenção:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_empresarial.ps1
```

Para publicar na pasta de rede padrão:

```powershell
powershell -ExecutionPolicy Bypass -File .\publicar_rede.ps1
```

O usuário final deve abrir o executável publicado na rede:

```text
EmbasaPedidosSAP.exe
```

Não copie apenas o `.exe`; o build é `onedir` e depende da pasta `_internal`.

## Observação

Os computadores dos usuários finais não precisam de Python, VS Code ou Git. Esses itens são necessários apenas para manutenção e geração de novas versões.
