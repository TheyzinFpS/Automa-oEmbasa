const ETAPAS = [
  // Ordem visual das etapas exibidas no painel de andamento.
  { id: "XD03", codigo: "XD03", titulo: "Buscar cliente" },
  { id: "VA01", codigo: "VA01", titulo: "Criar pedido" },
  { id: "VF01", codigo: "VF01", titulo: "Criar doc.fat." },
  { id: "FB03", codigo: "FB03", titulo: "Ajustar contábil" },
  { id: "VF02_RESALVAR", codigo: "VF02", titulo: "Salvar faturamento" },
  { id: "F110", codigo: "F110", titulo: "Gerar pagamento" }
];

// Valores padrão definidos pela regra de negócio atual.
const VALORES = {
  viabilidade: "R$ 1.038,02",
  agua: "R$ 2.357,70",
  esgoto: "R$ 2.357,70",
  agua_esgoto: "R$ 2.357,70"
};

// Rótulos amigáveis para o campo Tipo de solicitação.
const TIPOS_SOLICITACAO = {
  "": "Selecione",
  viabilidade: "Viabilidade",
  agua: "Água",
  esgoto: "Esgoto",
  agua_esgoto: "Água + Esgoto"
};

// Status operacional exibido no card de status da base.
const BASE_STATUS = {
  active: {
    text: "✓ ATIVO",
    subtext: "Ambiente apto para operação e testes.",
    cardClass: "status-active"
  },
  maintenance: {
    text: "Em manutenção",
    subtext: "Ambiente com ajustes em andamento.",
    cardClass: "status-maintenance"
  }
};

const MAX_VALOR_CENTAVOS = 1000000;
const MAX_CONTACT_ATTACHMENT_BYTES = 15 * 1024 * 1024;
const APP_VERSION = "1.4.6";
const CEP_API_BASE_URL = "https://viacep.com.br/ws";
const CEP_DEBOUNCE_MS = 450;
const CEP_UF_PERMITIDA = "BA";
const SUPPORTED_CONTACT_EXTENSIONS = new Set([".jpg", ".jpeg", ".png"]);
const SUPPORTED_CONTACT_MIME_TYPES = new Set(["image/jpeg", "image/png"]);
const THEME_STORAGE_KEY = "embasa-theme";
const STATUS_ATIVOS = new Set([
  "processando", "processing", "running", "ativo", "active", "iniciando", "iniciado"
]);
const STATUS_CONCLUIDOS = new Set([
  "concluido", "concluida", "concluído", "concluída", "done", "success", "sucesso", "finalizado", "finalizada"
]);
const STATUS_ERRO = new Set(["erro", "error", "falha", "failed"]);
const STATUS_CANCELADO = new Set(["cancelado", "cancelada", "cancel", "canceled", "cancelled"]);
const EMPTY_LOG_MARKUP = '<div class="log-empty">Os logs do fluxo aparecerão aqui.</div>';
const PDF_NAME_NOTICE_PREFIX = "PDF_NAME_READY::";
const PAYMENT_FILE_NOTICE_PREFIX = "PAYMENT_FILE_READY::";
// Mapeia eventos vindos do Python para a etapa visual correspondente.
const DISPLAY_STAGE_MAP = (() => {
  const map = new Map();

  ETAPAS.forEach((etapa, index) => {
    const aliases = etapa.aliases || [etapa.id];
    const segmentCount = aliases.length;

    aliases.forEach((alias, segmentIndex) => {
      map.set(alias, {
        index,
        alias,
        segmentIndex,
        segmentCount,
        isGrouped: segmentCount > 1
      });
    });
  });

  return map;
})();

// Estado central da interface durante uso e execução do fluxo.
const state = {
  valueMode: "auto",
  theme: "light",
  lastTipo: "",
  logCount: 0,
  baseStatus: "active",
  empreendimentoAberto: false,
  semNumero: false,
  semCep: false,
  etapaAtual: null,
  etapasStatus: [],
  etapasProgresso: [],
  etapasMensagens: [],
  resumeCheckpoint: null,
  etapasConstruidas: false,
  footerDateText: "",
  footerTimeText: "",
  statusSnapshot: "",
  empreendimentosFila: [],
  batchRunning: false,
  flowRunning: false,
  cancelRequested: false,
  currentPdfNameNotice: "",
  lastPdfNameNotice: "",
  currentPdfNoticeId: "",
  currentPaymentFileNotice: "",
  lastPaymentFileNotice: "",
  currentPaymentNoticeId: "",
  historicoItens: [],
  historicoSelecionado: null
};

const domCache = new Map();
const ETAPA_NODE_CACHE = [];
const pendingProgressEvents = [];
const cepLookupCache = new Map();
let pendingProgressFrame = 0;
let cepLookupTimer = 0;
let cepLookupController = null;
let cepLookupSeq = 0;
let cepLookupStatus = {
  cep: "",
  valid: null,
  message: "",
  code: ""
};
let ultimoComplementoAutoCep = "";
let ultimoEnderecoAutoCep = {
  cep: "",
  rua: "",
  bairro: "",
  cidade: "",
  complemento: ""
};
let historySearchTimer = 0;

// Cache simples de elementos DOM para evitar buscas repetidas.
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

// Liga cada campo da tela ao seu elemento de mensagem de erro.
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

// Normaliza percentuais enviados pelo backend para o intervalo 0-100.
function clampPercent(value) {
  const numero = Number(value);

  if (!Number.isFinite(numero)) {
    return null;
  }

  return Math.max(0, Math.min(100, Math.round(numero)));
}

// Remove mascara do documento antes de validar/enviar ao backend.
function limparDocumento(valor) {
  return String(valor || "").replace(/\D/g, "").slice(0, 14);
}

// Aplica máscara visual de CPF/CNPJ enquanto o usuário digita.
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

// Calcula informacoes visuais do documento: tipo, contador, status e dica.
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
    badge: completo ? "CPF válido" : "CPF",
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
    badge: completo ? "CNPJ válido" : "CNPJ",
    hint: completo ? "CNPJ completo e pronto para envio ao SAP." : `CNPJ em preenchimento. Faltam ${faltam} digitos.`,
    contador: `${digitos.length} de 14 digitos`,
    classe: completo ? "valid" : "progress"
  };
}

// Remove formatacao monetaria mantendo somente os digitos.
function limparValor(valor) {
  return String(valor || "").replace(/\D/g, "");
}

// Aplica máscara de CEP no padrão 00000-000.
function formatarCepValue(valor) {
  const digitos = String(valor || "").replace(/\D/g, "").slice(0, 8);

  if (digitos.length <= 5) {
    return digitos;
  }

  return `${digitos.slice(0, 5)}-${digitos.slice(5)}`;
}

// Remove números e caracteres indevidos do campo Cidade.
function sanitizarCidade(valor) {
  return String(valor || "")
    .replace(/[^A-Za-zÀ-ÿ\s'-]/g, "")
    .replace(/\s{2,}/g, " ");
}

function obterDigitosCep(valor) {
  return String(valor || "").replace(/\D/g, "").slice(0, 8);
}

function setCepLookupStatus(cep, valid, message = "", code = "") {
  cepLookupStatus = {
    cep,
    valid,
    message,
    code
  };
}

function setCepLoading(isLoading) {
  const input = el("enderecoCep");

  if (!input) {
    return;
  }

  input.classList.toggle("is-loading", Boolean(isLoading));
  input.setAttribute("aria-busy", String(Boolean(isLoading)));
}

function formatarCep(elm) {
  if (state.semCep) {
    elm.value = "SEM CEP";
    return;
  }

  elm.value = formatarCepValue(elm.value);
  limparMensagemCampo("enderecoCep");
  agendarConsultaCep();
}

function formatarCentavosParaMoeda(centavos) {
  const valor = centavos / 100;

  return valor.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL"
  });
}

// Formata valor customizado em moeda respeitando o limite de R$ 10.000,00.
function formatarValorDigitado(valor) {
  const digitos = limparValor(valor);

  if (!digitos) {
    return "";
  }

  const centavos = Math.min(Number(digitos), MAX_VALOR_CENTAVOS);
  return formatarCentavosParaMoeda(centavos);
}

