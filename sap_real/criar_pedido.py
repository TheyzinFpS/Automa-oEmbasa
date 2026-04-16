import time
from datetime import datetime
import re


# =========================
# ESPERA INTELIGENTE
# =========================
def wait_for_element(session, element_id, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            return session.findById(element_id)
        except:
            time.sleep(0.2)
    raise Exception(f"Elemento não encontrado: {element_id}")


# =========================
# TEXTO
# =========================
def montar_texto(tipo, dados):
    modelos = {
        "viabilidade": "Referente à solicitação de ANÁLISE DE VIABILIDADE TÉCNICA para fornecimento de Água e Esgotamento Sanitário, no EMPREENDIMENTO {nome}, localizado na {rua}, {numero}, {bairro}, {cidade}-BA, CEP: {cep}.",
        "agua": "Referente à solicitação de APROVAÇÃO DE PROJETO DE ABASTECIMENTO DE ÁGUA, no EMPREENDIMENTO {nome}, localizado na {rua}, {numero}, {bairro}, {cidade}-BA, CEP: {cep}.",
        "esgoto": "Referente à solicitação de APROVAÇÃO DE PROJETO DE ESGOTAMENTO SANITÁRIO, no EMPREENDIMENTO {nome}, localizado na {rua}, {numero}, {bairro}, {cidade}-BA, CEP: {cep}."
    }
    return modelos[tipo].format(**dados)


# =========================
# FUNÇÃO PRINCIPAL
# =========================
def criar_pedido(session, cliente, tipo_pedido, valor):

    data_hoje = datetime.now().strftime("%d%m%Y")

    materiais = {
        "viabilidade": "900000000032",
        "agua": "900000000017",
        "esgoto": "900000000018"
    }

    material = materiais.get(tipo_pedido)

    centro_lucro = "030002010L" if tipo_pedido in ["viabilidade", "agua"] else "072002000L"

    if tipo_pedido == "viabilidade":
        auart, spart, vkbur, vkgrp = "ZEST", "AE", "1055", "DM"
    elif tipo_pedido == "agua":
        auart, spart, vkbur, vkgrp = "ZPRO", "AG", "1055", "DM"
    else:
        auart, spart, vkbur, vkgrp = "ZPRO", "EG", "1070", "ME"

    # =========================
    # INPUT
    # =========================
    entrada = input("\nDigite: nome,rua,numero,bairro,cidade,cep\n")
    partes = [p.strip() for p in entrada.split(",")]

    if len(partes) != 6:
        raise ValueError("Formato inválido.")

    dados = {
        "nome": partes[0],
        "rua": partes[1],
        "numero": partes[2],
        "bairro": partes[3],
        "cidade": partes[4],
        "cep": partes[5]
    }

    if not re.match(r"^\d{5}-\d{3}$", dados["cep"]):
        raise ValueError("CEP inválido.")

    texto = montar_texto(tipo_pedido, dados)

    # =========================
    # VA01
    # =========================
    session.findById("wnd[0]/tbar[0]/okcd").text = "/nVA01"
    session.findById("wnd[0]").sendVKey(0)

    wait_for_element(session, "wnd[0]/usr/ctxtVBAK-AUART")

    # Cabeçalho
    session.findById("wnd[0]/usr/ctxtVBAK-AUART").text = auart
    session.findById("wnd[0]/usr/ctxtVBAK-VKORG").text = "EMBA"
    session.findById("wnd[0]/usr/ctxtVBAK-VTWEG").text = "PO"
    session.findById("wnd[0]/usr/ctxtVBAK-SPART").text = spart
    session.findById("wnd[0]/usr/ctxtVBAK-VKBUR").text = vkbur
    session.findById("wnd[0]/usr/ctxtVBAK-VKGRP").text = vkgrp

    session.findById("wnd[0]").sendVKey(0)

    # =========================
    # CLIENTE
    # =========================
    wait_for_element(
        session,
        "wnd[0]/usr/subSUBSCREEN_HEADER:SAPMV45A:4021/subPART-SUB:SAPMV45A:4701/ctxtKUAGV-KUNNR"
    )

    session.findById("wnd[0]/usr/subSUBSCREEN_HEADER:SAPMV45A:4021/subPART-SUB:SAPMV45A:4701/ctxtKUAGV-KUNNR").text = cliente
    session.findById("wnd[0]/usr/subSUBSCREEN_HEADER:SAPMV45A:4021/subPART-SUB:SAPMV45A:4701/ctxtKUWEV-KUNNR").text = cliente
    session.findById("wnd[0]/usr/subSUBSCREEN_HEADER:SAPMV45A:4021/ctxtVBKD-BSTDK").text = data_hoje

    session.findById("wnd[0]").sendVKey(0)

    # =========================
    # CAMPOS OBRIGATÓRIOS
    # =========================
    session.findById("wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01").select()

    session.findById(
        "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/"
        "ssubSUBSCREEN_BODY:SAPMV45A:4400/"
        "ssubHEADER_FRAME:SAPMV45A:4440/ctxtRV45A-DWERK"
    ).text = "CAB"

    session.findById(
        "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/"
        "ssubSUBSCREEN_BODY:SAPMV45A:4400/"
        "ssubHEADER_FRAME:SAPMV45A:4440/ctxtVBKD-ZTERM"
    ).text = "C060"

    session.findById("wnd[0]").sendVKey(0)

    # =========================
    # MATERIAL
    # =========================
    campo_material = wait_for_element(
        session,
        "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/"
        "ssubSUBSCREEN_BODY:SAPMV45A:4400/subSUBSCREEN_TC:SAPMV45A:4900/"
        "tblSAPMV45ATCTRL_U_ERF_AUFTRAG/ctxtRV45A-MABNR[1,0]"
    )

    campo_material.text = material
    session.findById("wnd[0]").sendVKey(0)

    # Quantidade
    session.findById(
        "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/"
        "ssubSUBSCREEN_BODY:SAPMV45A:4400/subSUBSCREEN_TC:SAPMV45A:4900/"
        "tblSAPMV45ATCTRL_U_ERF_AUFTRAG/txtRV45A-KWMENG[2,0]"
    ).text = "1"

    session.findById("wnd[0]").sendVKey(0)

    # Centro de lucro
    campo_prctr = wait_for_element(
        session,
        "wnd[0]/usr/tabsTAXI_TABSTRIP_OVERVIEW/tabpT\\01/"
        "ssubSUBSCREEN_BODY:SAPMV45A:4400/subSUBSCREEN_TC:SAPMV45A:4900/"
        "tblSAPMV45ATCTRL_U_ERF_AUFTRAG/ctxtVBAP-PRCTR[53,0]"
    )

    campo_prctr.text = centro_lucro
    session.findById("wnd[0]").sendVKey(0)
    time.sleep(1)

    # =========================
    # ENTRAR NO ITEM
    # =========================
    
    session.findById("wnd[0]").sendVKey(2)

    # =========================
    # TEXTO
    # =========================
    wait_for_element(session, "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\10").select()

    campo_texto = wait_for_element(
        session,
        "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\10/"
        "ssubSUBSCREEN_BODY:SAPMV45A:4152/subSUBSCREEN_TEXT:SAPLV70T:2100/"
        "cntlSPLITTER_CONTAINER/shellcont/shellcont/shell/shellcont[1]/shell"
    )

    campo_texto.text = texto + "\n"

    # =========================
    # CONDIÇÕES
    # =========================
    session.findById("wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\06").select()

    session.findById(
        "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\06/"
        "ssubSUBSCREEN_BODY:SAPLV69A:6201/subSUBSCREEN_PUSHBUTTONS:SAPLV69A:1000/btnBT_KOAN"
    ).press()

    wait_for_element(
        session,
        "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\06/"
        "ssubSUBSCREEN_BODY:SAPLV69A:6201/tblSAPLV69ATCTRL_KONDITIONEN"
    )

    session.findById(
        "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\06/"
        "ssubSUBSCREEN_BODY:SAPLV69A:6201/tblSAPLV69ATCTRL_KONDITIONEN/ctxtKOMV-KSCHL[1,1]"
    ).text = "PR00"

    session.findById(
        "wnd[0]/usr/tabsTAXI_TABSTRIP_ITEM/tabpT\\06/"
        "ssubSUBSCREEN_BODY:SAPLV69A:6201/tblSAPLV69ATCTRL_KONDITIONEN/txtKOMV-KBETR[3,1]"
    ).text = valor

    # SALVAR
    session.findById("wnd[0]").sendVKey(11)

    # SAIR
    try:
        session.findById("wnd[0]").sendVKey(12)
        session.findById("wnd[0]").sendVKey(12)
    except:
        pass

    print("Ordem-cliente criada")