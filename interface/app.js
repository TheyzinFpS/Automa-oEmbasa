const ETAPAS = [
  { id: "XD03", codigo: "XD03", titulo: "Buscar cliente" },
  { id: "VA01", codigo: "VA01", titulo: "Criar ordem-cliente" },
  { id: "VF01", codigo: "VF01", titulo: "Criar Doc.faturamento" },
  { id: "VF02_CAPTURA", codigo: "VF02", titulo: "Capturar Doc.Faturamento" },
  { id: "FB03", codigo: "FB03", titulo: "Ajustar contabil" },
  { id: "VF02_RESALVAR", codigo: "VF02", titulo: "Salvar faturamento" },
  { id: "F110", codigo: "F110", titulo: "Criacao Pagamento" }
];

const VALORES = {
  viabilidade: "R$ 1.038,02",
  agua: "R$ 2.357,70",
  esgoto: "R$ 2.357,70"
};

const TIPOS_SOLICITACAO = {
  "": "Selecione",
  viabilidade: "Viabilidade",
  agua: "\u00c1gua",
  esgoto: "Esgoto"
};

const BASE_STATUS = {
  active: {
    text: "✓ ATIVO",
    subtext: "Ambiente apto para operacao e testes.",
    cardClass: "status-active"
  },
  maintenance: {
    text: "Em manutencao",
    subtext: "Ambiente com ajustes em andamento.",
    cardClass: "status-maintenance"
  }
};

const MAX_VALOR_CENTAVOS = 1000000;
const THEME_STORAGE_KEY = "embasa-theme";
const ETAPA_ID_INDEX_MAP = new Map(ETAPAS.map((etapa, index) => [etapa.id, index]));
const STATUS_ATIVOS = new Set([
  "processando", "processing", "running", "ativo", "active", "iniciando", "iniciado"
]);
const STATUS_CONCLUIDOS = new Set([
  "concluido", "concluida", "done", "success", "sucesso", "finalizado", "finalizada"
]);
const STATUS_ERRO = new Set(["erro", "error", "falha", "failed"]);
const EMPTY_LOG_MARKUP = '<div class="log-empty">Os logs do fluxo aparecerao aqui.</div>';

const state = {
  valueMode: "auto",
  theme: "light",
  lastTipo: "",
  logCount: 0,
  baseStatus: "active",
  empreendimentoAberto: false,
  semNumero: false,
  etapaAtual: null,
  etapasStatus: [],
  etapasProgresso: [],
  etapasMensagens: [],
  resumeCheckpoint: null,
  etapasConstruidas: false,
  footerDateText: "",
  footerTimeText: "",
  statusSnapshot: ""
};

const domCache = new Map();
const ETAPA_NODE_CACHE = [];

function el(id) {
  if (domCache.has(id)) {
    return domCache.get(id);
  }

  const node = document.getElementById(id);

  if (node) {
    domCache.set(id, node);
  }

  return node;
}

const VALIDATION_FIELDS = {
  doc: { messageId: "docError" },
  tipo: { messageId: "tipoError", focusId: "tipoButton" },
  valor: { messageId: "valorError" },
  enderecoEmpreendimento: { messageId: "enderecoEmpreendimentoError", accordion: true },
  enderecoRua: { messageId: "enderecoRuaError", accordion: true },
  enderecoNumero: { messageId: "enderecoNumeroError", accordion: true },
  enderecoCep: { messageId: "enderecoCepError", accordion: true },
  enderecoBairro: { messageId: "enderecoBairroError", accordion: true },
  enderecoCidade: { messageId: "enderecoCidadeError", accordion: true }
};

function clampPercent(value) {
  const numero = Number(value);

  if (!Number.isFinite(numero)) {
    return null;
  }

  return Math.max(0, Math.min(100, Math.round(numero)));
}

function limparDocumento(valor) {
  return String(valor || "").replace(/\D/g, "").slice(0, 14);
}

function formatarDocumento(valor) {
  const digitos = limparDocumento(valor);

  if (digitos.length <= 11) {
    if (digitos.length <= 3) return digitos;
    if (digitos.length <= 6) return `${digitos.slice(0, 3)}.${digitos.slice(3)}`;
    if (digitos.length <= 9) {
      return `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6)}`;
    }

    return `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6, 9)}-${digitos.slice(9, 11)}`;
  }

  if (digitos.length <= 2) return digitos;
  if (digitos.length <= 5) return `${digitos.slice(0, 2)}.${digitos.slice(2)}`;
  if (digitos.length <= 8) {
    return `${digitos.slice(0, 2)}.${digitos.slice(2, 5)}.${digitos.slice(5)}`;
  }
  if (digitos.length <= 12) {
    return `${digitos.slice(0, 2)}.${digitos.slice(2, 5)}.${digitos.slice(5, 8)}/${digitos.slice(8)}`;
  }

  return `${digitos.slice(0, 2)}.${digitos.slice(2, 5)}.${digitos.slice(5, 8)}/${digitos.slice(8, 12)}-${digitos.slice(12, 14)}`;
}