// Recupera tema salvo no navegador embutido do pywebview.
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
  const logos = document.querySelectorAll("#brandLogo, .hero-symbol-mark");

  if (!logos.length) {
    return;
  }

  logos.forEach((logo) => logo.classList.remove("logo-animated"));

  window.requestAnimationFrame(() => {
    logos.forEach((logo) => logo.classList.add("logo-animated"));
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
  input.placeholder = ativo ? "Sem número" : "Informe o número";
  limparMensagemCampo("enderecoNumero");
}

function toggleSemNumero() {
  setSemNumero(!state.semNumero);
}

function resetarEnderecoAutoCep() {
  ultimoComplementoAutoCep = "";
  ultimoEnderecoAutoCep = {
    cep: "",
    rua: "",
    bairro: "",
    cidade: "",
    complemento: ""
  };
}

function setSemCep(ativo) {
  state.semCep = ativo;

  const input = el("enderecoCep");
  const button = el("semCepButton");

  cancelarConsultaCepPendente();
  resetarEnderecoAutoCep();

  if (button) {
    button.classList.toggle("active", ativo);
  }

  if (input) {
    input.readOnly = ativo;
    input.classList.toggle("readonly-like", ativo);
    input.value = ativo ? "SEM CEP" : "";
    input.placeholder = ativo ? "Sem CEP" : "00000-000";
    input.inputMode = ativo ? "text" : "numeric";
    input.setAttribute("aria-label", ativo ? "Endereço sem CEP" : "CEP");
  }

  if (ativo) {
    setCepLookupStatus("SEM CEP", true, "", "sem_cep");
    mostrarMensagemCampo(
      "enderecoCep",
      "Sem CEP ativo. Preencha rua, bairro e cidade manualmente.",
      "info"
    );
  } else {
    setCepLookupStatus("", null, "", "");
    limparMensagemCampo("enderecoCep");
  }
}

function toggleSemCep() {
  setSemCep(!state.semCep);
}

function coletarEndereco() {
  return {
    empreendimento: el("enderecoEmpreendimento").value.trim(),
    rua: el("enderecoRua").value.trim(),
    numero: state.semNumero
      ? "S/N"
      : el("enderecoNumero").value.trim(),
    cep: state.semCep ? "SEM CEP" : formatarCepValue(el("enderecoCep").value.trim()),
    sem_cep: state.semCep,
    bairro: el("enderecoBairro").value.trim(),
    complemento: el("enderecoComplemento").value.trim(),
    cidade: sanitizarCidade(el("enderecoCidade").value.trim()),
    estado: "BA"
  };
}

function enderecoTemConteudo(endereco) {
  return [
    endereco.empreendimento,
    endereco.rua,
    endereco.numero && endereco.numero !== "S/N" ? endereco.numero : "",
    endereco.cep,
    endereco.bairro,
    endereco.complemento,
    endereco.cidade
  ].some((valor) => String(valor || "").trim());
}

function cloneEndereco(endereco) {
  const semCep = Boolean(endereco.sem_cep) || String(endereco.cep || "").trim().toUpperCase() === "SEM CEP";

  return {
    empreendimento: String(endereco.empreendimento || "").trim(),
    rua: String(endereco.rua || "").trim(),
    numero: String(endereco.numero || "").trim() || "S/N",
    cep: semCep ? "SEM CEP" : formatarCepValue(endereco.cep || ""),
    sem_cep: semCep,
    bairro: String(endereco.bairro || "").trim(),
    complemento: String(endereco.complemento || "").trim(),
    cidade: sanitizarCidade(endereco.cidade || "").trim(),
    estado: "BA"
  };
}

function formatarEnderecoResumo(endereco) {
  const cepResumo = endereco.sem_cep
    ? "SEM CEP"
    : (endereco.cep ? `CEP ${endereco.cep}` : "");
  const partes = [
    `${endereco.rua || ""}, ${endereco.numero || ""}`.trim(),
    endereco.bairro,
    endereco.cidade ? `${endereco.cidade}-${endereco.estado || "BA"}` : "",
    cepResumo
  ].filter(Boolean);

  return partes.join(" | ");
}

function limparCamposEndereco() {
  cancelarConsultaCepPendente();
  setCepLookupStatus("", null, "");
  resetarEnderecoAutoCep();
  el("enderecoEmpreendimento").value = "";
  el("enderecoRua").value = "";
  el("enderecoCep").value = "";
  el("enderecoBairro").value = "";
  el("enderecoComplemento").value = "";
  el("enderecoCidade").value = "";
  setSemNumero(false);
  setSemCep(false);
  limparMensagensValidacao();
}

function renderizarFilaEmpreendimentos() {
  const queue = el("empreendimentoQueue");

  if (!queue) {
    return;
  }

  if (!state.empreendimentosFila.length) {
    queue.className = "batch-queue empty";
    queue.textContent = "Nenhum empreendimento adicional na fila.";
    return;
  }

  queue.className = "batch-queue";
  queue.innerHTML = state.empreendimentosFila
    .map((endereco, index) => `
      <div class="batch-item">
        <div>
          <strong>${index + 1}. ${escapeHtml(endereco.empreendimento)}</strong>
          <small>${escapeHtml(formatarEnderecoResumo(endereco))}</small>
        </div>
        <button type="button" onclick="removerEmpreendimentoDaFila(${index})">Remover</button>
      </div>
    `)
    .join("");
}

function adicionarEmpreendimentoNaFila() {
  const validacao = validarFormularioAntesDoFluxo();

  if (!validacao) {
    return;
  }

  state.empreendimentosFila.push(cloneEndereco(validacao.endereco));
  renderizarFilaEmpreendimentos();
  log(
    `Empreendimento adicionado à fila: ${validacao.endereco.empreendimento} - ${formatarEnderecoResumo(validacao.endereco)}.`
  );
  limparCamposEndereco();
  setEmpreendimentoAberto(true);
  setStatus("Empreendimento adicionado", "success");
}

function removerEmpreendimentoDaFila(index) {
  if (index < 0 || index >= state.empreendimentosFila.length) {
    return;
  }

  state.empreendimentosFila.splice(index, 1);
  renderizarFilaEmpreendimentos();
}

function limparFilaEmpreendimentos() {
  state.empreendimentosFila = [];
  renderizarFilaEmpreendimentos();
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
    message.className = "field-message hidden";
  }
}

function limparMensagensValidacao() {
  Object.keys(VALIDATION_FIELDS).forEach(limparMensagemCampo);
}

function mostrarMensagemCampo(fieldId, message, variant = "info", highlight = false) {
  const config = VALIDATION_FIELDS[fieldId];
  const baseElement = el(fieldId);
  const focusTarget = el(config?.focusId || fieldId) || baseElement;
  const field = focusTarget ? focusTarget.closest(".field") : null;
  const messageEl = config ? el(config.messageId) : null;

  if (field) {
    field.classList.toggle("has-error", Boolean(highlight));
  }

  if (messageEl) {
    messageEl.textContent = message;
    messageEl.className = `field-message ${variant}`;
  }
}

function cancelarConsultaCepPendente() {
  if (cepLookupTimer) {
    window.clearTimeout(cepLookupTimer);
    cepLookupTimer = 0;
  }

  if (cepLookupController) {
    cepLookupController.abort();
    cepLookupController = null;
  }

  setCepLoading(false);
}

function obterComplementoViaCep(data) {
  return [data?.complemento, data?.unidade]
    .map((item) => String(item || "").trim())
    .filter(Boolean)
    .join(" - ");
}

function deveAtualizarCampoEndereco(input, valorAnteriorAuto, forcarAtualizacao) {
  const valorAtual = String(input?.value || "").trim();

  return forcarAtualizacao || !valorAtual || valorAtual === String(valorAnteriorAuto || "").trim();
}

function preencherCampoEndereco(input, valor, valorAnteriorAuto, forcarAtualizacao, fieldId) {
  const valorNormalizado = String(valor || "").trim();

  if (!input || !valorNormalizado) {
    return "";
  }

  if (deveAtualizarCampoEndereco(input, valorAnteriorAuto, forcarAtualizacao)) {
    input.value = valorNormalizado;
    limparMensagemCampo(fieldId);
  }

  return valorNormalizado;
}

function preencherEnderecoComCep(data, cep) {
  const rua = el("enderecoRua");
  const bairro = el("enderecoBairro");
  const cidade = el("enderecoCidade");
  const estado = el("enderecoEstado");
  const complemento = el("enderecoComplemento");
  const complementoApi = obterComplementoViaCep(data);
  const cepAtual = String(cep || "").trim();
  const forcarAtualizacao = ultimoEnderecoAutoCep.cep !== cepAtual;

  const ruaAuto = preencherCampoEndereco(
    rua,
    data.logradouro,
    ultimoEnderecoAutoCep.rua,
    forcarAtualizacao,
    "enderecoRua"
  );
  const bairroAuto = preencherCampoEndereco(
    bairro,
    data.bairro,
    ultimoEnderecoAutoCep.bairro,
    forcarAtualizacao,
    "enderecoBairro"
  );
  const cidadeAuto = preencherCampoEndereco(
    cidade,
    sanitizarCidade(data.localidade || "").trim(),
    ultimoEnderecoAutoCep.cidade,
    forcarAtualizacao,
    "enderecoCidade"
  );

  if (estado) {
    estado.value = CEP_UF_PERMITIDA;
  }

  if (
    complementoApi &&
    deveAtualizarCampoEndereco(complemento, ultimoEnderecoAutoCep.complemento, forcarAtualizacao)
  ) {
    complemento.value = complementoApi;
    ultimoComplementoAutoCep = complementoApi;
  } else if (complemento.value.trim() === ultimoComplementoAutoCep) {
    complemento.value = "";
    ultimoComplementoAutoCep = "";
  }

  ultimoEnderecoAutoCep = {
    cep: cepAtual,
    rua: ruaAuto,
    bairro: bairroAuto,
    cidade: cidadeAuto,
    complemento: complementoApi
  };
}

