from buscar_cliente_final import buscar_cliente_final
from criar_pedido import criar_pedido
from criar_doc_faturamento import criar_doc_faturamento
from pos_faturamento import pos_faturamento
from f110 import f110

try:
    import win32com.client # type: ignore
except ImportError:
    raise ImportError("Instale o pacote 'pywin32' com: pip install pywin32")


# =========================
# CONEXÃO SAP (ÚNICA)
# =========================
SapGuiAuto = win32com.client.GetObject("SAPGUI")
application = SapGuiAuto.GetScriptingEngine
connection = application.Children(0)
session = connection.Children(0)


# =========================
# INPUTS
# =========================
doc   = input("CPF/CNPJ: ").strip()
tipo  = input("Tipo (viabilidade/agua/esgoto): ").strip().lower()
valor = input("Valor: ").strip()

if tipo not in ["viabilidade", "agua", "esgoto"]:
    raise ValueError(f"Tipo inválido: {tipo}. Use viabilidade, agua ou esgoto.")

entrada = input("\nDigite: nome,rua,numero,bairro,cidade,cep\n").strip()
partes  = [p.strip() for p in entrada.split(",")]

if len(partes) != 6:
    raise ValueError("Formato inválido. Informe: nome,rua,numero,bairro,cidade,cep")

dados = {
    "nome":    partes[0],
    "rua":     partes[1],
    "numero":  partes[2],
    "bairro":  partes[3],
    "cidade":  partes[4],
    "cep":     partes[5]
}


# =========================
# FLUXO PRINCIPAL
# =========================
try:
    # 1. Buscar cliente
    cliente = buscar_cliente_final(session, doc)

    if cliente is None:
        print("⚠️ CPF/CNPJ não cadastrado. Inicie o processo de cadastro manualmente.")
    else:
        # 2. Criar pedido
        # criar_pedido(session, cliente, tipo, valor, dados)

        # 3. Criar documento de faturamento
        # criar_doc_faturamento(session, ...)

        # 4. Pós-faturamento
        # pos_faturamento(session, ...)

        # 5. Pagamento automático
        # f110(session, ...)

        print("\n✅ PROCESSO FINALIZADO COM SUCESSO!")

except Exception as e:
    print(f"\n❌ ERRO NO PROCESSO: {e}")
    try:
        session.findById("wnd[0]").sendVKey(15)
    except Exception:
        pass