function analisarDocumento(valor) {
  const digitos = limparDocumento(valor);

  if (!digitos.length) {
    return {
      digitos,
      formatado: "",
      badge: "CPF/CNPJ",
      hint: "Digite 11 digitos para CPF ou 14 para CNPJ.",
      contador: "0 de 11 digitos",
      classe: "neutral"
    };
  }

  if (digitos.length <= 11) {
    const faltam = Math.max(0, 11 - digitos.length);
    const completo = digitos.length === 11;

    return {
      digitos,
      formatado: formatarDocumento(digitos),
      badge: completo ? "CPF valido" : "CPF",
      hint: completo ? "CPF completo e pronto para envio ao SAP." : `CPF em preenchimento. Faltam ${faltam} digitos.`,
      contador: `${digitos.length} de 11 digitos`,
      classe: completo ? "valid" : "progress"
    };
  }

  const faltam = Math.max(0, 14 - digitos.length);
  const completo = digitos.length === 14;

  return {
    digitos,
    formatado: formatarDocumento(digitos),
    badge: completo ? "CNPJ valido" : "CNPJ",
    hint: completo ? "CNPJ completo e pronto para envio ao SAP." : `CNPJ em preenchimento. Faltam ${faltam} digitos.`,
    contador: `${digitos.length} de 14 digitos`,
    classe: completo ? "valid" : "progress"
  };
}

function limparValor(valor) {
  return String(valor || "").replace(/\D/g, "");
}

function formatarCepValue(valor) {
  const digitos = String(valor || "").replace(/\D/g, "").slice(0, 8);

  if (digitos.length <= 5) {
    return digitos;
  }

  return `${digitos.slice(0, 5)}-${digitos.slice(5)}`;
}

function sanitizarCidade(valor) {
  return String(valor || "")
    .replace(/[^A-Za-zÀ-ÿ\s'-]/g, "")
    .replace(/\s{2,}/g, " ");
}

function formatarCep(el) {
  el.value = formatarCepValue(el.value);
  limparMensagemCampo("enderecoCep");
}

function formatarCentavosParaMoeda(centavos) {
  const valor = centavos / 100;

  return valor.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL"
  });
}

function formatarValorDigitado(valor) {
  const digitos = limparValor(valor);

  if (!digitos) {
    return "";
  }

  const centavos = Math.min(Number(digitos), MAX_VALOR_CENTAVOS);
  return formatarCentavosParaMoeda(centavos);
}

function carregarTemaSalvo() {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY);
  } catch (error) {
    return null;
  }
}

function salvarTema(theme) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch (error) {
    // ignora falhas de persistencia
  }
}

function atualizarLogoPorTema() {
  const logo = el("brandLogo");

  if (!logo) {
    return;
  }

  logo.classList.remove("logo-animated");

  window.requestAnimationFrame(() => {
    logo.classList.add("logo-animated");
  });
}

function setMenuOpen(menuId, buttonId, aberto) {
  const menu = el(menuId);
  const button = el(buttonId);

  if (!menu || !button) {
    return;
  }

  menu.classList.toggle("hidden", !aberto);
  button.classList.toggle("open", aberto);
  button.setAttribute("aria-expanded", String(aberto));
}

function closeMenu(menuId, buttonId) {
  setMenuOpen(menuId, buttonId, false);
}

function toggleMenu(menuId, buttonId, event) {
  if (event) {
    event.stopPropagation();
  }

  const menu = el(menuId);

  if (!menu) {
    return;
  }

  setMenuOpen(menuId, buttonId, menu.classList.contains("hidden"));
}

function atualizarEscalaLogo() {
  const frame = document.documentElement;
  const larguraViewport = window.innerWidth || 1280;
  const densidade = window.devicePixelRatio || 1;
  const largura = Math.min(720, Math.max(360, Math.round(larguraViewport * 0.4 * Math.min(densidade, 1.4))));
  const altura = Math.round(largura * 0.34);

  frame.style.setProperty("--brand-logo-width", `${largura}px`);
  frame.style.setProperty("--brand-logo-height", `${altura}px`);
}

function setEmpreendimentoAberto(aberto) {
  state.empreendimentoAberto = aberto;

  const shell = el("empreendimentoContent");
  const toggle = el("empreendimentoToggle");

  shell.classList.toggle("collapsed", !aberto);
  toggle.classList.toggle("open", aberto);
  toggle.setAttribute("aria-expanded", String(aberto));
}

function toggleEmpreendimento() {
  setEmpreendimentoAberto(!state.empreendimentoAberto);
}

function setSemNumero(ativo) {
  state.semNumero = ativo;

  const input = el("enderecoNumero");
  const button = el("semNumeroButton");

  button.classList.toggle("active", ativo);
  input.readOnly = ativo;
  input.classList.toggle("readonly-like", ativo);
  input.value = ativo ? "S/N" : "";
  input.placeholder = ativo ? "Sem numero" : "Informe o numero";
  limparMensagemCampo("enderecoNumero");
}