async function consultarCepViaCep(cep, signal) {
  if (cepLookupCache.has(cep)) {
    return cepLookupCache.get(cep);
  }

  const response = await fetch(`${CEP_API_BASE_URL}/${cep}/json/`, {
    method: "GET",
    signal
  });

  if (!response.ok) {
    return {
      ok: false,
      code: response.status === 400 ? "invalid" : "network",
      message: response.status === 400
        ? "CEP inválido. Informe 8 dígitos numéricos."
        : "Não foi possível consultar o CEP agora. Preencha o endereço manualmente."
    };
  }

  const data = await response.json();

  if (!data || typeof data !== "object") {
    return {
      ok: false,
      code: "empty",
      message: "A consulta do CEP não retornou dados. Confira o CEP informado."
    };
  }

  if (data.erro) {
    const resultado = {
      ok: false,
      code: "not_found",
      message: "CEP não encontrado na consulta. Preencha o endereço manualmente para prosseguir."
    };

    cepLookupCache.set(cep, resultado);
    return resultado;
  }

  const resultado = {
    ok: true,
    data
  };

  cepLookupCache.set(cep, resultado);
  return resultado;
}

async function buscarCepAutomaticamente(cep) {
  if (state.semCep) {
    return;
  }

  const requestId = ++cepLookupSeq;

  if (cepLookupController) {
    cepLookupController.abort();
  }

  cepLookupController = new AbortController();
  setCepLoading(true);
  mostrarMensagemCampo("enderecoCep", "Consultando CEP...", "info");

  try {
    const resultado = await consultarCepViaCep(cep, cepLookupController.signal);

    if (requestId !== cepLookupSeq) {
      return;
    }

    if (!resultado.ok) {
      const bloqueiaFluxo = resultado.code === "invalid";
      setCepLookupStatus(cep, bloqueiaFluxo ? false : null, resultado.message, resultado.code);
      mostrarMensagemCampo(
        "enderecoCep",
        resultado.message,
        bloqueiaFluxo ? "warning" : "info",
        bloqueiaFluxo
      );
      return;
    }

    const data = resultado.data;
    const uf = String(data.uf || "").trim().toUpperCase();

    if (uf !== CEP_UF_PERMITIDA) {
      const localidade = [data.localidade, uf].filter(Boolean).join("-");
      const message = localidade
        ? `CEP localizado em ${localidade}. Utilize um CEP da Bahia.`
        : "CEP localizado fora da Bahia. Utilize um CEP da Bahia.";

      setCepLookupStatus(cep, false, message, "outside_ba");
      mostrarMensagemCampo("enderecoCep", message, "warning", true);
      return;
    }

    if (!data.logradouro && !data.bairro && !data.localidade) {
      const message = "CEP retornou sem dados suficientes. Preencha o endereço manualmente para prosseguir.";

      setCepLookupStatus(cep, null, message, "empty");
      mostrarMensagemCampo("enderecoCep", message, "info");
      return;
    }

    preencherEnderecoComCep(data, cep);
    setCepLookupStatus(cep, true, "", "ok");
    mostrarMensagemCampo(
      "enderecoCep",
      `CEP localizado: ${sanitizarCidade(data.localidade || "Bahia").trim()}-BA. Campos preenchidos automaticamente.`,
      "success"
    );
  } catch (error) {
    if (error?.name === "AbortError") {
      return;
    }

    const message = "Erro de conexão ao consultar o CEP. Preencha o endereço manualmente.";
    setCepLookupStatus(cep, null, message, "network");
    mostrarMensagemCampo("enderecoCep", message, "info");
  } finally {
    if (requestId === cepLookupSeq) {
      setCepLoading(false);
      cepLookupController = null;
    }
  }
}

function agendarConsultaCep(options = {}) {
  const { immediate = false, mostrarIncompleto = false } = options;
  const input = el("enderecoCep");
  const cep = obterDigitosCep(input?.value);

  if (state.semCep) {
    cancelarConsultaCepPendente();
    setCepLookupStatus("SEM CEP", true, "", "sem_cep");
    return;
  }

  if (cepLookupTimer) {
    window.clearTimeout(cepLookupTimer);
    cepLookupTimer = 0;
  }

  if (cepLookupController) {
    cepLookupController.abort();
    cepLookupController = null;
  }

  setCepLoading(false);

  if (!cep) {
    setCepLookupStatus("", null, "", "");
    return;
  }

  if (cep.length < 8) {
    setCepLookupStatus(cep, null, "", "incomplete");

    if (mostrarIncompleto) {
      mostrarMensagemCampo("enderecoCep", "CEP incompleto. Informe 8 dígitos.", "warning", true);
    }

    return;
  }

  const executar = () => buscarCepAutomaticamente(cep);

  if (immediate) {
    executar();
    return;
  }

  cepLookupTimer = window.setTimeout(executar, CEP_DEBOUNCE_MS);
}

function registrarCepAutocomplete() {
  const input = el("enderecoCep");

  if (!input) {
    return;
  }

  input.addEventListener("blur", () => {
    agendarConsultaCep({ immediate: true, mostrarIncompleto: true });
  });
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
    messageEl.className = "field-message error";
  }

  if (focusTarget) {
    focusTarget.scrollIntoView({ behavior: "smooth", block: "center" });

    if (typeof focusTarget.focus === "function") {
      window.setTimeout(() => focusTarget.focus(), 160);
    }
  }

    setStatus("Atenção", "error");
  setStatus("Aguardando", "idle");
  closeLogsPopover();
}

function valorFoiInformado() {
  const valor = limparValor(el("valor").value);
  return Boolean(valor) && Number(valor) > 0;
}

function validarBaseAntesDoFluxo() {
  const docInfo = analisarDocumento(el("doc").value);
  const tipo = el("tipo").value;

  if (!docInfo.digitos) {
    mostrarErroCampo("doc", "CPF/CNPJ obrigatório.");
    return null;
  }

  if (![11, 14].includes(docInfo.digitos.length)) {
    mostrarErroCampo("doc", "Informe um CPF com 11 digitos ou um CNPJ com 14 digitos para prosseguir.");
    return null;
  }

  if (!tipo) {
    mostrarErroCampo("tipo", "Selecione o tipo de solicitação. Esta é a próxima etapa obrigatória.");
    return null;
  }

  if (!valorFoiInformado()) {
    mostrarErroCampo("valor", "Informe o valor da solicitação. Esta é a próxima etapa obrigatória.");
    return null;
  }

  return { docInfo, tipo };
}