function toggleSemNumero() {
  setSemNumero(!state.semNumero);
}

function coletarEndereco() {
  return {
    empreendimento: el("enderecoEmpreendimento").value.trim(),
    rua: el("enderecoRua").value.trim(),
    numero: state.semNumero
      ? "S/N"
      : el("enderecoNumero").value.trim(),
    cep: formatarCepValue(el("enderecoCep").value.trim()),
    bairro: el("enderecoBairro").value.trim(),
    complemento: el("enderecoComplemento").value.trim(),
    cidade: sanitizarCidade(el("enderecoCidade").value.trim()),
    estado: "BA"
  };
}

function limparMensagemCampo(fieldId) {
  const config = VALIDATION_FIELDS[fieldId];
  const baseElement = el(fieldId);
  const focusTarget = el(config?.focusId || fieldId) || baseElement;
  const field = focusTarget ? focusTarget.closest(".field") : null;
  const message = config ? el(config.messageId) : null;

  if (field) {
    field.classList.remove("has-error");
  }

  if (message) {
    message.textContent = "";
    message.classList.add("hidden");
  }
}

function limparMensagensValidacao() {
  Object.keys(VALIDATION_FIELDS).forEach(limparMensagemCampo);
}

function mostrarErroCampo(fieldId, message) {
  const config = VALIDATION_FIELDS[fieldId];
  const baseElement = el(fieldId);
  const focusTarget = el(config?.focusId || fieldId) || baseElement;
  const field = focusTarget ? focusTarget.closest(".field") : null;
  const messageEl = config ? el(config.messageId) : null;

  limparMensagensValidacao();

  if (config && config.accordion) {
    setEmpreendimentoAberto(true);
  }

  if (field) {
    field.classList.add("has-error");
  }

  if (messageEl) {
    messageEl.textContent = message;
    messageEl.classList.remove("hidden");
  }

  if (focusTarget) {
    focusTarget.scrollIntoView({ behavior: "smooth", block: "center" });

    if (typeof focusTarget.focus === "function") {
      window.setTimeout(() => focusTarget.focus(), 160);
    }
  }

  setStatus("Atencao", "error");
  setStatus("Aguardando", "idle");
  closeLogsPopover();
}

function valorFoiInformado() {
  const valor = limparValor(el("valor").value);
  return Boolean(valor) && Number(valor) > 0;
}

function validarFormularioAntesDoFluxo() {
  const docInfo = analisarDocumento(el("doc").value);
  const tipo = el("tipo").value;
  const endereco = coletarEndereco();
  const cepLimpo = String(endereco.cep || "").replace(/\D/g, "");

  if (!docInfo.digitos) {
    mostrarErroCampo("doc", "CPF/CNPJ obrigat\u00f3rio.");
    return null;
  }

  if (![11, 14].includes(docInfo.digitos.length)) {
    mostrarErroCampo("doc", "Informe um CPF com 11 d\u00edgitos ou um CNPJ com 14 d\u00edgitos para prosseguir.");
    return null;
  }

  if (!tipo) {
    mostrarErroCampo("tipo", "Selecione o tipo de solicita\u00e7\u00e3o. Esta \u00e9 a pr\u00f3xima etapa obrigat\u00f3ria.");
    return null;
  }

  if (!valorFoiInformado()) {
    mostrarErroCampo("valor", "Informe o valor da solicita\u00e7\u00e3o. Esta \u00e9 a pr\u00f3xima etapa obrigat\u00f3ria.");
    return null;
  }

  if (!endereco.empreendimento) {
    mostrarErroCampo("enderecoEmpreendimento", "Informe o empreendimento. Esta \u00e9 a pr\u00f3xima etapa obrigat\u00f3ria.");
    return null;
  }

  if (!endereco.rua) {
    mostrarErroCampo("enderecoRua", "Informe a rua do empreendimento para prosseguir.");
    return null;
  }

  if (!state.semNumero && !endereco.numero) {
    mostrarErroCampo("enderecoNumero", "Informe o n\u00famero do endere\u00e7o ou marque S/N para prosseguir.");
    return null;
  }

  if (!cepLimpo) {
    mostrarErroCampo("enderecoCep", "Informe o CEP do empreendimento. Esta \u00e9 a pr\u00f3xima etapa obrigat\u00f3ria.");
    return null;
  }

  if (cepLimpo.length !== 8) {
    mostrarErroCampo("enderecoCep", "Informe um CEP v\u00e1lido com 8 d\u00edgitos para prosseguir.");
    return null;
  }

  if (!endereco.bairro) {
    mostrarErroCampo("enderecoBairro", "Informe o bairro do empreendimento para prosseguir.");
    return null;
  }

  if (!endereco.cidade) {
    mostrarErroCampo("enderecoCidade", "Informe a cidade do empreendimento para prosseguir.");
    return null;
  }

  if (/[^A-Za-zÀ-ÿ\s'-]/.test(endereco.cidade)) {
    mostrarErroCampo("enderecoCidade", "A cidade deve conter apenas letras.");
    return null;
  }

  limparMensagensValidacao();

  return {
    docInfo,
    endereco
  };
}

function aplicarTema(theme) {
  state.theme = theme;
  document.documentElement.dataset.theme = theme;

  const label = el("themeLabel");
  const icon = el("themeIcon");
  const button = el("themeToggle");
  const proximo = theme === "dark" ? "Modo claro" : "Modo escuro";

  label.textContent = proximo;
  icon.textContent = theme === "dark" ? "CL" : "ES";
  button.setAttribute("aria-label", `Ativar ${proximo.toLowerCase()}`);

  atualizarLogoPorTema(theme);
}

function inicializarTema() {
  const temaSalvo = carregarTemaSalvo();
  const temaSistema = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";

  aplicarTema(temaSalvo || temaSistema);
}

function toggleTheme() {
  const proximo = state.theme === "dark" ? "light" : "dark";
  aplicarTema(proximo);
  salvarTema(proximo);
}

function setBaseStatus(status) {
  if (!BASE_STATUS[status]) {
    return;
  }

  state.baseStatus = status;

  const config = BASE_STATUS[status];
  const card = el("baseStatusCard");
  const text = el("baseStatusText");
  const sub = el("baseStatusSub");
  const buttonText = el("baseStatusButtonText");
  const activeOption = el("baseStatusOptionActive");
  const maintenanceOption = el("baseStatusOptionMaintenance");

  card.classList.remove("status-active", "status-maintenance");
  card.classList.add(config.cardClass);
  text.textContent = config.text;
  sub.textContent = config.subtext;
  buttonText.textContent = status === "active" ? "Sistema ativo" : "Sistema em manutencao";

  activeOption.classList.toggle("selected", status === "active");
  maintenanceOption.classList.toggle("selected", status === "maintenance");
}

function openBaseStatusMenu() {
  setMenuOpen("baseStatusMenu", "baseStatusButton", true);
}

function closeBaseStatusMenu() {
  closeMenu("baseStatusMenu", "baseStatusButton");
}

function toggleBaseStatusMenu(event) {
  toggleMenu("baseStatusMenu", "baseStatusButton", event);
}

function selectBaseStatus(status) {
  setBaseStatus(status);
  closeBaseStatusMenu();
}

function setStatus(texto, classe) {
  const nextSnapshot = `${classe}::${texto}`;

  if (state.statusSnapshot === nextSnapshot) {
    return;
  }

  state.statusSnapshot = nextSnapshot;
  const pill = el("statusPill");
  pill.textContent = texto;
  pill.className = `status-pill ${classe}`;
}

function atualizarDocumentoUI(valorAtual) {
  const input = el("doc");
  const badge = el("docBadge");
  const hint = el("docHint");
  const counter = el("digitCounter");
  const info = analisarDocumento(valorAtual);

  input.value = info.formatado;
  badge.textContent = info.badge;
  badge.className = `doc-badge ${info.classe}`;
  hint.textContent = info.hint;
  counter.textContent = info.contador;
}

function formatarDoc(el) {
  limparMensagemCampo("doc");
  atualizarDocumentoUI(el.value);
}

function atualizarTipo() {
  const tipo = el("tipo").value;
  const tipoMudou = Boolean(state.lastTipo) && state.lastTipo !== tipo;
  const tipoButtonText = el("tipoButtonText");

  limparMensagemCampo("tipo");
  limparMensagemCampo("valor");

  tipoButtonText.textContent = TIPOS_SOLICITACAO[tipo] || TIPOS_SOLICITACAO[""];

  if (state.valueMode === "custom" && tipoMudou) {
    state.valueMode = "auto";
    atualizarModoValorUI();
  }

  if (state.valueMode === "auto") {
    el("valor").value = VALORES[tipo] || "";
  }

  state.lastTipo = tipo;
}

function abrirMenuTipo() {
  setMenuOpen("tipoMenu", "tipoButton", true);
}

function fecharMenuTipo() {
  closeMenu("tipoMenu", "tipoButton");
}

function toggleTipoMenu(event) {
  toggleMenu("tipoMenu", "tipoButton", event);
}

function selecionarTipo(tipo, label) {
  el("tipo").value = tipo;
  el("tipoButtonText").textContent = label;
  fecharMenuTipo();
  atualizarTipo();
}

function atualizarModoValorUI() {
  const input = el("valor");
  const hint = el("valorHint");
  const chip = el("valueModeCurrent");

  if (state.valueMode === "custom") {
    input.readOnly = false;
    input.classList.add("editable");
    chip.textContent = "Valor customizado";
    hint.textContent = "Digite um valor customizado com limite de R$ 10.000,00.";

    if (!input.value) {
      const tipoAtual = el("tipo").value;
      input.value = VALORES[tipoAtual] || "";
    }
  } else {
    input.readOnly = true;
    input.classList.remove("editable");
    chip.textContent = "Valor da tabela";
    hint.textContent = "Valor definido automaticamente pelo tipo selecionado.";
    input.value = VALORES[el("tipo").value] || "";
  }
}

function abrirMenuValor() {
  setMenuOpen("valueMenu", "valueModeButton", true);
}

function fecharMenuValor() {
  closeMenu("valueMenu", "valueModeButton");
}

function toggleValueMenu(event) {
  toggleMenu("valueMenu", "valueModeButton", event);
}

function selecionarModoValor(mode) {
  state.valueMode = mode;
  atualizarModoValorUI();
  limparMensagemCampo("valor");
  fecharMenuValor();

  const input = el("valor");
  input.focus();
  input.setSelectionRange(input.value.length, input.value.length);
}

function handleValorInput(event) {
  if (state.valueMode !== "custom") {
    return;
  }

  const input = event.target;
  input.value = formatarValorDigitado(input.value);
  limparMensagemCampo("valor");
}

function filtrarCidade(input) {
  const valorSanitizado = sanitizarCidade(input.value);

  if (input.value !== valorSanitizado) {
    input.value = valorSanitizado;
  }

  limparMensagemCampo("enderecoCidade");
}

function registrarValidacaoInterativa() {
  [
    ["enderecoEmpreendimento", "input"],
    ["enderecoRua", "input"],
    ["enderecoNumero", "input"],
    ["enderecoBairro", "input"],
    ["enderecoCidade", "input"]
  ].forEach(([fieldId, eventName]) => {
    const element = el(fieldId);

    if (!element) {
      return;
    }

    element.addEventListener(eventName, () => {
      if (fieldId === "enderecoCidade") {
        filtrarCidade(element);
        return;
      }

      limparMensagemCampo(fieldId);
    });
  });
}

function updateLogCount() {
  const counter = el("logCount");
  const nextValue = String(state.logCount);

  if (counter.textContent !== nextValue) {
    counter.textContent = nextValue;
  }
}

function renderLogEmptyState() {
  const box = el("logBox");

  if (state.logCount === 0 && box.innerHTML === EMPTY_LOG_MARKUP) {
    return;
  }

  box.innerHTML = EMPTY_LOG_MARKUP;
}

function getEtapaIndexById(idOuCodigo) {
  const chave = String(idOuCodigo || "").trim().toUpperCase();

  if (!chave) {
    return -1;
  }

  if (ETAPA_ID_INDEX_MAP.has(chave)) {
    return ETAPA_ID_INDEX_MAP.get(chave);
  }

  return ETAPAS.findIndex((etapa) => etapa.codigo === chave);
}

function getEtapaDescricao(status, mensagem) {
  if (mensagem) {
    return mensagem;
  }

  if (status === "active") return "Em processamento";
  if (status === "done") return "Concluido";
  if (status === "error") return "Falha na etapa";
  return "Aguardando execucao";
}

function normalizarStatusTempoReal(status) {
  const valor = String(status || "").trim().toLowerCase();

  if (STATUS_ATIVOS.has(valor)) {
    return "active";
  }

  if (STATUS_CONCLUIDOS.has(valor)) {
    return "done";
  }

  if (STATUS_ERRO.has(valor)) {
    return "error";
  }

  return "pending";
}

window.resetarProgresso = function resetarProgresso() {
  limparPainel();
};

window.atualizarProgresso = function atualizarProgresso(payloadOrEtapa, status, mensagem = "", percentual = null) {
  processarEtapaTempoReal(payloadOrEtapa, status, mensagem, percentual);
};

function resetarEtapas() {
  state.etapaAtual = null;
  state.etapasStatus = ETAPAS.map(() => "pending");
  state.etapasProgresso = ETAPAS.map(() => 0);
  state.etapasMensagens = ETAPAS.map(() => "");

  ETAPAS.forEach((_, index) => {
    setEtapa(index, "pending", 0, "");
  });
}

function ativarEtapa(index, percentual = null, mensagem = "") {
  if (!Number.isInteger(index) || index < 0 || index >= ETAPAS.length) {
    return;
  }

  state.etapaAtual = index;
  setEtapa(index, "active", percentual, mensagem);
}

function concluirEtapa(index, mensagem = "") {
  if (!Number.isInteger(index) || index < 0 || index >= ETAPAS.length) {
    return;
  }

  state.etapaAtual = index;
  setEtapa(index, "done", 100, mensagem);
}

function falharEtapa(index, mensagem = "") {
  if (!Number.isInteger(index) || index < 0 || index >= ETAPAS.length) {
    return;
  }

  state.etapaAtual = index;
  setEtapa(index, "error", null, mensagem);
}

function construirEtapas() {
  const etapasRoot = el("etapas");

  if (state.etapasConstruidas && etapasRoot.children.length === ETAPAS.length) {
    return;
  }

  ETAPA_NODE_CACHE.length = 0;
  const fragment = document.createDocumentFragment();

  ETAPAS.forEach((etapa, index) => {
    const item = document.createElement("div");
    item.id = `etapa-${index}`;
    item.className = "etapa";
    item.innerHTML = `
      <div class="etapa-progress-track">
        <div class="etapa-progress-fill"></div>
      </div>
      <span class="etapa-code">${etapa.codigo}</span>
      <div class="etapa-copy">
        <strong>${etapa.titulo}</strong>
        <small>Aguardando execucao</small>
      </div>
    `;

    ETAPA_NODE_CACHE[index] = {
      item,
      fill: item.querySelector(".etapa-progress-fill"),
      small: item.querySelector("small")
    };

    fragment.appendChild(item);
  });

  etapasRoot.replaceChildren(fragment);
  state.etapasConstruidas = true;
}

function setEtapa(index, status = "pending", percentual = null, mensagem = "") {
  if (!Number.isInteger(index) || index < 0 || index >= ETAPAS.length) {
    return;
  }

  const progressoAtual = state.etapasProgresso[index] || 0;
  const progressoInformado = clampPercent(percentual);
  let novoProgresso = progressoAtual;

  if (status === "pending") {
    novoProgresso = 0;
  } else if (status === "done") {
    novoProgresso = 100;
  } else if (status === "error") {
    novoProgresso = progressoInformado ?? Math.max(progressoAtual, 8);
  } else if (status === "active") {
    novoProgresso = Math.max(progressoAtual, progressoInformado ?? 8);
  }

  state.etapasStatus[index] = status;
  state.etapasProgresso[index] = novoProgresso;
  state.etapasMensagens[index] = mensagem || "";

  const refs = ETAPA_NODE_CACHE[index];
  const etapaElement = refs?.item || el(`etapa-${index}`);

  if (!etapaElement) {
    return;
  }

  etapaElement.classList.remove("pending", "active", "done", "error");
  etapaElement.classList.add(status);

  const small = refs?.small || etapaElement.querySelector("small");
  const fill = refs?.fill || etapaElement.querySelector(".etapa-progress-fill");

  if (small) {
    small.textContent = getEtapaDescricao(status, mensagem);
  }

  if (fill) {
    const nextWidth = `${novoProgresso}%`;

    if (fill.style.width !== nextWidth) {
      fill.style.width = nextWidth;
    }
  }
}

function processarEtapaTempoReal(payloadOrEtapa, status, mensagem = "", percentual = null) {
  const payload = typeof payloadOrEtapa === "object" && payloadOrEtapa !== null
    ? payloadOrEtapa
    : { etapa: payloadOrEtapa, status, mensagem, percentual };

  const index = getEtapaIndexById(payload.etapa);
  const statusNormalizado = normalizarStatusTempoReal(payload.status);
  const mensagemEtapa = String(payload.mensagem || "");
  const percentualEtapa = clampPercent(payload.percentual);

  if (index === -1) {
    return;
  }

  if (statusNormalizado === "active") {
    ativarEtapa(index, percentualEtapa, mensagemEtapa);
    setStatus(`Processando ${ETAPAS[index].codigo}`, "running");
    return;
  }

  if (statusNormalizado === "done") {
    concluirEtapa(index, mensagemEtapa);

    if (index === ETAPAS.length - 1) {
      setStatus("Concluido", "success");
    }
    return;
  }

  if (statusNormalizado === "error") {
    falharEtapa(index, mensagemEtapa || "Falha na etapa");
    setStatus("Falha no processamento", "error");
    return;
  }

  setEtapa(index, "pending", 0, mensagemEtapa);
}
function limparLogs() {
  state.logCount = 0;
  updateLogCount();
  renderLogEmptyState();
}

function log(msg, classe = "") {
  const box = el("logBox");

  if (state.logCount === 0 && box.firstElementChild?.classList.contains("log-empty")) {
    box.innerHTML = "";
  }

  const line = document.createElement("div");
  line.className = `log-line ${classe}`.trim();
  line.textContent = msg;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;

  state.logCount += 1;
  updateLogCount();
}

function atualizarRodapeInfo() {
  const agora = new Date();
  const data = agora.toLocaleDateString("pt-BR");
  const hora = agora.toLocaleTimeString("pt-BR");

  const novoTextoData = `Data ${data}`;
  const novoTextoHora = `Hora ${hora}`;

  if (state.footerDateText !== novoTextoData) {
    state.footerDateText = novoTextoData;
    el("footerDate").textContent = novoTextoData;
  }

  if (state.footerTimeText !== novoTextoHora) {
    state.footerTimeText = novoTextoHora;
    el("footerTime").textContent = novoTextoHora;
  }
}

function preencherResultado(resultado = {}) {
  const box = el("resultBox");

  el("resultCliente").textContent = resultado.cliente || "--";
  el("resultPedido").textContent = resultado.pedido || "--";
  el("resultDocFat").textContent = resultado.doc_fat || "--";
  el("resultBoleto").textContent = resultado.boleto || "--";

  box.classList.remove("hidden");
}

window.preencherResultado = preencherResultado;

function esconderResultado() {
  el("resultBox").classList.add("hidden");
  el("resultCliente").textContent = "--";
  el("resultPedido").textContent = "--";
  el("resultDocFat").textContent = "--";
  el("resultBoleto").textContent = "--";
}

function hideResumeBox() {
  state.resumeCheckpoint = null;

  const box = el("resumeBox");
  if (!box) {
    return;
  }

  box.classList.add("hidden");
  el("resumeTitle").textContent = "";
  el("resumeMessage").textContent = "";
}

function showResumeBox(checkpoint, fallbackMessage = "") {
  if (!checkpoint || !checkpoint.resume_from) {
    hideResumeBox();
    return;
  }

  state.resumeCheckpoint = checkpoint;

  const index = getEtapaIndexById(checkpoint.resume_from);
  const etapa = index >= 0 ? ETAPAS[index] : null;
  const titulo = etapa
    ? `Retomar a partir de ${etapa.codigo} - ${etapa.titulo}`
    : `Retomar a partir de ${checkpoint.resume_from}`;

  el("resumeTitle").textContent = titulo;
  el("resumeMessage").textContent =
    fallbackMessage || "Depois de corrigir o problema no SAP, continue do ponto em que a automacao parou.";
  el("resumeBox").classList.remove("hidden");
}

function openLogsPopover() {
  el("logPopover").classList.remove("hidden");
  el("logBalloon").setAttribute("aria-expanded", "true");
}

function closeLogsPopover() {
  el("logPopover").classList.add("hidden");
  el("logBalloon").setAttribute("aria-expanded", "false");
}

function toggleLogsPopover(event) {
  event.stopPropagation();
  const popover = el("logPopover");

  if (popover.classList.contains("hidden")) {
    openLogsPopover();
  } else {
    closeLogsPopover();
  }
}
function openContactModal() {
  resetContactForm();
  el("contactModal").classList.remove("hidden");
  el("contactMatricula").focus();
}

function closeContactModal() {
  el("contactModal").classList.add("hidden");
  resetContactForm();
}

function updateContactCharCount() {
  const descricao = el("contactDescricao").value || "";
  el("contactCharCount").textContent = `${descricao.length} / 600`;
}

function handleContactImages() {
  const files = Array.from(el("contactImagens").files || []);
  const list = el("contactImageList");

  if (!files.length) {
    list.className = "image-list empty";
    list.textContent = "Nenhuma imagem adicionada.";
    return;
  }

  list.className = "image-list";
  list.innerHTML = files
    .map((file) => `<div class="image-pill">${file.name}</div>`)
    .join("");
}

function showContactFeedback(message, isSuccess) {
  const feedback = el("contactFeedback");
  feedback.textContent = message;
  feedback.className = `contact-feedback ${isSuccess ? "success" : "error"}`;
}

function hideContactFeedback() {
  const feedback = el("contactFeedback");
  feedback.textContent = "";
  feedback.className = "contact-feedback hidden";
}

function resetContactForm() {
  el("contactMatricula").value = "";
  el("contactNome").value = "";
  el("contactLotacao").value = "";
  el("contactSetor").value = "";
  el("contactDescricao").value = "";
  el("contactImagens").value = "";
  updateContactCharCount();
  handleContactImages();
  hideContactFeedback();
}

async function submitContactForm() {
  const submitButton = el("contactSubmitButton");
  const payload = {
    matricula: el("contactMatricula").value.trim(),
    nome: el("contactNome").value.trim(),
    lotacao: el("contactLotacao").value.trim(),
    setor: el("contactSetor").value.trim(),
    descricao: el("contactDescricao").value.trim(),
    imagens: Array.from(el("contactImagens").files || []).map((file) => file.name)
  };

  try {
    submitButton.disabled = true;
    submitButton.textContent = "Enviando...";

    const result = await window.pywebview.api.enviar_atendimento(payload);

    if (!result.ok) {
      showContactFeedback(result.msg, false);
      return;
    }

    showContactFeedback(result.msg || "Pedido de Atendimento Enviado Com Sucesso", true);

    setTimeout(() => {
      closeContactModal();
    }, 1800);
  } catch (error) {
    showContactFeedback(`Falha ao enviar atendimento: ${error}`, false);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Enviar";
  }
}

function limparPainel() {
  limparLogs();
  resetarEtapas();
  esconderResultado();
  hideResumeBox();
  limparMensagensValidacao();
  setStatus("Aguardando", "idle");
  closeLogsPopover();
}

async function reproduzirFluxo(logs, options = {}) {
  const { finalStatus = "done" } = options;

  resetarEtapas();

  for (const item of logs) {
    if (item.msg) {
      log(item.msg, item.classe || "");
    }
    await new Promise((resolve) => setTimeout(resolve, 180));
  }

  if (finalStatus === "error" && state.etapaAtual !== null) {
    falharEtapa(state.etapaAtual, "Falha na etapa");
  }
}

function montarPayloadAtual() {
  const validacao = validarFormularioAntesDoFluxo();

  if (!validacao) {
    return null;
  }

  const { docInfo, endereco } = validacao;

  return {
    doc: docInfo.digitos,
    tipo: el("tipo").value,
    valor: el("valor").value,
    modo_valor: state.valueMode,
    endereco
  };
}

function setFlowButtonsBusy(isBusy, mode = "start") {
  const submitButton = el("submitButton");
  const resumeButton = el("resumeButton");

  submitButton.disabled = isBusy;
  submitButton.textContent = isBusy ? "Gerando..." : "Gerar Boleto";

  if (resumeButton) {
    resumeButton.disabled = isBusy;
    resumeButton.textContent = isBusy && mode === "resume"
      ? "Retomando..."
      : "Continuar do ponto de parada";
  }
}

async function executarFluxo(payload, options = {}) {
  const { resume = false } = options;

  if (!resume) {
    hideResumeBox();
    window.resetarProgresso();
    setStatus("Processando", "running");
  } else {
    setStatus("Retomando", "running");
  }

  setFlowButtonsBusy(true, resume ? "resume" : "start");

  try {
    const dados = {
      ...payload,
      _resume_checkpoint: resume ? state.resumeCheckpoint : null
    };

    const res = await window.pywebview.api.gerar_boleto(dados);
    const tempoReal = Boolean(res && res.tempo_real);

    if (!res.ok) {
      if (!tempoReal) {
        await reproduzirFluxo(res.logs || [], { finalStatus: "error" });
      }

      if (res.resultado) {
        preencherResultado(res.resultado);
      }

      if (res.msg) {
        log(res.msg, "error");
      }

      showResumeBox(
        res.checkpoint,
        "Confira o SAP, corrija o problema nesta etapa e continue do mesmo ponto."
      );
      setStatus("Falha no processamento", "error");
      openLogsPopover();
      return;
    }

    hideResumeBox();

    if (!tempoReal) {
      await reproduzirFluxo(res.logs || [], { finalStatus: "done" });
    }

    preencherResultado(res.resultado || {});
    setStatus("Concluido", "success");
  } catch (error) {
    setStatus("Falha no processamento", "error");
    log(`Falha ao comunicar com o backend: ${error}`, "error");
    openLogsPopover();
  } finally {
    setFlowButtonsBusy(false);
  }
}

async function gerarBoleto() {
  const payload = montarPayloadAtual();

  if (!payload) {
    return;
  }

  await executarFluxo(payload, { resume: false });
}

async function retomarFluxo() {
  if (!state.resumeCheckpoint) {
    return;
  }

  const payload = montarPayloadAtual();

  if (!payload) {
    return;
  }

  await executarFluxo(payload, { resume: true });
}
document.addEventListener("click", (event) => {
  const menu = el("valueMenu");
  const valueButton = el("valueModeButton");
  const tipoMenu = el("tipoMenu");
  const tipoButton = el("tipoButton");
  const baseStatusMenu = el("baseStatusMenu");
  const baseStatusButton = el("baseStatusButton");
  const popover = el("logPopover");
  const balloon = el("logBalloon");
  const card = el("contactCard");
  const modal = el("contactModal");

  if (menu && valueButton && !menu.contains(event.target) && !valueButton.contains(event.target)) {
    fecharMenuValor();
  }

  if (tipoMenu && tipoButton && !tipoMenu.contains(event.target) && !tipoButton.contains(event.target)) {
    fecharMenuTipo();
  }

  if (popover && balloon && !popover.contains(event.target) && !balloon.contains(event.target)) {
    closeLogsPopover();
  }

  if (
    baseStatusMenu &&
    baseStatusButton &&
    !baseStatusMenu.contains(event.target) &&
    !baseStatusButton.contains(event.target)
  ) {
    closeBaseStatusMenu();
  }

  if (!modal.classList.contains("hidden") && card && !card.contains(event.target) && event.target.classList.contains("contact-backdrop")) {
    closeContactModal();
  }
});

el("valor").addEventListener("input", handleValorInput);
window.addEventListener("resize", atualizarEscalaLogo);

inicializarTema();
atualizarEscalaLogo();
setBaseStatus("active");
construirEtapas();
atualizarDocumentoUI("");
atualizarTipo();
atualizarModoValorUI();
registrarValidacaoInterativa();
updateContactCharCount();
handleContactImages();
setEmpreendimentoAberto(false);
setSemNumero(false);
limparPainel();
atualizarRodapeInfo();
window.setInterval(atualizarRodapeInfo, 1000);