function validarEnderecoAntesDoFluxo(endereco) {
  const cepLimpo = String(endereco.cep || "").replace(/\D/g, "");
  const semCep = Boolean(endereco.sem_cep);

  if (!endereco.empreendimento) {
    mostrarErroCampo("enderecoEmpreendimento", "Informe o empreendimento. Esta é a próxima etapa obrigatória.");
    return false;
  }

  if (!endereco.rua) {
    mostrarErroCampo("enderecoRua", "Informe a rua do empreendimento para prosseguir.");
    return false;
  }

  if (!endereco.numero) {
    mostrarErroCampo("enderecoNumero", "Informe o número do endereço ou marque S/N para prosseguir.");
    return false;
  }

  if (!semCep && !cepLimpo) {
    mostrarErroCampo("enderecoCep", "Informe o CEP do empreendimento. Esta é a próxima etapa obrigatória.");
    return false;
  }

  if (!semCep && cepLimpo.length !== 8) {
    mostrarErroCampo("enderecoCep", "Informe um CEP válido com 8 dígitos para prosseguir.");
    return false;
  }

  if (!endereco.bairro) {
    mostrarErroCampo("enderecoBairro", "Informe o bairro do empreendimento para prosseguir.");
    return false;
  }

  if (!endereco.cidade) {
    mostrarErroCampo("enderecoCidade", "Informe a cidade do empreendimento para prosseguir.");
    return false;
  }

  if (/[^A-Za-zÀ-ÿ\s'-]/.test(endereco.cidade)) {
    mostrarErroCampo("enderecoCidade", "A cidade deve conter apenas letras.");
    return false;
  }

  if (!semCep && cepLookupStatus.cep === cepLimpo && cepLookupStatus.valid === false) {
    const bloqueiaPorCep = ["invalid", "outside_ba"].includes(cepLookupStatus.code);

    if (bloqueiaPorCep) {
      mostrarErroCampo(
        "enderecoCep",
        cepLookupStatus.message || "CEP inválido ou incompatível com o estado da Bahia."
      );
      return false;
    }

    mostrarMensagemCampo(
      "enderecoCep",
      cepLookupStatus.message || "CEP não localizado na consulta. Prosseguindo com endereço manual.",
      "info"
    );
  }

  return true;
}

// Garante que todos os campos obrigatórios foram preenchidos antes do SAP rodar.
function validarFormularioAntesDoFluxo() {
  const base = validarBaseAntesDoFluxo();

  if (!base) {
    return null;
  }

  const endereco = coletarEndereco();

  if (!validarEnderecoAntesDoFluxo(endereco)) {
    return null;
  }

  limparMensagensValidacao();

  return {
    docInfo: base.docInfo,
    endereco
  };
}

// Aplica tema claro/escuro e atualiza textos do botao de alternancia.
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

// Atualiza visualmente o status operacional da base.
function setBaseStatus(status) {
  if (!BASE_STATUS[status]) {
    return;
  }

  state.baseStatus = status;

  const config = BASE_STATUS[status];
  const card = el("baseStatusCard");
  const text = el("baseStatusText");
  const sub = el("baseStatusSub");

  if (card) {
    card.classList.remove("status-active", "status-maintenance");
    card.classList.add(config.cardClass);
  }

  if (text) {
    text.textContent = config.text;
  }

  if (sub) {
    sub.textContent = config.subtext;
  }
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

// Sincroniza input, badge, contador e dica do CPF/CNPJ.
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

function formatarDoc(elm) {
  limparMensagemCampo("doc");
  atualizarDocumentoUI(elm.value);
}

// Atualiza tipo de solicitação e reseta valor customizado quando necessário.
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

// Alterna entre valor de tabela e valor customizado.
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

// Remove mensagens de erro conforme o usuário corrige cada campo.
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

  if (DISPLAY_STAGE_MAP.has(chave)) {
    return DISPLAY_STAGE_MAP.get(chave).index;
  }

  return ETAPAS.findIndex((etapa) => etapa.codigo === chave);
}

function getDisplayStageMeta(idOuCodigo) {
  const chave = String(idOuCodigo || "").trim().toUpperCase();

  if (!chave) {
    return null;
  }

  if (DISPLAY_STAGE_MAP.has(chave)) {
    return DISPLAY_STAGE_MAP.get(chave);
  }

  const directIndex = ETAPAS.findIndex((etapa) => etapa.id === chave || etapa.codigo === chave);

  if (directIndex === -1) {
    return null;
  }

  return {
    index: directIndex,
    alias: chave,
    segmentIndex: 0,
    segmentCount: 1,
    isGrouped: false
  };
}

function normalizeGroupedPercent(meta, status, percentual) {
  const informed = clampPercent(percentual);

  if (!meta || !meta.isGrouped) {
    return informed;
  }

  const segmentSize = 100 / meta.segmentCount;
  const segmentStart = meta.segmentIndex * segmentSize;
  const segmentEnd = segmentStart + segmentSize;

  if (status === "done") {
    return Math.round(segmentEnd);
  }

  if (status === "active" || status === "error") {
    const localPercent = informed ?? 8;
    return Math.round(segmentStart + ((segmentEnd - segmentStart) * localPercent) / 100);
  }

  return informed;
}

function getEtapaDescricao(status, mensagem) {
  if (mensagem) {
    return mensagem;
  }

  if (status === "active") return "Em processamento";
  if (status === "done") return "Concluído";
  if (status === "error") return "Falha na etapa";
  return "Aguardando execução";
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

  if (STATUS_CANCELADO.has(valor)) {
    return "error";
  }

  return "pending";
}

// Funcao chamada pelo Python para reiniciar visualmente o progresso.
window.resetarProgresso = function resetarProgresso() {
  limparPainel();
};

// Recebe eventos em tempo real do backend e processa no próximo frame visual.
window.atualizarProgresso = function atualizarProgresso(payloadOrEtapa, status, mensagem = "", percentual = null) {
  const payload = typeof payloadOrEtapa === "object" && payloadOrEtapa !== null
    ? payloadOrEtapa
    : { etapa: payloadOrEtapa, status, mensagem, percentual };

  pendingProgressEvents.push(payload);

  if (!pendingProgressFrame) {
    pendingProgressFrame = window.requestAnimationFrame(() => {
      pendingProgressFrame = 0;

      while (pendingProgressEvents.length) {
        processarEtapaTempoReal(pendingProgressEvents.shift());
      }
    });
  }
};

// Volta todas as etapas para aguardando execução.
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

// Monta o HTML das etapas de progresso uma unica vez.
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
        <small>Aguardando execução</small>
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

// Atualiza uma etapa especifica, incluindo barra verde e mensagem.
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

// Traduz o evento do backend para o comportamento visual correto da etapa.
function processarEtapaTempoReal(payloadOrEtapa, status, mensagem = "", percentual = null) {
  const payload = typeof payloadOrEtapa === "object" && payloadOrEtapa !== null
    ? payloadOrEtapa
    : { etapa: payloadOrEtapa, status, mensagem, percentual };

  const meta = getDisplayStageMeta(payload.etapa);
  const index = meta ? meta.index : -1;
  const statusNormalizado = normalizarStatusTempoReal(payload.status);
  const mensagemEtapa = tratarAvisosOperacionais(String(payload.mensagem || ""));
  const percentualEtapa = normalizeGroupedPercent(meta, statusNormalizado, payload.percentual);

  if (index === -1) {
    return;
  }

  if (statusNormalizado === "active") {
    ativarEtapa(index, percentualEtapa, mensagemEtapa);
    setStatus(mensagemEtapa || `Processando ${ETAPAS[index].codigo}`, "running");
    return;
  }

  if (statusNormalizado === "done") {
    if (meta?.isGrouped && meta.segmentIndex < meta.segmentCount - 1) {
      ativarEtapa(index, percentualEtapa, mensagemEtapa);
      return;
    }

    concluirEtapa(index, mensagemEtapa);

    if (index === ETAPAS.length - 1) {
      setStatus("Concluído", "success");
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

// Limpa somente os logs visíveis ao usuário final.
function limparLogs() {
  state.logCount = 0;
  updateLogCount();
  renderLogEmptyState();
}

function extrairNomePdfDoAviso(mensagem) {
  const texto = String(mensagem || "").trim();

  if (!texto) {
    return "";
  }

  if (texto.startsWith(PDF_NAME_NOTICE_PREFIX)) {
    return texto.slice(PDF_NAME_NOTICE_PREFIX.length).trim();
  }

  const marcador = "Nome do PDF copiado. Cole no PDFCreator:";
  const indice = texto.indexOf(marcador);

  if (indice === -1) {
    return "";
  }

  return texto.slice(indice + marcador.length).trim();
}

function extrairNomeMeioPagamentoDoAviso(mensagem) {
  const texto = String(mensagem || "").trim();

  if (!texto) {
    return "";
  }

  if (texto.startsWith(PAYMENT_FILE_NOTICE_PREFIX)) {
    return texto.slice(PAYMENT_FILE_NOTICE_PREFIX.length).trim();
  }

  return "";
}

function limparMensagemAvisoPdf(mensagem) {
  const texto = String(mensagem || "").trim();

  if (texto.startsWith(PDF_NAME_NOTICE_PREFIX)) {
    return "Linha de boleto selecionada. Impressão manual liberada.";
  }

  if (extrairNomePdfDoAviso(texto)) {
    return "Linha de boleto selecionada. Impressão manual liberada.";
  }

  return texto;
}

function limparMensagemAvisoMeioPagamento(mensagem) {
  const texto = String(mensagem || "").trim();

  if (texto.startsWith(PAYMENT_FILE_NOTICE_PREFIX)) {
    return "Nome do arquivo de meio de pagamento pronto para copiar.";
  }

  return texto;
}

function tratarAvisoNomePdf(mensagem) {
  const nomePdf = extrairNomePdfDoAviso(mensagem);

  if (nomePdf) {
    openPdfNameModal(nomePdf);
  }

  return limparMensagemAvisoPdf(mensagem);
}

function tratarAvisoMeioPagamento(mensagem) {
  const nomeArquivo = extrairNomeMeioPagamentoDoAviso(mensagem);

  if (nomeArquivo) {
    openPaymentFileModal(nomeArquivo);
  }

  return limparMensagemAvisoMeioPagamento(mensagem);
}

function tratarAvisosOperacionais(mensagem) {
  return tratarAvisoMeioPagamento(tratarAvisoNomePdf(mensagem));
}

function copiarTextoFallback(texto) {
  const textarea = document.createElement("textarea");
  textarea.value = texto;
  textarea.setAttribute("readonly", "readonly");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();

  try {
    document.execCommand("copy");
  } finally {
    textarea.remove();
  }
}

async function copiarTextoParaAreaTransferencia(texto) {
  const conteudo = String(texto || "");

  if (!conteudo) {
    return;
  }

  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(conteudo);
      return;
    } catch (error) {
      // O WebView pode bloquear clipboard moderno em alguns ambientes.
    }
  }

  copiarTextoFallback(conteudo);
}

function openPdfNameModal(nomePdf) {
  const nomeLimpo = String(nomePdf || "").trim();

  if (!nomeLimpo) {
    return;
  }

  if (state.lastPdfNameNotice === nomeLimpo) {
    return;
  }

  state.currentPdfNameNotice = nomeLimpo;
  state.lastPdfNameNotice = nomeLimpo;

  try {
    window.focus();
  } catch (error) {
    // O foco visual pode depender do Windows/SAP, mas o aviso fica pronto na interface.
  }

  const value = el("pdfNameValue");

  if (value) {
    value.textContent = nomeLimpo;
  }

  openModal("pdfNameModal");
}

function openPdfNameModalComConfirmacao(nomePdf, noticeId = "") {
  state.lastPdfNameNotice = "";
  state.currentPdfNoticeId = String(noticeId || "");
  openPdfNameModal(nomePdf);
}

function closePdfNameModal() {
  closeModal("pdfNameModal");
}

async function confirmarAvisoOperacional(noticeId) {
  const id = String(noticeId || "").trim();

  if (!id || !window.pywebview?.api?.confirmar_aviso_operacional) {
    return;
  }

  try {
    await window.pywebview.api.confirmar_aviso_operacional(id);
  } catch (error) {
    log(`Não foi possível confirmar o aviso operacional: ${error}`, "error");
  }
}

async function copyPdfNameAndClose() {
  await copiarTextoParaAreaTransferencia(state.currentPdfNameNotice);
  const noticeId = state.currentPdfNoticeId;
  state.currentPdfNoticeId = "";
  closePdfNameModal();
  await confirmarAvisoOperacional(noticeId);
}

function openPaymentFileModal(nomeArquivo) {
  const nomeLimpo = String(nomeArquivo || "").trim();

  if (!nomeLimpo) {
    return;
  }

  if (state.lastPaymentFileNotice === nomeLimpo) {
    return;
  }

  state.currentPaymentFileNotice = nomeLimpo;
  state.lastPaymentFileNotice = nomeLimpo;

  try {
    window.focus();
  } catch (error) {
    // O foco depende do Windows/SAP, mas o aviso fica pronto na interface.
  }

  const value = el("paymentFileNameValue");

  if (value) {
    value.textContent = nomeLimpo;
  }

  openModal("paymentFileModal");
}

function openPaymentFileModalComConfirmacao(nomeArquivo, noticeId = "") {
  state.lastPaymentFileNotice = "";
  state.currentPaymentNoticeId = String(noticeId || "");
  openPaymentFileModal(nomeArquivo);
}

function closePaymentFileModal() {
  closeModal("paymentFileModal");
}

async function copyPaymentFileNameAndClose() {
  await copiarTextoParaAreaTransferencia(state.currentPaymentFileNotice);
  const noticeId = state.currentPaymentNoticeId;
  state.currentPaymentNoticeId = "";
  closePaymentFileModal();
  await confirmarAvisoOperacional(noticeId);
}

function mostrarAvisoOperacional(tipo, payload = {}) {
  const noticeId = String(payload.id || "");
  const nome = String(payload.nome || payload.nome_arquivo || payload.nome_pdf || "").trim();

  if (!nome) {
    confirmarAvisoOperacional(noticeId);
    return;
  }

  if (tipo === "payment") {
    openPaymentFileModalComConfirmacao(nome, noticeId);
    return;
  }

  openPdfNameModalComConfirmacao(nome, noticeId);
}

window.mostrarAvisoOperacional = mostrarAvisoOperacional;

function historyResumoItem(item = {}) {
  const dataHora = [item.data, item.hora].filter(Boolean).join(" ");
  const pedido = item.numero_pedido || item.doc_fat || "--";
  const cliente = item.nome_cliente || "Cliente não identificado";
  const empreendimento = item.empreendimento || "Empreendimento não informado";

  return `
    <button
      type="button"
      class="history-item"
      onclick="selecionarHistorico('${escapeHtml(item.id)}')"
    >
      <span>${escapeHtml(dataHora || "Sem data")}</span>
      <strong>Pedido ${escapeHtml(pedido)}</strong>
      <small>${escapeHtml(cliente)} • ${escapeHtml(empreendimento)}</small>
    </button>
  `;
}

function renderHistoryList(items = []) {
  const list = el("historyList");

  if (!items.length) {
    list.innerHTML = '<div class="history-empty">Nenhum registro encontrado.</div>';
    return;
  }

  list.innerHTML = items.map(historyResumoItem).join("");
}

function campoHistorico(label, value) {
  return `
    <div class="history-field">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value || "--")}</strong>
    </div>
  `;
}

function renderHistoryDetail(registro = null) {
  const detail = el("historyDetail");

  if (!registro) {
    detail.innerHTML = `
      <div class="history-empty">
        Selecione um pedido para visualizar cliente, documento, número SAP e texto padrão.
      </div>
    `;
    return;
  }

  const endereco = registro.endereco || {};
  const documento = `${registro.documento_formatado || "--"} (${registro.tipo_pessoa_label || "--"})`;
  const pedido = registro.numero_pedido || registro.faturamento || registro.doc_fat || "--";
  const docFat = registro.doc_fat || registro.faturamento || "--";

  detail.innerHTML = `
    <div class="history-detail-head">
      <span>${escapeHtml([registro.data, registro.hora].filter(Boolean).join(" "))}</span>
      <strong>Pedido ${escapeHtml(pedido)}</strong>
    </div>

    <div class="history-field-grid">
      ${campoHistorico("Nome do cliente", registro.nome_cliente)}
      ${campoHistorico("CPF/CNPJ", documento)}
      ${campoHistorico("Tipo de pessoa", registro.tipo_pessoa_label)}
      ${campoHistorico("Número do cliente", registro.numero_cliente)}
      ${campoHistorico("Número do pedido", pedido)}
      ${campoHistorico("Doc. fat", docFat)}
      ${campoHistorico("Boleto/BOL", registro.boleto || registro.identificacao_pagamento)}
      ${campoHistorico("Tipo", registro.tipo_solicitacao_label)}
      ${campoHistorico("Valor", registro.valor)}
      ${campoHistorico("Empreendimento", endereco.empreendimento)}
      ${campoHistorico("Endereço", `${endereco.rua || "--"}, ${endereco.numero || "--"}`)}
      ${campoHistorico("Bairro", endereco.bairro)}
      ${campoHistorico("Cidade/UF", `${endereco.cidade || "--"}-${endereco.estado || "--"}`)}
      ${campoHistorico("CEP", endereco.cep)}
    </div>

    <div class="history-text-block">
      <span>Texto padrão VA01</span>
      <pre>${escapeHtml(registro.texto_padrao || "--")}</pre>
    </div>
  `;
}

async function carregarHistorico() {
  const list = el("historyList");
  const filtro = el("historySearch")?.value || "";

  list.innerHTML = '<div class="history-empty">Carregando histórico...</div>';

  try {
    if (!window.pywebview?.api?.listar_historico) {
      list.innerHTML = '<div class="history-empty">Histórico disponível apenas dentro do aplicativo pywebview.</div>';
      renderHistoryDetail(null);
      return;
    }

    const resposta = await window.pywebview.api.listar_historico(filtro);

    if (!resposta?.ok) {
      list.innerHTML = `<div class="history-empty">${escapeHtml(resposta?.msg || "Falha ao carregar histórico.")}</div>`;
      return;
    }

    state.historicoItens = resposta.itens || [];
    renderHistoryList(state.historicoItens);

    if (state.historicoItens.length) {
      await selecionarHistorico(state.historicoItens[0].id);
    } else {
      renderHistoryDetail(null);
    }
  } catch (error) {
    list.innerHTML = `<div class="history-empty">Falha ao carregar histórico: ${escapeHtml(error)}</div>`;
  }
}

function scheduleHistorySearch() {
  window.clearTimeout(historySearchTimer);
  historySearchTimer = window.setTimeout(carregarHistorico, 350);
}

function handleHistorySearchKey(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    carregarHistorico();
  }
}

async function selecionarHistorico(id) {
  const registroId = String(id || "").trim();

  if (!registroId) {
    return;
  }

  try {
    const resposta = await window.pywebview.api.obter_historico(registroId);

    if (!resposta?.ok) {
      renderHistoryDetail({
        numero_pedido: "--",
        texto_padrao: resposta?.msg || "Registro não encontrado."
      });
      return;
    }

    state.historicoSelecionado = resposta.registro;
    renderHistoryDetail(resposta.registro);

    Array.from(document.querySelectorAll(".history-item")).forEach((button) => {
      button.classList.toggle(
        "selected",
        button.getAttribute("onclick")?.includes(registroId)
      );
    });
  } catch (error) {
    renderHistoryDetail({
      numero_pedido: "--",
      texto_padrao: `Falha ao abrir histórico: ${error}`
    });
  }
}

function openHistoryModal() {
  openModal("historyModal");
  carregarHistorico();
  window.setTimeout(() => el("historySearch")?.focus(), 50);
}

function closeHistoryModal() {
  closeModal("historyModal");
}

// Adiciona uma linha ao balao de logs publicos.
function log(msg, classe = "") {
  const box = el("logBox");
  const mensagemVisivel = tratarAvisosOperacionais(msg);

  if (state.logCount === 0 && box.firstElementChild?.classList.contains("log-empty")) {
    box.innerHTML = "";
  }

  const line = document.createElement("div");
  line.className = `log-line ${classe}`.trim();
  line.textContent = mensagemVisivel;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;

  state.logCount += 1;
  updateLogCount();
}

// Mantem data e hora do rodape sempre atualizadas.
function atualizarRodapeInfo() {
  const agora = new Date();
  const data = agora.toLocaleDateString("pt-BR");
  const hora = agora.toLocaleTimeString("pt-BR");

  const novoTextoData = `Data ${data}`;
  const novoTextoHora = `Hora ${hora}`;
  const novoTextoVersao = `Versão da API ${APP_VERSION}`;

  if (state.footerDateText !== novoTextoData) {
    state.footerDateText = novoTextoData;
    el("footerDate").textContent = novoTextoData;
  }

  if (state.footerTimeText !== novoTextoHora) {
    state.footerTimeText = novoTextoHora;
    el("footerTime").textContent = novoTextoHora;
  }

  if (el("footerVersion").textContent !== novoTextoVersao) {
    el("footerVersion").textContent = novoTextoVersao;
  }
}

function formatarBytes(bytes) {
  const valor = Number(bytes || 0);

  if (!Number.isFinite(valor) || valor <= 0) {
    return "0 KB";
  }

  if (valor >= 1024 * 1024) {
    return `${(valor / (1024 * 1024)).toFixed(2)} MB`;
  }

  return `${Math.max(1, Math.round(valor / 1024))} KB`;
}

function getFileExtension(name) {
  const normalized = String(name || "").trim().toLowerCase();
  const lastDot = normalized.lastIndexOf(".");
  return lastDot >= 0 ? normalized.slice(lastDot) : "";
}

// Valida extensao e MIME type dos anexos do Fale Conosco.
function isSupportedContactFile(file) {
  const extension = getFileExtension(file?.name);
  const mimeType = String(file?.type || "").trim().toLowerCase();

  if (!SUPPORTED_CONTACT_EXTENSIONS.has(extension)) {
    return false;
  }

  if (mimeType && !SUPPORTED_CONTACT_MIME_TYPES.has(mimeType)) {
    return false;
  }

  return true;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// Preenche o card de resultado com cliente, faturamento, doc_fat e boleto.
function preencherResultado(resultado = {}) {
  const box = el("resultBox");

  const valorPedidoOuFaturamento = resultado.pedido || resultado.faturamento || "--";
  const valorBoletoOuIdentificacao =
    resultado.boleto || resultado.identificacao_pagamento || "--";

  el("resultCliente").textContent = resultado.cliente || "--";
  el("resultPedido").textContent = valorPedidoOuFaturamento;
  el("resultDocFat").textContent = resultado.doc_fat || "--";
  el("resultBoleto").textContent = valorBoletoOuIdentificacao;

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

function cloneCheckpoint(checkpoint) {
  if (!checkpoint) {
    return null;
  }

  try {
    return JSON.parse(JSON.stringify(checkpoint));
  } catch (error) {
    return checkpoint;
  }
}

function formatarListaResumoCancelamento(items) {
  if (!Array.isArray(items) || !items.length) {
    return "nenhum";
  }

  return items.map((item) => String(item || "").trim()).filter(Boolean).join("; ") || "nenhum";
}

function registrarResumoCancelamento(resultado = {}) {
  const dados = resultado.resultado || {};
  const ultimaEtapa = dados.ultima_etapa || resultado.etapa || "não informada";
  const colocados = formatarListaResumoCancelamento(dados.dados_colocados);
  const pendentes = formatarListaResumoCancelamento(dados.dados_pendentes);

  log(`Cancelamento confirmado. Última função acessada: ${ultimaEtapa}.`, "error");
  log(`Dados já confirmados: ${colocados}.`);
  log(`Dados pendentes: ${pendentes}.`, "error");
}

function hideResumeBox(clearCheckpoint = true) {
  if (clearCheckpoint) {
    state.resumeCheckpoint = null;
  }

  const box = el("resumeBox");
  if (!box) {
    return;
  }

  box.classList.add("hidden");
  el("resumeTitle").textContent = "";
  el("resumeMessage").textContent = "";
}

// Mostra opção de retomada quando o backend retorna checkpoint após falha.
function showResumeBox(checkpoint, fallbackMessage = "") {
  if (!checkpoint || !checkpoint.resume_from) {
    hideResumeBox();
    return;
  }

  state.resumeCheckpoint = cloneCheckpoint(checkpoint);

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

// Abre o modal Fale Conosco e prepara os campos.
function openContactModal() {
  resetContactForm();
  openModal("contactModal");
  el("contactMatricula").focus();
}

function closeContactModal() {
  closeModal("contactModal");
  resetContactForm();
}

function openContactSuccessModal(message) {
  el("contactSuccessMessage").textContent =
    message || "Favor aguardar o retorno do atendimento interno.";
  openModal("contactSuccessModal");
}

function closeContactSuccessModal() {
  closeModal("contactSuccessModal");
}

const MODAL_IDS = [
  "contactModal",
  "contactSuccessModal",
  "pdfNameModal",
  "paymentFileModal",
  "historyModal",
  "aboutModal",
  "batchConfirmModal",
  "cancelFlowModal"
];

function modalEstaAberto(id) {
  const modal = el(id);
  return modal && !modal.classList.contains("hidden");
}

// Mantem o scroll preso no modal aberto, evitando que a tela de fundo role.
function sincronizarScrollDosModais() {
  const existeModalAberto = MODAL_IDS.some(modalEstaAberto);
  document.body.classList.toggle("modal-open", existeModalAberto);
}

function openModal(id) {
  const modal = el(id);

  if (!modal) {
    return;
  }

  modal.classList.remove("hidden");
  sincronizarScrollDosModais();
}

function closeModal(id) {
  const modal = el(id);

  if (!modal) {
    return;
  }

  modal.classList.add("hidden");
  sincronizarScrollDosModais();
}

function normalizarValorSobre(value, fallback = "--") {
  const texto = String(value ?? "").trim();
  return texto || fallback;
}

function renderAboutRows(rows) {
  const content = el("aboutContent");

  const linhas = rows
    .map(([label, value, wide = false]) => `
      <div class="about-row${wide ? " wide" : ""}">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(normalizarValorSobre(value))}</strong>
      </div>
    `)
    .join("");

  content.innerHTML = `
    <div class="about-summary">
      <strong>Embasa Pedidos SAP</strong>
      <p>
        Ferramenta desktop interna para automação assistida de pedidos,
        faturamento e geração de boleto no SAP GUI.
      </p>
    </div>

    <div class="about-grid">
      ${linhas}
    </div>

    <div class="about-section">
      <h3>Escopo operacional</h3>
      <ul>
        <li>Consulta e validação de cliente na XD03.</li>
        <li>Criação de pedido na VA01 e faturamento na VF01.</li>
        <li>Ajustes pós-faturamento em FB03/VF02 e geração pela F110.</li>
        <li>Progresso em tempo real, logs resumidos e retomada de fluxo.</li>
      </ul>
    </div>

    <div class="about-section">
      <h3>Responsável</h3>
      <p>
        API desenvolvida por Augusto Taylor para apoiar a Gerência de Tesouraria - FAFTA
        na padronização e aceleração do processo operacional SAP.
      </p>
    </div>
  `;
}

async function carregarDiagnosticoSobre() {
  renderAboutRows([
    ["Produto", "Embasa Pedidos SAP"],
    ["Versão da API", APP_VERSION],
    ["Status local", "Carregando diagnóstico..."],
    ["Integração", "SAP GUI Scripting local"]
  ]);

  try {
    if (!window.pywebview?.api?.obter_diagnostico) {
      renderAboutRows([
        ["Produto", "Embasa Pedidos SAP"],
        ["Versão da API", APP_VERSION],
        ["Status local", "Interface carregada em modo local"],
        ["Integração", "Backend pywebview indisponível nesta abertura"],
        ["Interface", "HTML/CSS/JS embarcado"],
        ["Execução", "Aguardando pywebview para diagnóstico completo", true]
      ]);
      return;
    }

    const diagnostico = await window.pywebview.api.obter_diagnostico();
    const app = diagnostico?.app || {};
    const cache = diagnostico?.cache || {};
    const history = diagnostico?.history || {};

    renderAboutRows([
      ["Produto", app.name || "Embasa Pedidos SAP"],
      ["Versão da API", app.version || APP_VERSION],
      ["Status local", "Backend conectado"],
      ["Integração", "pywebview + SAP GUI Scripting"],
      ["Empresa SAP", app.company_code || "EMBA"],
      ["Cache de clientes", `${cache.total || 0} registro(s)`],
      ["Histórico", `${history.total || 0} registro(s)`],
    ]);
  } catch (error) {
    renderAboutRows([
      ["Produto", "Embasa Pedidos SAP"],
      ["Versão da API", APP_VERSION],
      ["Status local", "Falha ao carregar diagnóstico"],
      ["Detalhe técnico", String(error), true],
    ]);
  }
}

function openAboutModal() {
  openModal("aboutModal");
  carregarDiagnosticoSobre();
}

function closeAboutModal() {
  closeModal("aboutModal");
}

function updateContactCharCount() {
  const descricao = el("contactDescricao").value || "";
  el("contactCharCount").textContent = `${descricao.length} / 600`;
}

function getSelectedContactFiles() {
  return Array.from(el("contactImagens").files || []);
}

function getContactFilesTotalBytes(files = getSelectedContactFiles()) {
  return files.reduce((total, file) => total + Number(file.size || 0), 0);
}

function updateContactUploadMeta(files = getSelectedContactFiles()) {
  const meta = el("contactUploadMeta");

  if (!files.length) {
    meta.textContent = "Nenhum arquivo selecionado.";
    return;
  }

  meta.textContent = `${files.length} arquivo(s) selecionado(s) • ${formatarBytes(getContactFilesTotalBytes(files))} de 15 MB`;
}

// Valida anexos escolhidos e renderiza a lista de arquivos selecionados.
function handleContactImages() {
  const input = el("contactImagens");
  const files = getSelectedContactFiles();
  const list = el("contactImageList");
  const totalBytes = getContactFilesTotalBytes(files);
  const invalidFile = files.find((file) => !isSupportedContactFile(file));

  if (invalidFile) {
    input.value = "";
    list.className = "image-list empty";
    list.textContent = "Nenhum arquivo adicionado.";
    updateContactUploadMeta([]);
    showContactFeedback(
      `Tipo de arquivo não suportado: ${invalidFile.name}. Use apenas JPG, JPEG ou PNG.`,
      false
    );
    return;
  }

  if (totalBytes > MAX_CONTACT_ATTACHMENT_BYTES) {
    input.value = "";
    list.className = "image-list empty";
    list.textContent = "Nenhum arquivo adicionado.";
    updateContactUploadMeta([]);
    showContactFeedback(
      "Tamanho de arquivo não suportado. Os anexos excedem o limite total de 15 MB.",
      false
    );
    return;
  }

  if (!files.length) {
    list.className = "image-list empty";
    list.textContent = "Nenhum arquivo adicionado.";
    updateContactUploadMeta([]);
    hideContactFeedback();
    return;
  }

  hideContactFeedback();
  list.className = "image-list";
  list.innerHTML = files
    .map(
      (file) => `
        <div class="image-pill">
          <strong>${escapeHtml(file.name)}</strong>
          <small>${formatarBytes(file.size)}</small>
        </div>
      `
    )
    .join("");
  updateContactUploadMeta(files);
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

// Valida o formulário de atendimento antes de chamar o backend.
function validarContatoAntesDeEnviar(payload) {
  if (!payload.matricula) {
    return "Informe a matrícula.";
  }

  if (!payload.nome) {
    return "Informe o nome.";
  }

  if (!payload.lotacao) {
    return "Informe a lotação.";
  }

  if (!payload.setor) {
    return "Informe o setor.";
  }

  if (!payload.descricao) {
    return "Informe a descrição do atendimento.";
  }

  if (payload.descricao.length > 600) {
    return "A descrição deve ter no máximo 600 caracteres.";
  }

  return "";
}

// Converte arquivo selecionado para base64 antes de enviar ao Python.
function fileToAttachment(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = () => {
      const result = String(reader.result || "");
      const commaIndex = result.indexOf(",");
      const contentBase64 = commaIndex >= 0 ? result.slice(commaIndex + 1) : "";

      resolve({
        name: file.name,
        size: Number(file.size || 0),
        type: file.type || "",
        content_base64: contentBase64
      });
    };

    reader.onerror = () => {
      reject(new Error(`Não foi possível ler o arquivo ${file.name}.`));
    };

    reader.readAsDataURL(file);
  });
}

async function coletarAnexosContato() {
  const files = getSelectedContactFiles();

  if (!files.length) {
    return [];
  }

  const invalidFile = files.find((file) => !isSupportedContactFile(file));

  if (invalidFile) {
    throw new Error(
      `Tipo de arquivo não suportado: ${invalidFile.name}. Use apenas JPG, JPEG ou PNG.`
    );
  }

  const totalBytes = getContactFilesTotalBytes(files);

  if (totalBytes > MAX_CONTACT_ATTACHMENT_BYTES) {
    throw new Error("Tamanho de arquivo não suportado. Os anexos excedem o limite total de 15 MB.");
  }

  return Promise.all(files.map(fileToAttachment));
}

// Envia o Fale Conosco via pywebview.api e exibe retorno ao usuário.
async function submitContactForm() {
  const submitButton = el("contactSubmitButton");
  const payload = {
    matricula: el("contactMatricula").value.trim(),
    nome: el("contactNome").value.trim(),
    lotacao: el("contactLotacao").value.trim(),
    setor: el("contactSetor").value.trim(),
    descricao: el("contactDescricao").value.trim(),
    imagens: []
  };

  const erroValidacao = validarContatoAntesDeEnviar(payload);

  if (erroValidacao) {
    showContactFeedback(erroValidacao, false);
    return;
  }

  try {
    submitButton.disabled = true;
    submitButton.textContent = "Enviando...";
    hideContactFeedback();

    payload.imagens = await coletarAnexosContato();

    const result = await window.pywebview.api.enviar_atendimento(payload);

    if (!result.ok) {
      showContactFeedback(result.msg, false);
      return;
    }

    closeContactModal();
    openContactSuccessModal(
      result.msg || "Seu pedido foi enviado. Favor aguardar o retorno do atendimento interno."
    );

    setTimeout(closeContactSuccessModal, 2400);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    showContactFeedback(`Falha ao enviar atendimento: ${message}`, false);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Enviar";
  }
}

// Limpa painel, logs, resultados e mensagens para iniciar novo fluxo.
function limparPainel() {
  pendingProgressEvents.length = 0;

  if (pendingProgressFrame) {
    window.cancelAnimationFrame(pendingProgressFrame);
    pendingProgressFrame = 0;
  }

  limparLogs();
  resetarEtapas();
  esconderResultado();
  hideResumeBox();
  state.currentPdfNameNotice = "";
  state.lastPdfNameNotice = "";
  state.currentPdfNoticeId = "";
  state.currentPaymentFileNotice = "";
  state.lastPaymentFileNotice = "";
  state.currentPaymentNoticeId = "";
  closePdfNameModal();
  closePaymentFileModal();
  limparMensagensValidacao();
  setStatus("Aguardando", "idle");
  closeLogsPopover();
}

// Fallback antigo: reproduz logs quando o backend nao envia tempo real.
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

// Monta o payload final que sera enviado para o Python.
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

function montarPayloadsLoteAtual() {
  const base = validarBaseAntesDoFluxo();

  if (!base) {
    return null;
  }

  const enderecoAtual = coletarEndereco();
  const enderecos = state.empreendimentosFila.map(cloneEndereco);

  if (!enderecos.length || enderecoTemConteudo(enderecoAtual)) {
    if (!validarEnderecoAntesDoFluxo(enderecoAtual)) {
      return null;
    }

    enderecos.push(cloneEndereco(enderecoAtual));
  }

  if (!enderecos.length) {
    mostrarErroCampo("enderecoEmpreendimento", "Adicione ao menos um empreendimento para gerar o boleto.");
    return null;
  }

  limparMensagensValidacao();

  return enderecos.map((endereco, index) => ({
    doc: base.docInfo.digitos,
    tipo: el("tipo").value,
    valor: el("valor").value,
    modo_valor: state.valueMode,
    endereco,
    _batch: {
      index: index + 1,
      total: enderecos.length,
      empreendimento: endereco.empreendimento
    }
  }));
}

// Bloqueia botões enquanto o fluxo SAP está executando.
function setFlowButtonsBusy(isBusy, mode = "start") {
  const submitButton = el("submitButton");
  const resumeButton = el("resumeButton");
  const cancelButton = el("cancelFlowButton");

  state.flowRunning = Boolean(isBusy);

  if (!isBusy) {
    state.cancelRequested = false;
  }

  submitButton.disabled = isBusy;
  submitButton.textContent = isBusy
    ? (mode === "batch" ? "Gerando lote..." : "Gerando...")
    : "Gerar Boleto";

  if (cancelButton) {
    cancelButton.disabled = !isBusy || state.cancelRequested;
    cancelButton.textContent = state.cancelRequested ? "Cancelando..." : "Cancelar criação";
  }

  if (resumeButton) {
    resumeButton.disabled = isBusy;
    if (isBusy && mode === "resume") {
      resumeButton.textContent = "Retomando...";
    } else if (isBusy && mode === "batch") {
      resumeButton.textContent = "Lote em andamento";
    } else {
      resumeButton.textContent = "Continuar do ponto de parada";
    }
  }
}

function openCancelFlowModal() {
  if (!state.flowRunning || state.cancelRequested) {
    return;
  }

  const message = el("cancelFlowMessage");
  const etapa = Number.isInteger(state.etapaAtual) ? ETAPAS[state.etapaAtual] : null;

  message.textContent = etapa
    ? `A criação está em ${etapa.codigo} - ${etapa.titulo}. O sistema vai cancelar no próximo ponto seguro para evitar erro no SAP.`
    : "A criação do boleto será interrompida no próximo ponto seguro para evitar erro no SAP.";

  openModal("cancelFlowModal");
}

function closeCancelFlowModal() {
  closeModal("cancelFlowModal");
}

async function confirmarCancelamentoFluxo() {
  if (!state.flowRunning || state.cancelRequested) {
    closeCancelFlowModal();
    return;
  }

  closeCancelFlowModal();
  state.cancelRequested = true;
  setFlowButtonsBusy(true, state.batchRunning ? "batch" : "start");
  setStatus("Cancelando", "error");
  log("Cancelamento solicitado pelo usuário. Aguardando próximo ponto seguro...", "error");
  openLogsPopover();

  try {
    const resposta = await window.pywebview.api.cancelar_fluxo();

    if (resposta?.msg) {
      log(resposta.msg, resposta.ok ? "" : "error");
    }
  } catch (error) {
    log(`Não foi possível solicitar cancelamento ao backend: ${error}`, "error");
  }
}

function aguardarConfirmacaoBoletoLote(payload, resultado, proximoIndex, total) {
  return new Promise((resolve) => {
    const modal = el("batchConfirmModal");
    const message = el("batchConfirmMessage");
    const continueButton = el("batchConfirmContinue");
    const pauseButton = el("batchConfirmPause");
    const nome = payload.endereco?.empreendimento || `empreendimento ${proximoIndex}`;
    const proximoNome = state.empreendimentosFila[proximoIndex]?.empreendimento || `empreendimento ${proximoIndex + 1}`;
    const docFat = resultado?.resultado?.doc_fat || resultado?.resultado?.faturamento || "--";

    message.textContent =
      `Boleto do empreendimento "${nome}" finalizado. Doc. fat: ${docFat}. ` +
      `Confirme para seguir para "${proximoNome}" (${proximoIndex + 1} de ${total}).`;

    const finalizar = (continuar) => {
      closeModal("batchConfirmModal");
      continueButton.onclick = null;
      pauseButton.onclick = null;
      resolve(continuar);
    };

    continueButton.onclick = () => finalizar(true);
    pauseButton.onclick = () => finalizar(false);
    openModal("batchConfirmModal");
  });
}

function montarCheckpointClienteParaProximo(payload, resultado) {
  const cliente = resultado?.resultado?.cliente;

  if (!cliente) {
    return null;
  }

  return {
    resume_from: "VA01",
    contexto: {
      cliente,
      nome_cliente: resultado?.resultado?.nome_cliente,
      documento: payload.doc,
      tipo_documento: payload.doc.length === 14 ? "CNPJ" : "CPF",
      valor: payload.valor
    }
  };
}

async function executarLoteEmpreendimentos(payloads) {
  state.batchRunning = true;
  setFlowButtonsBusy(true, "batch");
  hideResumeBox();

  let checkpointCliente = null;

  try {
    for (let index = 0; index < payloads.length; index += 1) {
      const payload = payloads[index];
      const total = payloads.length;
      const nome = payload.endereco?.empreendimento || `Empreendimento ${index + 1}`;
      const resume = Boolean(index > 0 && checkpointCliente);
      const resumoEndereco = formatarEnderecoResumo(payload.endereco || {});

      window.resetarProgresso();
      log(`Iniciando empreendimento ${index + 1}/${total}: ${nome}.`);
      log(`Endereço do empreendimento: ${resumoEndereco}.`);
      setStatus(`Processando ${index + 1}/${total}`, "running");
      processarEtapaTempoReal(
        "XD03",
        resume ? "concluido" : "processando",
        resume
          ? `Cliente já validado para o lote. Seguindo com ${nome}.`
          : `Validando cliente para o lote: ${nome}.`,
        resume ? 100 : 8
      );

      const resultado = await executarFluxo(payload, {
        resume,
        checkpoint: checkpointCliente,
        manageButtons: false,
        resetProgress: false
      });

      if (!resultado || !resultado.ok) {
        if (resultado?.cancelado) {
          log(`Lote cancelado no empreendimento ${index + 1}/${total}: ${nome}.`, "error");
          setStatus("Cancelado", "error");
        } else {
          log(`Lote pausado no empreendimento ${index + 1}/${total}.`, "error");
          setStatus("Falha no processamento", "error");
        }
        return;
      }

      log(`Empreendimento concluído ${index + 1}/${total}: ${nome}.`);
      log(`Resultado ${nome}: Cliente ${resultado?.resultado?.cliente || "--"} | Doc. fat ${resultado?.resultado?.doc_fat || resultado?.resultado?.faturamento || "--"} | Boleto ${resultado?.resultado?.boleto || resultado?.resultado?.identificacao_pagamento || "--"}.`);
      checkpointCliente = montarCheckpointClienteParaProximo(payload, resultado) || checkpointCliente;

      if (index < payloads.length - 1) {
        const proximoNome = payloads[index + 1]?.endereco?.empreendimento || `Empreendimento ${index + 2}`;
        setStatus(`Aguardando confirmação ${index + 1}/${total}`, "idle");
        log(`Aguardando confirmação do boleto de ${nome} para seguir para ${proximoNome}.`);

        const continuar = await aguardarConfirmacaoBoletoLote(
          payload,
          resultado,
          index + 1,
          total
        );

        if (!continuar) {
          log(`Lote pausado pelo usuário após o empreendimento: ${nome}.`);
          setStatus("Lote pausado", "idle");
          return;
        }

        log(`Confirmação recebida. Próximo empreendimento: ${proximoNome}.`);
      }
    }

    limparFilaEmpreendimentos();
    setStatus("Lote concluído", "success");
    log("Todos os empreendimentos do lote foram processados.");
  } finally {
    state.batchRunning = false;
    setFlowButtonsBusy(false);
  }
}

// Chama a API Python para iniciar ou retomar o fluxo SAP.
async function executarFluxo(payload, options = {}) {
  const {
    resume = false,
    checkpoint = null,
    manageButtons = true,
    resetProgress = true
  } = options;
  const resumeCheckpoint = resume
    ? cloneCheckpoint(checkpoint || state.resumeCheckpoint)
    : null;

  if (!resume) {
    hideResumeBox();
    if (resetProgress) {
      window.resetarProgresso();
    }
    setStatus("Processando", "running");
  } else {
    if (!resumeCheckpoint || !resumeCheckpoint.resume_from) {
      log("Não foi possível retomar: checkpoint ausente ou inválido.", "error");
      setStatus("Falha no processamento", "error");
      openLogsPopover();
      return { ok: false, msg: "Checkpoint ausente ou inválido." };
    }

    hideResumeBox(false);
    setStatus("Retomando", "running");
    log(`Retomando a partir de ${resumeCheckpoint.resume_from}.`);
  }

  if (manageButtons) {
    setFlowButtonsBusy(true, resume ? "resume" : "start");
  }

  try {
    const dados = {
      ...payload,
      _resume_checkpoint: resumeCheckpoint
    };

    const res = await window.pywebview.api.gerar_boleto(dados);
    const tempoReal = Boolean(res && res.tempo_real);

    if (!res.ok) {
      if (res.cancelado) {
        registrarResumoCancelamento(res);
        preencherResultado(res.resultado || {});
        showResumeBox(
          res.checkpoint,
          "Processo cancelado. Confira a tela do SAP e continue somente se estiver seguro retomar deste ponto."
        );
        setStatus("Cancelado", "error");
        openLogsPopover();
        return res;
      }

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
      return res;
    }

    hideResumeBox();

    if (!tempoReal) {
      await reproduzirFluxo(res.logs || [], { finalStatus: "done" });
    }

    preencherResultado(res.resultado || {});
    setStatus("Concluído", "success");
    return res;
  } catch (error) {
    setStatus("Falha no processamento", "error");
    log(`Falha ao comunicar com o backend: ${error}`, "error");
    openLogsPopover();
    return { ok: false, msg: String(error) };
  } finally {
    if (manageButtons) {
      setFlowButtonsBusy(false);
    }
    closeCancelFlowModal();
  }
}

// Handler principal do botao Gerar Boleto.
async function gerarBoleto() {
  const payloads = montarPayloadsLoteAtual();

  if (!payloads) {
    return;
  }

  if (payloads.length > 1) {
    await executarLoteEmpreendimentos(payloads);
    return;
  }

  await executarFluxo(payloads[0], { resume: false });
}

// Continua a automacao a partir do checkpoint salvo.
async function retomarFluxo() {
  const checkpoint = cloneCheckpoint(state.resumeCheckpoint);

  if (!checkpoint || !checkpoint.resume_from) {
    log("Não foi possível retomar: checkpoint ausente ou inválido.", "error");
    openLogsPopover();
    return;
  }

  const payload = montarPayloadAtual();

  if (!payload) {
    return;
  }

  await executarFluxo(payload, { resume: true, checkpoint });
}

document.addEventListener("click", (event) => {
  const menu = el("valueMenu");
  const valueButton = el("valueModeButton");
  const tipoMenu = el("tipoMenu");
  const tipoButton = el("tipoButton");
  const popover = el("logPopover");
  const balloon = el("logBalloon");
  const card = el("contactCard");
  const modal = el("contactModal");
  const cancelModal = el("cancelFlowModal");

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
    !modal.classList.contains("hidden") &&
    card &&
    !card.contains(event.target) &&
    event.target.classList.contains("contact-backdrop")
  ) {
    closeContactModal();
  }

  if (
    cancelModal &&
    !cancelModal.classList.contains("hidden") &&
    event.target.classList.contains("contact-backdrop")
  ) {
    closeCancelFlowModal();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") {
    return;
  }

  if (modalEstaAberto("aboutModal")) {
    closeAboutModal();
    return;
  }

  if (modalEstaAberto("contactModal")) {
    closeContactModal();
    return;
  }

  if (modalEstaAberto("contactSuccessModal")) {
    closeContactSuccessModal();
    return;
  }

  if (modalEstaAberto("pdfNameModal")) {
    if (state.currentPdfNoticeId) {
      return;
    }

    closePdfNameModal();
    return;
  }

  if (modalEstaAberto("paymentFileModal")) {
    if (state.currentPaymentNoticeId) {
      return;
    }

    closePaymentFileModal();
    return;
  }

  if (modalEstaAberto("historyModal")) {
    closeHistoryModal();
    return;
  }

  if (modalEstaAberto("cancelFlowModal")) {
    closeCancelFlowModal();
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
registrarCepAutocomplete();
updateContactCharCount();
handleContactImages();
setEmpreendimentoAberto(false);
setSemNumero(false);
setSemCep(false);
renderizarFilaEmpreendimentos();
limparPainel();
atualizarRodapeInfo();
window.setInterval(atualizarRodapeInfo, 1000);
