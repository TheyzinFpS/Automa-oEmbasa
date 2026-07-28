const MONITOR_STAGES = {
  boletos: [
  // Ordem visual das etapas exibidas no painel de andamento.
  { id: "XD03", codigo: "XD03", titulo: "Buscar cliente" },
  { id: "VA01", codigo: "VA01", titulo: "Criar pedido" },
  { id: "VF01", codigo: "VF01", titulo: "Criar doc.fat." },
  { id: "FB03", codigo: "FB03", titulo: "Ajustar contábil" },
  { id: "VF02_RESALVAR", codigo: "VF02", titulo: "Salvar faturamento" },
  { id: "F110", codigo: "F110", titulo: "Gerar pagamento" }
  ],
  cliente: [
    { id: "XD01", codigo: "XD01", titulo: "Criar cliente" }
  ],
  multa: [
    { id: "XD03", codigo: "XD03", titulo: "Buscar cliente" },
    { id: "VA01", codigo: "VA01", titulo: "Criar pedido" },
    { id: "VF01", codigo: "VF01", titulo: "Criar doc.fat." },
    { id: "FB03", codigo: "FB03", titulo: "Ajustar contabil" },
    { id: "VF02_RESALVAR", codigo: "VF02", titulo: "Salvar faturamento" },
    { id: "F110", codigo: "F110", titulo: "Gerar pagamento" }
  ],
  setor: [
    { id: "XD01", codigo: "XD01", titulo: "Criar setor" }
  ],
  extratos: [
    { id: "BE", codigo: "BE", titulo: "Baixar extratos" }
  ]
};

let ETAPAS = MONITOR_STAGES.boletos;

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
  multa_contratual: "Multa Contratual",
  agua_esgoto: "Água + Esgoto"
};

const TRATAMENTOS_CADASTRO = {
  auto: "Automático",
  Empresa: "Empresa",
  Sr: "Sr",
  Sra: "Sra"
};

const SETOR_MODELOS = {
  AE: { titulo: "Viabilidade", vendas: "1055", grupo: "DM" },
  AG: { titulo: "Água", vendas: "1055", grupo: "DM" },
  EG: { titulo: "Esgoto", vendas: "1070", grupo: "ME" },
  MC: { titulo: "Multa Contratual", vendas: "1010", grupo: "CAB" }
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
const APP_VERSION = "1.4.53";
const CEP_API_BASE_URL = "https://viacep.com.br/ws";
const CEP_DEBOUNCE_MS = 450;
const CEP_UF_PERMITIDA = "BA";
const SUPPORTED_CONTACT_EXTENSIONS = new Set([".jpg", ".jpeg", ".png"]);
const SUPPORTED_CONTACT_MIME_TYPES = new Set(["image/jpeg", "image/png"]);
const THEME_STORAGE_KEY = "embasa-theme";
const CLIENT_DRAFT_STORAGE_KEY = "embasa-client-drafts";
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
const SIMPLE_NOTICE_PREFIX = "SIMPLE_NOTICE::";
const EXTRATO_RESULT_NOTICE_PREFIX = "EXTRATO_RESULT::";
const MESES_EXTRATO = {
  "01": "Janeiro",
  "02": "Fevereiro",
  "03": "Marco",
  "04": "Abril",
  "05": "Maio",
  "06": "Junho",
  "07": "Julho",
  "08": "Agosto",
  "09": "Setembro",
  "10": "Outubro",
  "11": "Novembro",
  "12": "Dezembro"
};
const MESES_EXTRATO_SIGLA = {
  "01": "JAN",
  "02": "FEV",
  "03": "MAR",
  "04": "ABR",
  "05": "MAI",
  "06": "JUN",
  "07": "JUL",
  "08": "AGO",
  "09": "SET",
  "10": "OUT",
  "11": "NOV",
  "12": "DEZ"
};
const EXTRATO_PASTA_BASE_PADRAO = "";
const NAVEGADORES_EXTRATO = {
  opera: "Opera",
  chrome: "Chrome",
  edge: "Microsoft Edge"
};
const EXTRATO_CAIXA_PASSOS = [
  "Saldo e Extratos",
  "Extrato Individualizado de Contas",
  "Selecionar conta",
  "Selecionar mes e ano",
  "Pesquisar",
  "Exportar PDF",
  "Salvar na pasta CEF"
];
// Mapeia eventos vindos do Python para a etapa visual correspondente.
function criarDisplayStageMap(etapas = ETAPAS) {
  const map = new Map();

  etapas.forEach((etapa, index) => {
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
}

let DISPLAY_STAGE_MAP = criarDisplayStageMap();

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
  clientesFila: [],
  clienteQueueSeq: 0,
  batchConfirmTransitionTimer: 0,
  rascunhosClientes: [],
  rascunhoClienteEditando: "",
  rascunhosClientesCarregados: false,
  rascunhosBackendSincronizado: false,
  batchRunning: false,
  flowRunning: false,
  cancelRequested: false,
  currentPdfNameNotice: "",
  lastPdfNameNotice: "",
  currentPdfNoticeId: "",
  currentPdfRequiresConfirmation: false,
  currentPaymentFileNotice: "",
  lastPaymentFileNotice: "",
  paymentFileCopiedTimer: 0,
  operationalNoticeQueue: [],
  simpleOperationalToastTimer: null,
  pendingSapAction: null,
  pendingSapPayload: null,
  clientRegistrationSource: "",
  currentWorkspace: "boletos",
  monitorMode: "boletos",
  sidebarOpen: false,
  cadastroCepLookupTimer: 0,
  cadastroCepLookupSeq: 0,
  cadastroCepLookupController: null,
  historicoItens: [],
  historicoSelecionado: null,
  extratoResultados: []
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
  enderecoCidade: { messageId: "enderecoCidadeError", accordion: true },
  multaDoc: { messageId: "multaDocError" },
  multaValor: { messageId: "multaFormError" },
  multaContrato: { messageId: "multaFormError" },
  multaValidade: { messageId: "multaValidadeError", focusId: "multaValidade30" }
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

function formatarCepCadastro(elm) {
  elm.value = formatarCepValue(elm.value);
  agendarConsultaCepCadastro();
}

function formatarUfCadastro(elm) {
  elm.value = String(elm.value || "")
    .replace(/[^A-Za-z]/g, "")
    .toUpperCase()
    .slice(0, 2);
}

function formatarTelefoneCadastro(elm) {
  const digitos = String(elm.value || "").replace(/\D/g, "").slice(0, 11);

  if (digitos.length <= 2) {
    elm.value = digitos ? `(${digitos}` : "";
    return;
  }

  if (digitos.length <= 6) {
    elm.value = `(${digitos.slice(0, 2)}) ${digitos.slice(2)}`;
    return;
  }

  if (digitos.length <= 10) {
    elm.value = `(${digitos.slice(0, 2)}) ${digitos.slice(2, 6)}-${digitos.slice(6)}`;
    return;
  }

  elm.value = `(${digitos.slice(0, 2)}) ${digitos.slice(2, 7)}-${digitos.slice(7)}`;
}

function cancelarConsultaCepCadastroPendente() {
  if (state.cadastroCepLookupTimer) {
    window.clearTimeout(state.cadastroCepLookupTimer);
    state.cadastroCepLookupTimer = 0;
  }

  if (state.cadastroCepLookupController) {
    state.cadastroCepLookupController.abort();
    state.cadastroCepLookupController = null;
  }
}

function setCadastroCepLoading(isLoading) {
  const input = el("clienteCadastroCep");

  if (!input) {
    return;
  }

  input.classList.toggle("is-loading", Boolean(isLoading));
  input.setAttribute("aria-busy", String(Boolean(isLoading)));
}

async function buscarCepCadastroAutomaticamente(cep) {
  const requestId = ++state.cadastroCepLookupSeq;

  if (state.cadastroCepLookupController) {
    state.cadastroCepLookupController.abort();
  }

  state.cadastroCepLookupController = new AbortController();
  setCadastroCepLoading(true);

  try {
    const resultado = await consultarCepViaCep(cep, state.cadastroCepLookupController.signal);

    if (requestId !== state.cadastroCepLookupSeq) {
      return;
    }

    if (!resultado.ok) {
      showCadastroClienteFeedback(resultado.message, false, "clienteCadastroCep");
      return;
    }

    const data = resultado.data;
    preencherCampoCadastroCep("clienteCadastroRua", data.logradouro);
    preencherCampoCadastroCep("clienteCadastroBairro", data.bairro);
    preencherCampoCadastroCep("clienteCadastroCidade", sanitizarCidade(data.localidade || "").trim());
    preencherCampoCadastroCep("clienteCadastroEstado", String(data.uf || "").trim().toUpperCase());
    hideCadastroClienteFeedback();
  } catch (error) {
    if (error?.name !== "AbortError") {
      showCadastroClienteFeedback("Erro de conexão ao consultar o CEP. Preencha o endereço manualmente.", false, "clienteCadastroCep");
    }
  } finally {
    if (requestId === state.cadastroCepLookupSeq) {
      setCadastroCepLoading(false);
      state.cadastroCepLookupController = null;
    }
  }
}

function preencherCampoCadastroCep(fieldId, value) {
  const input = el(fieldId);
  const texto = String(value || "").trim();

  if (!input || !texto || String(input.value || "").trim()) {
    return;
  }

  input.value = texto;
}

function agendarConsultaCepCadastro(options = {}) {
  const { immediate = false, mostrarIncompleto = false } = options;
  cancelarConsultaCepCadastroPendente();

  const cep = obterDigitosCep(el("clienteCadastroCep")?.value || "");

  if (!cep) {
    return;
  }

  if (cep.length < 8) {
    if (mostrarIncompleto) {
      showCadastroClienteFeedback("CEP incompleto. Informe 8 dígitos.", false, "clienteCadastroCep");
    }
    return;
  }

  const executar = () => buscarCepCadastroAutomaticamente(cep);

  if (immediate) {
    executar();
    return;
  }

  state.cadastroCepLookupTimer = window.setTimeout(executar, CEP_DEBOUNCE_MS);
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

function formatarValorDigitadoSemLimite(valor) {
  const digitos = limparValor(valor);

  if (!digitos) {
    return "";
  }

  return formatarCentavosParaMoeda(Number(digitos));
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

function cloneEnderecoParcial(endereco = {}) {
  const semCep = Boolean(endereco.sem_cep) || String(endereco.cep || "").trim().toUpperCase() === "SEM CEP";

  return {
    empreendimento: String(endereco.empreendimento || "").trim(),
    rua: String(endereco.rua || "").trim(),
    numero: String(endereco.numero || "").trim(),
    cep: semCep ? "SEM CEP" : formatarCepValue(endereco.cep || ""),
    sem_cep: semCep,
    bairro: String(endereco.bairro || "").trim(),
    complemento: String(endereco.complemento || "").trim(),
    cidade: sanitizarCidade(endereco.cidade || "").trim(),
    estado: String(endereco.estado || "BA").trim().toUpperCase() || "BA"
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
  el("enderecoNumero").value = "";
  el("enderecoCep").value = "";
  el("enderecoBairro").value = "";
  el("enderecoComplemento").value = "";
  el("enderecoCidade").value = "";
  el("enderecoEstado").value = "BA";
  setSemNumero(false);
  setSemCep(false);
  limparMensagensValidacao();
}

function preencherCamposEndereco(endereco = {}) {
  const dados = cloneEnderecoParcial(endereco || {});
  const numero = String(dados.numero || "").trim();
  const semNumero = numero.toUpperCase() === "S/N";
  const semCep = Boolean(dados.sem_cep) || String(dados.cep || "").trim().toUpperCase() === "SEM CEP";

  cancelarConsultaCepPendente();
  setCepLookupStatus("", null, "");
  resetarEnderecoAutoCep();

  el("enderecoEmpreendimento").value = dados.empreendimento || "";
  el("enderecoRua").value = dados.rua || "";
  setSemNumero(semNumero);
  if (!semNumero) {
    el("enderecoNumero").value = numero;
  }
  setSemCep(semCep);
  if (!semCep) {
    el("enderecoCep").value = formatarCepValue(dados.cep || "");
  }
  el("enderecoBairro").value = dados.bairro || "";
  el("enderecoComplemento").value = dados.complemento || "";
  el("enderecoCidade").value = dados.cidade || "";
  el("enderecoEstado").value = dados.estado || "BA";
  limparMensagensValidacao();
}

function limparFormularioCriacaoBoleto() {
  atualizarDocumentoUI("");
  el("tipo").value = "";
  el("tipoButtonText").textContent = TIPOS_SOLICITACAO[""];
  state.lastTipo = "";
  state.valueMode = "auto";
  atualizarModoValorUI();
  limparCamposEndereco();
  limparFilaEmpreendimentos();
  state.rascunhoClienteEditando = "";
  setEmpreendimentoAberto(false);
  fecharMenuTipo();
  fecharMenuValor();
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

function getTipoSolicitacaoLabel(tipo) {
  return TIPOS_SOLICITACAO[tipo] || tipo || "Nao informado";
}

function coletarEnderecosParaExecucao() {
  const enderecoAtual = coletarEndereco();
  const enderecos = [];

  for (let index = 0; index < state.empreendimentosFila.length; index += 1) {
    const enderecoFila = cloneEnderecoParcial(state.empreendimentosFila[index]);

    if (!validarEnderecoAntesDoFluxo(enderecoFila)) {
      state.empreendimentosFila.splice(index, 1);
      preencherCamposEndereco(enderecoFila);
      renderizarFilaEmpreendimentos();
      setEmpreendimentoAberto(true);
      validarEnderecoAntesDoFluxo(enderecoFila);
      setStatus("Revise o empreendimento", "error");
      return null;
    }

    enderecos.push(cloneEndereco(enderecoFila));
  }

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

  return enderecos;
}

function coletarEnderecosParciaisCliente() {
  const enderecos = state.empreendimentosFila.map(cloneEnderecoParcial);
  const atual = cloneEnderecoParcial(coletarEndereco());

  if (enderecoTemConteudo(atual) || !enderecos.length) {
    enderecos.push(atual);
  }

  return enderecos.filter(enderecoTemConteudo);
}

function resumoClienteFila(item = {}) {
  const enderecos = Array.isArray(item.enderecos) ? item.enderecos : [];
  const primeiro = enderecos[0] || {};
  const total = enderecos.length;
  const tipoLabel = item.tipo_label || getTipoSolicitacaoLabel(item.tipo);
  const titulo = primeiro.empreendimento || (total > 1 ? `${total} empreendimentos` : "Sem empreendimento");

  return {
    doc: item.doc_formatado || formatarDocumentoResumo(item.doc),
    tipoLabel,
    titulo,
    detalhe: `${tipoLabel} | ${total || 0} empreendimento${total === 1 ? "" : "s"}`,
    endereco: primeiro ? formatarEnderecoResumo(primeiro) : ""
  };
}

function montarClienteAtualParaFila() {
  const base = validarBaseAntesDoFluxo();

  if (!base) {
    return null;
  }

  const enderecos = coletarEnderecosParaExecucao();

  if (!enderecos) {
    return null;
  }

  limparMensagensValidacao();

  return {
    id: `fila_${Date.now()}_${base.docInfo.digitos.slice(-6)}`,
    doc: base.docInfo.digitos,
    doc_formatado: base.docInfo.formatado,
    tipo: base.tipo,
    tipo_label: getTipoSolicitacaoLabel(base.tipo),
    valor: el("valor").value,
    modo_valor: state.valueMode,
    enderecos,
    status: "pronto",
    criado_em: new Date().toISOString()
  };
}

function montarRascunhoClienteAtual() {
  const docInfo = analisarDocumento(el("doc").value);

  if (![11, 14].includes(docInfo.digitos.length)) {
    mostrarErroCampo("doc", "Informe CPF ou CNPJ completo para salvar o rascunho.");
    return null;
  }

  limparMensagemCampo("doc");

  return {
    id: state.rascunhoClienteEditando || "",
    doc: docInfo.digitos,
    doc_formatado: docInfo.formatado,
    tipo: el("tipo").value,
    tipo_label: getTipoSolicitacaoLabel(el("tipo").value),
    valor: el("valor").value,
    modo_valor: state.valueMode,
    enderecos: coletarEnderecosParciaisCliente(),
    status: "rascunho"
  };
}

function normalizarChaveFila(valor) {
  return String(valor || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, " ");
}

function chaveEnderecoFila(endereco = {}) {
  return [
    endereco.empreendimento,
    endereco.rua,
    endereco.numero,
    endereco.cep,
    endereco.bairro,
    endereco.cidade,
    endereco.estado
  ].map(normalizarChaveFila).join("|");
}

function garantirIdClienteFila(cliente = {}) {
  if (!cliente._queue_id) {
    state.clienteQueueSeq += 1;
    cliente._queue_id = `cliente-${Date.now()}-${state.clienteQueueSeq}`;
  }

  return cliente._queue_id;
}

function resolverInicioRetomadaFilaClientes(contexto = {}) {
  const queueId = String(contexto.queueId || "").trim();
  const enderecoKey = String(contexto.enderecoKey || "").trim();
  let startClientIndex = -1;

  if (queueId) {
    startClientIndex = state.clientesFila.findIndex(
      (cliente) => String(cliente?._queue_id || "") === queueId
    );
  }

  if (startClientIndex < 0) {
    startClientIndex = Math.max(0, Number(contexto.clienteIndex) || 0);
  }

  startClientIndex = Math.min(startClientIndex, Math.max(state.clientesFila.length - 1, 0));

  const cliente = state.clientesFila[startClientIndex] || {};
  const enderecos = Array.isArray(cliente.enderecos) ? cliente.enderecos : [];
  let startPayloadIndex = enderecoKey
    ? enderecos.findIndex((endereco) => chaveEnderecoFila(endereco) === enderecoKey)
    : -1;

  if (startPayloadIndex < 0) {
    startPayloadIndex = Math.max(0, Number(contexto.payloadIndex) || 0);
  }

  startPayloadIndex = Math.min(startPayloadIndex, Math.max(enderecos.length - 1, 0));

  return { startClientIndex, startPayloadIndex };
}

function removerPayloadConcluidoDaFilaClientes(payload = {}) {
  const contexto = payload._queue_context || {};
  const queueId = String(contexto.queueId || "").trim();
  const enderecoKey = String(contexto.enderecoKey || chaveEnderecoFila(payload.endereco || {})).trim();
  let clienteIndex = -1;

  if (queueId) {
    clienteIndex = state.clientesFila.findIndex(
      (cliente) => String(cliente?._queue_id || "") === queueId
    );
  }

  if (clienteIndex < 0) {
    const doc = limparDocumento(payload.doc || "");
    clienteIndex = state.clientesFila.findIndex((cliente) => (
      limparDocumento(cliente?.doc || "") === doc &&
      String(cliente?.tipo || "") === String(payload.tipo || "")
    ));
  }

  if (clienteIndex < 0) {
    return;
  }

  const cliente = state.clientesFila[clienteIndex];
  const enderecos = Array.isArray(cliente.enderecos) ? cliente.enderecos : [];
  let enderecoIndex = enderecos.findIndex((endereco) => chaveEnderecoFila(endereco) === enderecoKey);

  if (enderecoIndex < 0) {
    enderecoIndex = Math.min(
      Math.max(0, Number(contexto.payloadIndex) || 0),
      Math.max(enderecos.length - 1, 0)
    );
  }

  if (enderecos.length > 1 && enderecoIndex >= 0) {
    enderecos.splice(enderecoIndex, 1);
  } else {
    state.clientesFila.splice(clienteIndex, 1);
  }

  renderizarFilaClientes();
}

function removerPayloadConcluidoDaFilaEmpreendimentos(payload = {}) {
  const enderecoKey = chaveEnderecoFila(payload.endereco || {});
  const index = state.empreendimentosFila.findIndex(
    (endereco) => chaveEnderecoFila(endereco) === enderecoKey
  );

  if (index >= 0) {
    state.empreendimentosFila.splice(index, 1);
    renderizarFilaEmpreendimentos();
  }
}

function renderizarFilaClientes() {
  const queue = el("clienteQueue");

  if (!queue) {
    return;
  }

  const fila = state.clientesFila || [];
  const rascunhos = state.rascunhosClientes || [];

  if (!fila.length && !rascunhos.length) {
    queue.className = "client-queue empty";
    queue.textContent = "Nenhum CPF/CNPJ na fila e nenhum rascunho salvo.";
    return;
  }

  const filaHtml = fila.map((item, index) => {
    const resumo = resumoClienteFila(item);

    return `
      <div class="client-queue-item ready">
        <div>
          <span class="client-queue-badge">Fila ${index + 1}</span>
          <strong>${escapeHtml(resumo.doc)} - ${escapeHtml(resumo.titulo)}</strong>
          <small>${escapeHtml(resumo.detalhe)}</small>
          <small>${escapeHtml(resumo.endereco)}</small>
        </div>
        <div class="client-queue-actions">
          <button type="button" onclick="editarClienteFila(${index})">Editar</button>
          <button type="button" onclick="removerClienteDaFila(${index})">Remover</button>
        </div>
      </div>
    `;
  }).join("");

  const rascunhosHtml = rascunhos.map((item) => {
    const resumo = resumoClienteFila(item);

    return `
      <div class="client-queue-item draft">
        <div>
          <span class="client-queue-badge">Rascunho</span>
          <strong>${escapeHtml(resumo.doc)} - ${escapeHtml(resumo.titulo)}</strong>
          <small>${escapeHtml(resumo.detalhe)}</small>
          <small>${escapeHtml(resumo.endereco || "Dados incompletos salvos.")}</small>
        </div>
        <div class="client-queue-actions">
          <button type="button" onclick="carregarRascunhoCliente(${htmlJsArg(item.id)})">Editar</button>
          <button type="button" onclick="excluirRascunhoCliente(${htmlJsArg(item.id)})">Excluir</button>
        </div>
      </div>
    `;
  }).join("");

  queue.className = "client-queue";
  queue.innerHTML = `
    ${filaHtml ? `<div class="client-queue-section"><span>Clientes prontos</span>${filaHtml}</div>` : ""}
    ${rascunhosHtml ? `<div class="client-queue-section"><span>Rascunhos salvos</span>${rascunhosHtml}</div>` : ""}
  `;
}

async function adicionarClienteNaFila() {
  const cliente = montarClienteAtualParaFila();

  if (!cliente) {
    return;
  }

  const draftId = state.rascunhoClienteEditando;
  garantirIdClienteFila(cliente);
  state.clientesFila.push(cliente);
  state.rascunhoClienteEditando = "";
  renderizarFilaClientes();
  log(`Cliente adicionado a fila: ${cliente.doc_formatado || cliente.doc} - ${cliente.tipo_label}.`);
  setStatus("Cliente adicionado", "success");
  limparFormularioCriacaoBoleto();
  setEmpreendimentoAberto(true);

  if (draftId) {
    await excluirRascunhoCliente(draftId, { silent: true });
  }
}

function removerClienteDaFila(index) {
  if (index < 0 || index >= state.clientesFila.length) {
    return;
  }

  const [removido] = state.clientesFila.splice(index, 1);
  renderizarFilaClientes();
  log(`Cliente removido da fila: ${removido?.doc_formatado || removido?.doc || "--"}.`);
}

function limparFilaClientes() {
  state.clientesFila = [];
  renderizarFilaClientes();
}

function carregarClienteNoFormulario(item = {}, options = {}) {
  const enderecos = Array.isArray(item.enderecos)
    ? item.enderecos.map(cloneEnderecoParcial)
    : [];

  atualizarDocumentoUI(item.doc || "");
  el("tipo").value = item.tipo || "";
  state.valueMode = item.modo_valor || "auto";
  atualizarModoValorUI();
  atualizarTipo();

  if (item.valor) {
    el("valor").value = item.valor;
  }

  if (enderecos.length) {
    preencherCamposEndereco(enderecos[0]);
  state.empreendimentosFila = enderecos.slice(1).map(cloneEnderecoParcial);
  } else {
    limparCamposEndereco();
    state.empreendimentosFila = [];
  }

  renderizarFilaEmpreendimentos();
  state.rascunhoClienteEditando = options.rascunho ? String(item.id || "") : "";
  setEmpreendimentoAberto(true);
  showBoletoWorkspace({ status: false });
  setStatus(options.rascunho ? "Rascunho carregado" : "Cliente carregado", "idle");
  window.setTimeout(() => el("enderecoEmpreendimento")?.focus(), 180);
}

function editarClienteFila(index) {
  if (index < 0 || index >= state.clientesFila.length) {
    return;
  }

  const [item] = state.clientesFila.splice(index, 1);
  renderizarFilaClientes();
  carregarClienteNoFormulario(item);
}

function carregarRascunhosLocal() {
  try {
    return JSON.parse(localStorage.getItem(CLIENT_DRAFT_STORAGE_KEY) || "[]");
  } catch (error) {
    return [];
  }
}

function salvarRascunhosLocal(itens) {
  try {
    localStorage.setItem(CLIENT_DRAFT_STORAGE_KEY, JSON.stringify(itens || []));
  } catch (error) {
    // ignora falhas de armazenamento local
  }
}

async function carregarRascunhosClientes() {
  try {
    if (window.pywebview?.api?.listar_rascunhos_clientes) {
      const resposta = await window.pywebview.api.listar_rascunhos_clientes();

      if (resposta?.ok) {
        state.rascunhosClientes = resposta.itens || [];
        state.rascunhosClientesCarregados = true;
        state.rascunhosBackendSincronizado = true;
        renderizarFilaClientes();
        return;
      }
    }
  } catch (error) {
    log(`Nao foi possivel carregar rascunhos: ${error}`, "error");
  }

  state.rascunhosClientes = carregarRascunhosLocal();
  state.rascunhosClientesCarregados = true;
  renderizarFilaClientes();

  window.setTimeout(() => {
    if (!state.rascunhosBackendSincronizado && window.pywebview?.api?.listar_rascunhos_clientes) {
      carregarRascunhosClientes();
    }
  }, 900);
}

async function salvarRascunhoCliente() {
  const rascunho = montarRascunhoClienteAtual();

  if (!rascunho) {
    return;
  }

  try {
    if (window.pywebview?.api?.salvar_rascunho_cliente) {
      const resposta = await window.pywebview.api.salvar_rascunho_cliente(rascunho);

      if (!resposta?.ok) {
        throw new Error(resposta?.msg || "Falha ao salvar rascunho.");
      }

      state.rascunhosClientes = resposta.itens || [];
      state.rascunhoClienteEditando = resposta.item?.id || rascunho.id || "";
    } else {
      const itens = carregarRascunhosLocal();
      const id = rascunho.id || `local_${Date.now()}_${rascunho.doc.slice(-6)}`;
      const item = {
        ...rascunho,
        id,
        atualizado_em: new Date().toISOString(),
        criado_em: rascunho.criado_em || new Date().toISOString()
      };
      const filtrados = itens.filter((draft) => draft.id !== id);
      state.rascunhosClientes = [item, ...filtrados];
      salvarRascunhosLocal(state.rascunhosClientes);
      state.rascunhoClienteEditando = id;
    }

    renderizarFilaClientes();
    showSimpleOperationalToast("Rascunho salvo.");
    setStatus("Rascunho salvo", "success");
  } catch (error) {
    log(`Falha ao salvar rascunho: ${error}`, "error");
    openLogsPopover();
    setStatus("Falha ao salvar", "error");
  }
}

async function excluirRascunhoCliente(rascunhoId, options = {}) {
  const id = String(rascunhoId || "");

  if (!id) {
    return;
  }

  try {
    if (window.pywebview?.api?.excluir_rascunho_cliente) {
      const resposta = await window.pywebview.api.excluir_rascunho_cliente(id);

      if (!resposta?.ok) {
        throw new Error(resposta?.msg || "Falha ao excluir rascunho.");
      }

      state.rascunhosClientes = resposta.itens || [];
    } else {
      state.rascunhosClientes = carregarRascunhosLocal().filter((item) => item.id !== id);
      salvarRascunhosLocal(state.rascunhosClientes);
    }

    if (state.rascunhoClienteEditando === id) {
      state.rascunhoClienteEditando = "";
    }

    renderizarFilaClientes();

    if (!options.silent) {
      showSimpleOperationalToast("Rascunho excluido.");
    }
  } catch (error) {
    log(`Falha ao excluir rascunho: ${error}`, "error");
    openLogsPopover();
  }
}

function carregarRascunhoCliente(rascunhoId) {
  const item = state.rascunhosClientes.find((draft) => String(draft.id || "") === String(rascunhoId || ""));

  if (!item) {
    showSimpleOperationalToast("Rascunho nao encontrado.");
    return;
  }

  carregarClienteNoFormulario(item, { rascunho: true });
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

  if (input) {
    input.addEventListener("blur", () => {
      agendarConsultaCep({ immediate: true, mostrarIncompleto: true });
    });
  }

  const cadastroInput = el("clienteCadastroCep");

  if (cadastroInput) {
    cadastroInput.addEventListener("blur", () => {
      agendarConsultaCepCadastro({ immediate: true, mostrarIncompleto: true });
    });
  }
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

function setSidebarExpanded(expanded) {
  state.sidebarOpen = Boolean(expanded);

  const sidebar = el("appSidebar");
  const toggle = el("sidebarToggle");

  if (sidebar) {
    sidebar.classList.toggle("is-open", state.sidebarOpen);
  }

  if (toggle) {
    toggle.setAttribute("aria-expanded", String(state.sidebarOpen));
    toggle.setAttribute("aria-label", state.sidebarOpen ? "Fechar menu" : "Abrir menu");
  }
}

function toggleSidebar() {
  setSidebarExpanded(!state.sidebarOpen);
}

function lockSidebarCollapsed(locked) {
  const sidebar = el("appSidebar");

  if (locked) {
    setSidebarExpanded(false);
  }

  if (sidebar) {
    sidebar.classList.toggle("is-locked-collapsed", Boolean(locked));
  }
}

function setSidebarActive(view) {
  const mapa = {
    boletos: "navBoleto",
    cliente: "navCliente",
    multa: "navMulta",
    extratos: "navExtratos"
  };

  Object.values(mapa).forEach((id) => {
    const node = el(id);

    if (node) {
      node.classList.remove("active");
    }
  });

  const active = el(mapa[view] || mapa.boletos);

  if (active) {
    active.classList.add("active");
  }
}

function setMonitorMode(mode) {
  const nextMode = MONITOR_STAGES[mode] ? mode : "boletos";

  if (state.monitorMode === nextMode && ETAPA_NODE_CACHE.length === MONITOR_STAGES[nextMode].length) {
    return;
  }

  state.monitorMode = nextMode;
  ETAPAS = MONITOR_STAGES[nextMode];
  DISPLAY_STAGE_MAP = criarDisplayStageMap(ETAPAS);
  state.etapasConstruidas = false;
  construirEtapas();
  resetarEtapas();
}

function mostrarPainelWorkspace(view) {
  const panels = {
    boletos: el("mainFormPanel"),
    cliente: el("clientRegistrationPanel"),
    multa: el("multaContratualPanel"),
    extratos: el("bankStatementsPanel")
  };

  Object.entries(panels).forEach(([key, node]) => {
    if (!node) {
      return;
    }

    node.classList.toggle("hidden", key !== view);
  });

  state.currentWorkspace = view;
  setSidebarActive(view);
}

function showBoletoWorkspace(options = {}) {
  setMonitorMode("boletos");
  mostrarPainelWorkspace("boletos");
  hideCadastroClienteFeedback();

  if (options.status !== false && !state.flowRunning) {
    setStatus("Aguardando", "idle");
  }
}

function showMultaContratualWorkspace(options = {}) {
  if (state.flowRunning) {
    showSimpleOperationalToast("Aguarde a conclusÃ£o da aÃ§Ã£o SAP atual.");
    return;
  }

  setMonitorMode("multa");
  mostrarPainelWorkspace("multa");
  hideCadastroClienteFeedback();
  setSidebarExpanded(false);

  if (options.status !== false) {
    setStatus("Multa Contratual", "idle");
  }

  window.setTimeout(() => el("multaDoc")?.focus(), 180);
}

function showClienteRegistrationWorkspace() {
  if (state.flowRunning) {
    showSimpleOperationalToast("Aguarde a conclusão da ação SAP atual.");
    return;
  }

  const payload = {
    doc: limparDocumento(el("doc")?.value || ""),
    tipo: el("tipo")?.value || "",
    _cadastro_manual: true
  };

  state.pendingSapAction = null;
  state.pendingSapPayload = clonePlain(payload);
  preencherCadastroClienteComPayload(payload, { travarOrigem: false });
  abrirCadastroClientePanel();
  setSidebarExpanded(false);
  setStatus("Cadastro de cliente", "idle");
  window.setTimeout(() => el("clienteCadastroDoc")?.focus(), 180);
}

function obterPeriodoPadraoExtrato() {
  const hoje = new Date();
  const referencia = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
  return {
    mes: String(referencia.getMonth() + 1).padStart(2, "0"),
    ano: String(referencia.getFullYear())
  };
}

function obterAnoAtualExtrato() {
  return obterPeriodoPadraoExtrato().ano;
}

function obterMesAtualExtrato() {
  return obterPeriodoPadraoExtrato().mes;
}

function preencherMesAnoExtratosPadrao(force = false) {
  const mes = el("extratoMes");
  const ano = el("extratoAno");

  if (mes && (force || !mes.value)) {
    mes.value = obterMesAtualExtrato();
  }

  if (ano && (force || !ano.value)) {
    ano.value = obterAnoAtualExtrato();
  }

  atualizarPreviewExtrato();
}

function normalizarPastaBaseExtrato(valor) {
  return String(valor || "").trim().replace(/[\\\/]+$/, "");
}

function normalizarContaExtrato(input) {
  input.value = String(input.value || "")
    .toUpperCase()
    .replace(/[^0-9A-Z-]/g, "")
    .slice(0, 32);
  atualizarPreviewExtrato();
}

function montarPastaDestinoExtrato(mes, ano, pastaBase) {
  const base = normalizarPastaBaseExtrato(pastaBase || EXTRATO_PASTA_BASE_PADRAO);
  const sigla = MESES_EXTRATO_SIGLA[mes] || "MES";

  if (!mes || String(ano || "").length !== 4) {
    return "--";
  }

  if (!base) {
    return "";
  }

  return `${base}\\${ano}\\${mes}.${sigla}\\CEF`;
}

function montarNomeArquivoExtrato(contaArquivo, mes, ano) {
  const conta = String(contaArquivo || "").trim() || "CONTA";
  const sigla = MESES_EXTRATO_SIGLA[mes] || "MES";
  const anoCurto = String(ano || "").slice(-2) || "AA";
  return `CEF ${conta}_${sigla}-${anoCurto}.pdf`;
}

function atualizarPreviewExtrato() {
  const preview = el("extratoPreview");

  if (!preview) {
    return;
  }

  const mes = el("extratoMes")?.value || "";
  const ano = String(el("extratoAno")?.value || "").replace(/\D/g, "").slice(0, 4);
  const periodoPreview = el("extratoPeriodoPreview") || preview.querySelector("strong");

  if (periodoPreview) {
    periodoPreview.textContent = mes && ano.length === 4
      ? `${MESES_EXTRATO[mes] || mes}/${ano}`
      : "--";
  }
}

function normalizarAnoExtrato(input) {
  input.value = String(input.value || "").replace(/\D/g, "").slice(0, 4);
  atualizarPreviewExtrato();
}

function limparErroExtrato() {
  const erro = el("extratoFormError");

  if (erro) {
    erro.textContent = "";
    erro.classList.add("hidden");
  }
}

function mostrarErroExtrato(mensagem) {
  const erro = el("extratoFormError");

  if (erro) {
    erro.textContent = mensagem;
    erro.classList.remove("hidden");
  }
}

function montarPayloadExtratos() {
  const banco = el("extratoBanco")?.value || "caixa";
  const navegador = el("extratoNavegador")?.value || "opera";
  const mes = el("extratoMes")?.value || "";
  const ano = String(el("extratoAno")?.value || "").replace(/\D/g, "").slice(0, 4);
  const pastaBase = normalizarPastaBaseExtrato(EXTRATO_PASTA_BASE_PADRAO);

  limparErroExtrato();

  if (banco !== "caixa") {
    mostrarErroExtrato("Banco ainda nao preparado para esta rotina.");
    return null;
  }

  if (!MESES_EXTRATO[mes]) {
    mostrarErroExtrato("Selecione o mes do extrato.");
    return null;
  }

  if (ano.length !== 4) {
    mostrarErroExtrato("Informe o ano com 4 digitos.");
    return null;
  }

  return {
    banco,
    banco_label: "Caixa",
    navegador,
    navegador_label: NAVEGADORES_EXTRATO[navegador] || "Opera",
    mes,
    mes_label: MESES_EXTRATO[mes],
    mes_sigla: MESES_EXTRATO_SIGLA[mes],
    ano,
    conta_arquivo: "",
    pasta_base: pastaBase,
    pasta_destino: montarPastaDestinoExtrato(mes, ano, pastaBase),
    nome_arquivo: "",
    passos: [...EXTRATO_CAIXA_PASSOS]
  };
}

function extrairNomeArquivoExtrato(caminho) {
  const partes = String(caminho || "")
    .split(/[\\\/]/)
    .map((parte) => parte.trim())
    .filter(Boolean);

  return partes.pop() || "--";
}

function normalizarResultadosExtrato(resposta, payload, erroPadrao = "") {
  const origem = Array.isArray(resposta?.itens)
    ? resposta.itens
    : Array.isArray(resposta?.resultados)
      ? resposta.resultados
      : [resposta || {}];

  return origem.map((item) => {
    const statusTexto = String(item?.status || "").toLowerCase();
    const ok = typeof item?.ok === "boolean"
      ? item.ok
      : statusTexto
        ? !["erro", "error", "falha", "failed"].includes(statusTexto)
        : resposta?.ok !== false;

    return {
      status: ok ? "ok" : "erro",
      conta: String(item?.conta || resposta?.conta || "--").trim() || "--",
      arquivo: String(item?.arquivo || resposta?.arquivo || payload?.nome_arquivo || "").trim(),
      erro: String(item?.erro || item?.msg || resposta?.msg || erroPadrao || "").trim()
    };
  });
}

function renderizarResultadosExtrato() {
  const summary = el("extratoRunSummary");
  const list = el("extratoRunList");
  const count = el("extratoRunCount");

  if (!summary || !list || !count) {
    return;
  }

  list.replaceChildren();

  if (!state.extratoResultados.length) {
    summary.classList.add("hidden");
    count.textContent = "0 contas";
    return;
  }

  const baixados = state.extratoResultados.filter((item) => item.status === "ok").length;
  const erros = state.extratoResultados.length - baixados;
  count.textContent = erros
    ? `${baixados} baixadas / ${erros} erro`
    : `${baixados} baixadas`;

  state.extratoResultados.forEach((item) => {
    const row = document.createElement("div");
    row.className = `bank-run-item ${item.status}`;

    const badge = document.createElement("span");
    badge.className = "bank-run-status";
    badge.textContent = item.status === "ok" ? "OK" : "ERRO";

    const copy = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = item.conta || "--";

    const detail = document.createElement("small");
    detail.textContent = item.status === "ok"
      ? extrairNomeArquivoExtrato(item.arquivo)
      : item.erro || "Falha ao baixar esta conta.";

    copy.append(title, detail);
    row.append(badge, copy);
    list.appendChild(row);
  });

  summary.classList.remove("hidden");
}

function resetarResultadosExtrato() {
  state.extratoResultados = [];
  renderizarResultadosExtrato();
}

function registrarResultadosExtrato(itens) {
  state.extratoResultados = [
    ...state.extratoResultados,
    ...itens
  ];
  renderizarResultadosExtrato();
}

function definirResultadosExtrato(itens) {
  state.extratoResultados = [...itens];
  renderizarResultadosExtrato();
}

function abrirResumoFinalExtratos(itens, okGeral) {
  const titulo = el("extratoResumoTitulo");
  const texto = el("extratoResumoTexto");
  const lista = el("extratoResumoLista");

  if (!titulo || !texto || !lista) {
    return;
  }

  const baixados = itens.filter((item) => item.status === "ok").length;
  const erros = itens.length - baixados;

  titulo.textContent = okGeral && !erros
    ? "Baixa finalizada"
    : "Baixa concluida com alerta";
  texto.textContent = erros
    ? `${baixados} conta(s) baixada(s) e ${erros} com erro.`
    : `${baixados} conta(s) baixada(s) com sucesso.`;

  lista.replaceChildren();
  itens.forEach((item) => {
    const row = document.createElement("div");
    row.className = `extrato-summary-item ${item.status}`;

    const status = document.createElement("span");
    status.textContent = item.status === "ok" ? "OK" : "ERRO";

    const info = document.createElement("div");
    const conta = document.createElement("strong");
    conta.textContent = item.conta || "--";

    const detalhe = document.createElement("small");
    detalhe.textContent = item.status === "ok"
      ? extrairNomeArquivoExtrato(item.arquivo)
      : item.erro || "Falha ao baixar esta conta.";

    info.append(conta, detalhe);
    row.append(status, info);
    lista.appendChild(row);
  });

  openModal("extratoResumoModal");
}

function closeExtratoResumoModal() {
  closeModal("extratoResumoModal");
}

function showExtratosWorkspace(options = {}) {
  if (state.flowRunning) {
    showSimpleOperationalToast("Aguarde a conclusao da acao SAP atual.");
    return;
  }

  setMonitorMode("extratos");
  mostrarPainelWorkspace("extratos");
  hideCadastroClienteFeedback();
  setSidebarExpanded(false);
  preencherMesAnoExtratosPadrao();

  if (options.status !== false) {
    setStatus("Baixar extratos", "idle");
  }

  window.setTimeout(() => el("extratoMes")?.focus(), 180);
}

function prepararBaixaExtratos() {
  const payload = montarPayloadExtratos();

  if (!payload) {
    setStatus("Revise os extratos", "error");
    return;
  }

  window.resetarProgresso();
  ativarEtapa(0, 40, `GovConta Caixa preparado para ${payload.mes_label}/${payload.ano}.`);
  concluirEtapa(0, `Salvar PDF na area de trabalho.`);
  setStatus("Base pronta", "success");
  log(`Rotina de extratos preparada: ${payload.banco_label} - ${payload.mes_label}/${payload.ano}.`);
  log(`Passos mapeados: ${payload.passos.join(" > ")}.`);
  log(`Destino sugerido: ${payload.pasta_destino || "Area de trabalho do usuario atual"}.`);
  log(`Nome sugerido: ${payload.nome_arquivo}.`);
  showSimpleOperationalToast("Roteiro Caixa preparado com pasta e nome sugeridos.");
}

function setExtratoChromeBusy(busy) {
  const chromeButton = el("extratoChromeButton");
  const openButton = el("extratoOpenBrowserButton");

  [chromeButton, openButton].forEach((button) => {
    if (button) {
      button.disabled = Boolean(busy);
    }
  });

  if (chromeButton) {
    chromeButton.textContent = busy
      ? "Baixando..."
      : "Baixar extratos";
  }
}

async function abrirNavegadorCaixa() {
  limparErroExtrato();

  const navegador = el("extratoNavegador")?.value || "opera";
  const navegadorLabel = NAVEGADORES_EXTRATO[navegador] || "Opera";

  if (!window.pywebview?.api?.abrir_navegador_caixa) {
    mostrarErroExtrato("Backend indisponivel para abrir o navegador.");
    setStatus("Navegador indisponivel", "error");
    return;
  }

  try {
    setExtratoChromeBusy(true);
    setStatus("Abrindo navegador", "running");
    log(`Abrindo ${navegadorLabel} controlavel para acesso a Caixa.`);
    const resposta = await window.pywebview.api.abrir_navegador_caixa(navegador);

    if (!resposta?.ok) {
      mostrarErroExtrato(resposta?.msg || `Nao foi possivel abrir ${navegadorLabel}.`);
      setStatus("Navegador nao aberto", "error");
      log(resposta?.msg || `Nao foi possivel abrir ${navegadorLabel}.`, "error");
      openLogsPopover();
      return;
    }

    setStatus("Navegador aberto", "success");
    log(resposta.msg || `${navegadorLabel} controlavel aberto.`);
    showSimpleOperationalToast(`${navegadorLabel} aberto. Faca login na Caixa.`);
  } catch (error) {
    mostrarErroExtrato(`Falha ao abrir navegador: ${error}`);
    setStatus("Navegador nao aberto", "error");
    log(`Falha ao abrir navegador: ${error}`, "error");
    openLogsPopover();
  } finally {
    setExtratoChromeBusy(false);
  }
}

async function testarChromeCaixa() {
  limparErroExtrato();
  const navegador = el("extratoNavegador")?.value || "opera";
  const navegadorLabel = NAVEGADORES_EXTRATO[navegador] || "Opera";

  if (!window.pywebview?.api?.diagnosticar_chrome_caixa) {
    mostrarErroExtrato("Backend indisponivel para testar o navegador.");
    setStatus("Navegador indisponivel", "error");
    return;
  }

  try {
    setExtratoChromeBusy(true);
    setStatus("Testando navegador", "running");
    log(`Testando conexao com ${navegadorLabel} controlavel na porta 9222.`);
    const resposta = await window.pywebview.api.diagnosticar_chrome_caixa(navegador);

    if (!resposta?.ok) {
      mostrarErroExtrato(resposta?.msg || "Navegador controlavel nao encontrado.");
      setStatus("Navegador nao conectado", "error");
      log(resposta?.msg || "Navegador controlavel nao encontrado.", "error");
      openLogsPopover();
      return;
    }

    setStatus("Navegador conectado", "success");
    log(`${resposta.msg} Abas abertas: ${resposta.tabs || 0}.`);
    showSimpleOperationalToast("Navegador controlavel conectado.");
  } catch (error) {
    mostrarErroExtrato(`Falha ao testar navegador: ${error}`);
    setStatus("Navegador nao conectado", "error");
    log(`Falha ao testar navegador: ${error}`, "error");
    openLogsPopover();
  } finally {
    setExtratoChromeBusy(false);
  }
}

async function baixarExtratoAtualChrome() {
  const payload = montarPayloadExtratos();

  if (!payload) {
    setStatus("Revise os extratos", "error");
    return;
  }

  if (!window.pywebview?.api?.baixar_extratos_caixa) {
    mostrarErroExtrato("Backend indisponivel para controlar o navegador.");
    setStatus("Navegador indisponivel", "error");
    return;
  }

  try {
    setExtratoChromeBusy(true);
    resetarResultadosExtrato();
    window.resetarProgresso();
    ativarEtapa(0, 10, "Conectando ao navegador controlavel.");
    setStatus("Baixando extrato", "running");
    log(`Baixa Caixa solicitada no ${payload.navegador_label}: ${payload.mes_label}/${payload.ano}.`);

    const resposta = await window.pywebview.api.baixar_extratos_caixa(payload);
    const itens = normalizarResultadosExtrato(resposta, payload);
    const erros = itens.filter((item) => item.status === "erro").length;
    definirResultadosExtrato(itens);

    if (!resposta?.ok) {
      const mensagem = resposta?.msg || "Falha ao baixar extrato Caixa.";
      mostrarErroExtrato(mensagem);
      setStatus("Falha nos extratos", "error");
      log(mensagem, "error");
      abrirResumoFinalExtratos(itens, false);
      return;
    }

    const primeiroArquivo = itens.find((item) => item.status === "ok")?.arquivo || resposta.arquivo || "";
    concluirEtapa(0, `Arquivo salvo: ${primeiroArquivo || "PDF Caixa"}.`);
    setStatus(erros ? "Extratos com alerta" : "Extratos baixados", erros ? "error" : "success");
    log(`Extratos Caixa processados: ${itens.length}. Baixados: ${itens.length - erros}. Erros: ${erros}.`);
    showSimpleOperationalToast(erros ? "Baixa finalizada com alerta." : "Extratos Caixa baixados com sucesso.");
    abrirResumoFinalExtratos(itens, !erros);
  } catch (error) {
    const mensagem = `Falha ao baixar extrato: ${error}`;
    const itens = normalizarResultadosExtrato({ ok: false, msg: mensagem }, payload, mensagem);
    registrarResultadosExtrato(itens);
    mostrarErroExtrato(mensagem);
    setStatus("Falha nos extratos", "error");
    log(mensagem, "error");
    abrirResumoFinalExtratos(itens, false);
  } finally {
    setExtratoChromeBusy(false);
  }
}

function limparFormularioExtratos() {
  const banco = el("extratoBanco");
  const navegador = el("extratoNavegador");
  const mes = el("extratoMes");
  const ano = el("extratoAno");

  if (banco) {
    banco.value = "caixa";
  }

  if (navegador) {
    navegador.value = "opera";
  }

  if (mes) {
    mes.value = "";
  }

  if (ano) {
    ano.value = obterAnoAtualExtrato();
  }

  limparErroExtrato();
  resetarResultadosExtrato();
  atualizarPreviewExtrato();
  setStatus("Baixar extratos", "idle");
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

function formatarDocCadastro(elm) {
  elm.value = formatarDocumento(elm.value);
  atualizarResumoCadastroCliente();
}

function atualizarDocumentoMultaUI(valorAtual) {
  const input = el("multaDoc");
  const badge = el("multaDocBadge");
  const hint = el("multaDocHint");
  const counter = el("multaDigitCounter");
  const info = analisarDocumento(valorAtual);

  if (input) {
    input.value = info.formatado;
  }

  if (badge) {
    badge.textContent = info.badge;
    badge.className = `doc-badge ${info.classe}`;
  }

  if (hint) {
    hint.textContent = info.hint;
  }

  if (counter) {
    counter.textContent = info.contador;
  }
}

function formatarDocMulta(elm) {
  limparMensagemCampo("multaDoc");
  atualizarDocumentoMultaUI(elm.value);
}

function formatarValorMulta(elm) {
  limparMensagemCampo("multaValor");
  elm.value = formatarValorDigitadoSemLimite(elm.value);
}

function formatarContratoMulta(elm) {
  limparMensagemCampo("multaContrato");
  elm.value = String(elm.value || "").replace(/\D/g, "").slice(0, 9);
}

function atualizarValidadeMultaUI() {
  const valor = el("multaValidade")?.value === "60" ? "60" : "30";

  el("multaValidade30")?.classList.toggle("active", valor === "30");
  el("multaValidade60")?.classList.toggle("active", valor === "60");
}

function selecionarValidadeMulta(dias) {
  const valor = String(dias || "").replace(/\D/g, "") === "60" ? "60" : "30";
  const input = el("multaValidade");

  if (input) {
    input.value = valor;
  }

  limparMensagemCampo("multaValidade");
  atualizarValidadeMultaUI();
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

function atualizarCadastroTipoUI() {
  const tipo = el("clienteCadastroTipo")?.value || "";
  const label = TIPOS_SOLICITACAO[tipo] || TIPOS_SOLICITACAO[""];
  const buttonText = el("clienteCadastroTipoButtonText");

  if (buttonText) {
    buttonText.textContent = label;
  }
}

function setCadastroTipoTravado(travado) {
  const button = el("clienteCadastroTipoButton");

  if (button) {
    button.disabled = Boolean(travado);
    button.classList.toggle("readonly-like", Boolean(travado));
  }
}

function toggleCadastroTipoMenu(event) {
  if (el("clienteCadastroTipoButton")?.disabled) {
    return;
  }

  toggleMenu("clienteCadastroTipoMenu", "clienteCadastroTipoButton", event);
}

function fecharCadastroTipoMenu() {
  closeMenu("clienteCadastroTipoMenu", "clienteCadastroTipoButton");
}

function selecionarCadastroTipo(tipo, label) {
  el("clienteCadastroTipo").value = tipo;
  el("clienteCadastroTipoButtonText").textContent = label;
  fecharCadastroTipoMenu();
  atualizarResumoCadastroCliente();
}

function atualizarCadastroTituloUI() {
  const titulo = el("clienteCadastroTitulo")?.value || "auto";
  const buttonText = el("clienteCadastroTituloButtonText");

  if (buttonText) {
    buttonText.textContent = TRATAMENTOS_CADASTRO[titulo] || TRATAMENTOS_CADASTRO.auto;
  }
}

function setCadastroTituloTravado(travado) {
  const button = el("clienteCadastroTituloButton");

  if (button) {
    button.disabled = Boolean(travado);
    button.classList.toggle("readonly-like", Boolean(travado));
  }
}

function toggleCadastroTituloMenu(event) {
  if (el("clienteCadastroTituloButton")?.disabled) {
    return;
  }

  toggleMenu("clienteCadastroTituloMenu", "clienteCadastroTituloButton", event);
}

function fecharCadastroTituloMenu() {
  closeMenu("clienteCadastroTituloMenu", "clienteCadastroTituloButton");
}

function selecionarCadastroTitulo(titulo, label) {
  el("clienteCadastroTitulo").value = titulo;
  el("clienteCadastroTituloButtonText").textContent = label;
  fecharCadastroTituloMenu();
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
  return extrairDadosMeioPagamentoDoAviso(mensagem).nome;
}

function extrairDadosMeioPagamentoDoAviso(mensagem) {
  const texto = String(mensagem || "").trim();

  if (!texto) {
    return {};
  }

  if (texto.startsWith(PAYMENT_FILE_NOTICE_PREFIX)) {
    const payload = texto.slice(PAYMENT_FILE_NOTICE_PREFIX.length).trim();

    if (!payload) {
      return {};
    }

    if (payload.startsWith("{")) {
      try {
        const dados = JSON.parse(payload);
        const nome = String(dados.nome || dados.nome_arquivo || dados.nomeArquivo || "").trim();
        return {
          nome,
          cliente: dados.cliente,
          doc_fat: dados.doc_fat || dados.docFat
        };
      } catch (error) {
        return { nome: payload };
      }
    }

    return { nome: payload };
  }

  return {};
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
    return "Nome do arquivo de meio de pagamento pronto para copiar e salvar.";
  }

  return texto;
}

function tratarAvisoNomePdf(mensagem) {
  const nomePdf = extrairNomePdfDoAviso(mensagem);

  if (nomePdf) {
    if (modalEstaAberto("pdfNameModal") && state.currentPdfNameNotice !== nomePdf) {
      const jaEnfileirado = state.operationalNoticeQueue.some((item) => {
        const payload = item?.payload || {};
        const nomeFila = String(payload.nome || payload.nome_arquivo || payload.nome_pdf || "").trim();
        return item?.tipo === "pdf" && nomeFila === nomePdf;
      });

      if (!jaEnfileirado) {
        state.operationalNoticeQueue.push({
          tipo: "pdf",
          payload: { nome_pdf: nomePdf }
        });
      }

      return limparMensagemAvisoPdf(mensagem);
    }

    openPdfNameModal(nomePdf);
  }

  return limparMensagemAvisoPdf(mensagem);
}

function tratarAvisoMeioPagamento(mensagem) {
  const dadosMeioPagamento = extrairDadosMeioPagamentoDoAviso(mensagem);
  const nomeArquivo = dadosMeioPagamento.nome;

  if (nomeArquivo) {
    atualizarMeioPagamentoResultado(dadosMeioPagamento);
  }

  return limparMensagemAvisoMeioPagamento(mensagem);
}

function tratarAvisoSimples(mensagem) {
  const texto = String(mensagem || "").trim();

  if (!texto.startsWith(SIMPLE_NOTICE_PREFIX)) {
    return mensagem;
  }

  const aviso = texto.slice(SIMPLE_NOTICE_PREFIX.length).trim();
  showSimpleOperationalToast(aviso || "Ação concluída.");
  return aviso || "Ação concluída.";
}

function tratarAvisoResultadoExtrato(mensagem) {
  const texto = String(mensagem || "").trim();

  if (!texto.startsWith(EXTRATO_RESULT_NOTICE_PREFIX)) {
    return mensagem;
  }

  const payload = texto.slice(EXTRATO_RESULT_NOTICE_PREFIX.length).trim();

  try {
    const item = JSON.parse(payload);
    const itens = normalizarResultadosExtrato({ ok: item?.status !== "erro", itens: [item] }, {});
    registrarResultadosExtrato(itens);
    const conta = itens[0]?.conta || "--";
    return itens[0]?.status === "ok"
      ? `Extrato baixado: ${conta}.`
      : `Falha na conta: ${conta}.`;
  } catch (error) {
    return "Resultado de extrato recebido.";
  }
}

function tratarAvisosOperacionais(mensagem) {
  return tratarAvisoSimples(
    tratarAvisoResultadoExtrato(
      tratarAvisoMeioPagamento(
        tratarAvisoNomePdf(mensagem)
      )
    )
  );
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

function prepararInterfaceParaAvisoOperacional() {
  try {
    window.focus();
  } catch (error) {
    // O foco visual pode depender do Windows/SAP, mas o aviso fica pronto na interface.
  }
}

function showSimpleOperationalToast(message) {
  const texto = String(message || "").trim();

  if (!texto) {
    return;
  }

  let toast = el("simpleOperationalToast");

  if (!toast) {
    toast = document.createElement("div");
    toast.id = "simpleOperationalToast";
    toast.className = "simple-operational-toast";
    document.body.appendChild(toast);
    domCache.set("simpleOperationalToast", toast);
  }

  toast.textContent = texto;
  toast.classList.add("visible");
  window.clearTimeout(state.simpleOperationalToastTimer);
  state.simpleOperationalToastTimer = window.setTimeout(() => {
    toast.classList.remove("visible");
  }, 4600);
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

function setMeioPagamentoResultado(nomeArquivo, copied = false) {
  const nome = String(nomeArquivo || "").trim();
  const value = el("resultMeioPagamento");
  const button = el("resultMeioPagamentoButton");
  const hint = el("resultMeioPagamentoHint");

  if (value) {
    value.textContent = nome || "--";
  }

  if (button) {
    button.disabled = !nome;
    button.classList.toggle("copied", Boolean(nome && copied));
  }

  if (hint) {
    hint.textContent = nome ? (copied ? "Texto copiado" : "Clique para copiar") : "Aguardando nome";
  }
}

function atualizarMeioPagamentoResultado(payload = {}) {
  const dados = typeof payload === "string" ? { nome: payload } : (payload || {});
  const nome = String(dados.nome || dados.nome_arquivo || dados.nomeArquivo || "").trim();

  if (!nome) {
    return;
  }

  state.currentPaymentFileNotice = nome;
  state.lastPaymentFileNotice = nome;

  if (dados.cliente && el("resultCliente")) {
    el("resultCliente").textContent = dados.cliente;
  }

  if ((dados.doc_fat || dados.docFat) && el("resultDocFat")) {
    el("resultDocFat").textContent = dados.doc_fat || dados.docFat;
  }

  setMeioPagamentoResultado(nome, false);
  el("resultBox")?.classList.remove("hidden");
}

async function copiarMeioPagamentoResultado() {
  const nome = String(state.currentPaymentFileNotice || el("resultMeioPagamento")?.textContent || "").trim();

  if (!nome || nome === "--") {
    return;
  }

  await copiarTextoParaAreaTransferencia(nome);
  setMeioPagamentoResultado(nome, true);
  showSimpleOperationalToast("Meio de pagamento copiado.");
  window.clearTimeout(state.paymentFileCopiedTimer);
  state.paymentFileCopiedTimer = window.setTimeout(() => {
    setMeioPagamentoResultado(nome, false);
  }, 3200);
}

window.copiarMeioPagamentoResultado = copiarMeioPagamentoResultado;

function openPdfNameModal(nomePdf, options = {}) {
  const nomeLimpo = String(nomePdf || "").trim();

  if (!nomeLimpo) {
    return;
  }

  const exigeConfirmacao = Boolean(options.aguardar_confirmacao || options.exigir_confirmacao);
  const forceOpen = Boolean(options.forceOpen || exigeConfirmacao);

  if (state.lastPdfNameNotice === nomeLimpo && !forceOpen) {
    return;
  }

  state.currentPdfNameNotice = nomeLimpo;
  state.lastPdfNameNotice = nomeLimpo;
  state.currentPdfNoticeId = String(options.notice_id || "");
  state.currentPdfRequiresConfirmation = exigeConfirmacao;

  prepararInterfaceParaAvisoOperacional();

  const value = el("pdfNameValue");
  const warning = el("pdfNameWarning");
  const button = el("pdfNameActionButton");

  if (value) {
    value.textContent = nomeLimpo;
  }

  if (warning) {
    const aviso = String(options.aviso_confirmacao || "").trim();
    warning.textContent = aviso;
    warning.classList.toggle("hidden", !aviso);
  }

  if (button) {
    button.textContent = String(options.botao_confirmacao || "").trim() || "Fechar";
  }

  copiarTextoParaAreaTransferencia(nomeLimpo).catch(() => {});
  openModal("pdfNameModal");
}

function openPdfNameModalComConfirmacao(nomePdf, options = {}) {
  state.lastPdfNameNotice = "";
  openPdfNameModal(nomePdf, { ...options, forceOpen: true });
}

function closePdfNameModal() {
  closeModal("pdfNameModal");
}

function promoverModalConfirmacaoLote() {
  const modal = el("batchConfirmModal");

  if (!modal || modal.classList.contains("hidden")) {
    return;
  }

  window.clearTimeout(state.batchConfirmTransitionTimer);
  modal.classList.add("batch-confirm-promote");
  state.batchConfirmTransitionTimer = window.setTimeout(() => {
    modal.classList.remove("batch-confirm-promote");
  }, 360);
}

function closePdfNameNotice() {
  const estavaEmpilhado =
    modalEstaAberto("pdfNameModal") &&
    modalEstaAberto("batchConfirmModal");
  const noticeId = state.currentPdfNoticeId;
  const deveConfirmar = state.currentPdfRequiresConfirmation;

  state.currentPdfNoticeId = "";
  state.currentPdfRequiresConfirmation = false;

  closePdfNameModal();

  if (deveConfirmar && noticeId) {
    try {
      window.pywebview?.api?.confirmar_aviso_operacional?.(noticeId)?.catch?.(() => {});
    } catch (error) {
      // A confirmacao e opcional para a interface, mas exigida pelo backend neste aviso.
    }
  }

  if (estavaEmpilhado) {
    promoverModalConfirmacaoLote();
  }

  processarProximoAvisoOperacional();
}

function algumAvisoOperacionalAberto() {
  return modalEstaAberto("pdfNameModal");
}

function processarProximoAvisoOperacional() {
  if (algumAvisoOperacionalAberto() || !state.operationalNoticeQueue.length) {
    return;
  }

  const proximo = state.operationalNoticeQueue.shift();
  window.setTimeout(() => {
    mostrarAvisoOperacionalAgora(proximo.tipo, proximo.payload);
  }, 120);
}

function mostrarAvisoOperacionalAgora(tipo, payload = {}) {
  const nome = String(payload.nome || payload.nome_arquivo || payload.nome_pdf || "").trim();

  if (!nome) {
    processarProximoAvisoOperacional();
    return;
  }

  if (tipo === "payment") {
    atualizarMeioPagamentoResultado({ ...payload, nome });
    processarProximoAvisoOperacional();
    return;
  }

  openPdfNameModalComConfirmacao(nome, payload);
}

function mostrarAvisoOperacional(tipo, payload = {}) {
  if (algumAvisoOperacionalAberto()) {
    state.operationalNoticeQueue.push({
      tipo,
      payload: { ...payload }
    });
    return;
  }

  mostrarAvisoOperacionalAgora(tipo, payload);
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
      ${campoHistorico("Numero do BOL", registro.numero_bol || registro.identificacao_pagamento || registro.boleto)}
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

function htmlJsArg(value) {
  return escapeHtml(JSON.stringify(String(value || "")));
}

// Preenche o card de resultado com os dados essenciais do processo.
function preencherResultado(resultado = {}) {
  const box = el("resultBox");
  const nomeMeioPagamento =
    resultado.nome_arquivo_meio_pagamento
    || resultado.meio_pagamento
    || state.currentPaymentFileNotice
    || "";

  el("resultCliente").textContent = resultado.cliente || "--";
  el("resultDocFat").textContent = resultado.doc_fat || resultado.faturamento || "--";
  setMeioPagamentoResultado(nomeMeioPagamento, false);

  box.classList.remove("hidden");
}

window.preencherResultado = preencherResultado;

function esconderResultado() {
  el("resultBox").classList.add("hidden");
  el("resultCliente").textContent = "--";
  el("resultDocFat").textContent = "--";
  state.currentPaymentFileNotice = "";
  state.lastPaymentFileNotice = "";
  window.clearTimeout(state.paymentFileCopiedTimer);
  setMeioPagamentoResultado("", false);
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

function clonePlain(value) {
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(JSON.stringify(value));
  } catch (error) {
    return value;
  }
}

function formatarDocumentoResumo(documento) {
  const info = analisarDocumento(documento || "");
  return info.formatado || String(documento || "").trim() || "--";
}

function getSetoresPendentesLabel(acao = {}) {
  const setores = Array.isArray(acao.setores_necessarios)
    ? acao.setores_necessarios
    : [];

  return setores.filter(Boolean).join(" + ") || "--";
}

function setPendingSapAction(acao, payload) {
  state.pendingSapAction = clonePlain(acao);
  state.pendingSapPayload = clonePlain(payload);
}

function openSapActionModal(acao, payload) {
  if (!acao) {
    return false;
  }

  setPendingSapAction(acao, payload);

  const tipoAcao = String(acao.tipo || "").trim();
  const doc = acao.documento || payload?.doc || "";
  const details = el("sapActionDetails");
  const confirmButton = el("sapActionConfirm");
  const title = el("sapActionTitle");
  const message = el("sapActionMessage");
  const kicker = el("sapActionKicker");

  confirmButton.disabled = false;

  if (tipoAcao === "cliente_nao_cadastrado") {
    const isMulta = payload?.modalidade === "multa_contratual" || payload?.tipo === "multa_contratual";
    kicker.textContent = "Cliente não cadastrado";
    title.textContent = isMulta ? "Criar cliente para Multa Contratual?" : "Criar cliente no SAP?";
    message.textContent = "O CPF/CNPJ informado não foi localizado. Para continuar, cadastre o cliente e depois o fluxo será retomado automaticamente.";
    confirmButton.textContent = "Criar cliente";
    details.innerHTML = `
      <div>
        <span>Cliente</span>
        <strong>${escapeHtml(formatarDocumentoResumo(doc))}</strong>
      </div>
      <div>
        <span>Tipo solicitado</span>
        <strong>${escapeHtml(TIPOS_SOLICITACAO[payload?.tipo] || payload?.tipo || "--")}</strong>
      </div>
    `;
  } else if (tipoAcao === "setor_ausente") {
    kicker.textContent = "Setor ausente";
    title.textContent = "Criar setor do cliente?";
    message.textContent = "O cliente existe, mas não possui o setor exigido para o tipo selecionado. Os dados de setor são padrão, então o sistema pode criar e seguir o fluxo.";
    confirmButton.textContent = "Criar setores e continuar";
    details.innerHTML = `
      <div>
        <span>Cliente</span>
        <strong>${escapeHtml(acao.cliente || "--")}</strong>
      </div>
      <div>
        <span>Setor necessário</span>
        <strong>${escapeHtml(getSetoresPendentesLabel(acao))}</strong>
      </div>
      <div>
        <span>Cliente</span>
        <strong>${escapeHtml(formatarDocumentoResumo(doc))}</strong>
      </div>
    `;
  } else {
    return false;
  }

  openModal("sapActionModal");
  return true;
}

function closeSapActionModal() {
  closeModal("sapActionModal");
}

function cancelarAcaoSapPendente() {
  closeSapActionModal();
  setStatus("Aguardando", "idle");
}

function preencherCadastroClienteComPayload(payload = {}, options = {}) {
  const { travarOrigem = true } = options;
  const docInfo = analisarDocumento(payload.doc || "");
  const isMulta = payload.modalidade === "multa_contratual" || payload.tipo === "multa_contratual";
  const nomeCliente = String(
    payload.nome_cliente
    || payload.cliente_nome
    || payload.nome
    || payload.razao_social
    || ""
  ).trim();

  el("clientRegistrationKicker").textContent = isMulta ? "Cadastro MC" : "Cadastro SAP";
  el("clientRegistrationTitle").textContent = isMulta
    ? "Criar cliente - Multa Contratual"
    : "Criar cliente";
  el("clientRegistrationDoc").textContent = docInfo.formatado || payload.doc || "--";
  el("clientRegistrationTipo").textContent = TIPOS_SOLICITACAO[payload.tipo] || payload.tipo || "--";
  el("clientRegistrationDocBadge").textContent = docInfo.badge || "CPF/CNPJ";
  el("clientRegistrationDocBadge").className = `doc-badge ${docInfo.classe || "neutral"}`;
  el("clientRegistrationSubmit").textContent = isMulta
    ? "Criar cliente e continuar multa"
    : "Criar cliente e continuar";

  el("clienteCadastroNome1").value = nomeCliente;
  el("clienteCadastroDoc").value = docInfo.formatado || formatarDocumento(payload.doc || "");
  el("clienteCadastroDoc").readOnly = travarOrigem;
  el("clienteCadastroDoc").classList.toggle("readonly-like", travarOrigem);
  el("clienteCadastroTipo").value = payload.tipo || "";
  el("clienteCadastroTipo").disabled = travarOrigem;
  setCadastroTipoTravado(travarOrigem);
  atualizarCadastroTipoUI();
  el("clienteCadastroRua").value = "";
  el("clienteCadastroNumero").value = "";
  el("clienteCadastroCep").value = "";
  el("clienteCadastroBairro").value = "";
  el("clienteCadastroCidade").value = "";
  el("clienteCadastroEstado").value = "BA";
  el("clienteCadastroInscricao").value = "ISENTO";
  el("clienteCadastroTelefone").value = "";
  el("clienteCadastroEmail").value = "";
  state.clientRegistrationSource = isMulta ? "multa" : (travarOrigem ? "boleto" : "manual");
  atualizarTratamentoCadastroPorDocumento();
  hideCadastroClienteFeedback();
}

function atualizarResumoCadastroCliente() {
  const docInfo = analisarDocumento(el("clienteCadastroDoc")?.value || "");
  const tipo = el("clienteCadastroTipo")?.value || "";

  el("clientRegistrationDoc").textContent = docInfo.formatado || "--";
  el("clientRegistrationTipo").textContent = TIPOS_SOLICITACAO[tipo] || "--";
  el("clientRegistrationDocBadge").textContent = docInfo.badge || "CPF/CNPJ";
  el("clientRegistrationDocBadge").className = `doc-badge ${docInfo.classe || "neutral"}`;
  atualizarCadastroTipoUI();
  atualizarTratamentoCadastroPorDocumento();
}

function atualizarTratamentoCadastroPorDocumento() {
  const docInfo = analisarDocumento(el("clienteCadastroDoc")?.value || "");
  const tratamento = el("clienteCadastroTitulo");

  if (!tratamento) {
    return;
  }

  if (docInfo.digitos.length === 14) {
    tratamento.value = "Empresa";
    tratamento.disabled = true;
    tratamento.classList.add("readonly-like");
    setCadastroTituloTravado(true);
    atualizarCadastroTituloUI();
    return;
  }

  tratamento.disabled = false;
  tratamento.classList.remove("readonly-like");
  setCadastroTituloTravado(false);

  if (tratamento.value === "Empresa") {
    tratamento.value = "auto";
  }

  atualizarCadastroTituloUI();
}

function abrirCadastroClientePanel() {
  setMonitorMode("cliente");
  mostrarPainelWorkspace("cliente");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function abrirAbaCadastroCliente() {
  const payload = clonePlain(state.pendingSapPayload);

  if (!payload) {
    log("Não foi possível abrir cadastro: dados originais do fluxo ausentes.", "error");
    openLogsPopover();
    return;
  }

  preencherCadastroClienteComPayload(payload);
  abrirCadastroClientePanel();
  setStatus("Aguardando cadastro", "idle");
  window.setTimeout(() => el("clienteCadastroNome1").focus(), 180);
}

function fecharAbaCadastroCliente(options = {}) {
  if (el("clientRegistrationPanel")) {
    el("clientRegistrationPanel").classList.add("hidden");
  }

  hideCadastroClienteFeedback();

  if (options.mostrarBoleto !== false) {
    const destino = options.destino || state.clientRegistrationSource;

    if (destino === "multa") {
      showMultaContratualWorkspace({ status: options.status !== false });
    } else {
      showBoletoWorkspace({ status: options.status !== false });
    }
  }
}

function cancelarCadastroCliente() {
  const origem = state.clientRegistrationSource;

  if (origem === "manual" || origem === "multa") {
    state.pendingSapAction = null;
    state.pendingSapPayload = null;
  }

  state.clientRegistrationSource = "";
  fecharAbaCadastroCliente({ destino: origem });
  setStatus("Aguardando", "idle");
}

function clearCadastroClienteFieldErrors() {
  [
    "clienteCadastroDoc",
    "clienteCadastroTipo",
    "clienteCadastroTitulo",
    "clienteCadastroNome1",
    "clienteCadastroRua",
    "clienteCadastroNumero",
    "clienteCadastroCep",
    "clienteCadastroBairro",
    "clienteCadastroCidade",
    "clienteCadastroEstado",
    "clienteCadastroTelefone",
    "clienteCadastroEmail"
  ].forEach((fieldId) => {
    const field = el(fieldId)?.closest(".field");

    if (field) {
      field.classList.remove("has-error");
    }
  });
}

function showCadastroClienteFeedback(message, ok = false, fieldId = "") {
  const feedback = el("clientRegistrationFeedback");
  clearCadastroClienteFieldErrors();
  feedback.textContent = message;
  feedback.className = `contact-feedback ${ok ? "success" : "error"}`;

  if (fieldId) {
    const target = el(fieldId);
    const field = target?.closest(".field");

    if (field) {
      field.classList.add("has-error");
    }

    const focusTarget =
      fieldId === "clienteCadastroTipo"
        ? el("clienteCadastroTipoButton")
        : fieldId === "clienteCadastroTitulo"
          ? el("clienteCadastroTituloButton")
          : target;

    if (focusTarget && typeof focusTarget.focus === "function" && !focusTarget.disabled && !focusTarget.readOnly) {
      (field || focusTarget).scrollIntoView({ behavior: "smooth", block: "center" });
      window.setTimeout(() => focusTarget.focus(), 160);
    }
  }
}

function hideCadastroClienteFeedback() {
  const feedback = el("clientRegistrationFeedback");
  if (!feedback) {
    return;
  }

  feedback.textContent = "";
  feedback.className = "contact-feedback hidden";
  clearCadastroClienteFieldErrors();
}

function coletarCadastroCliente() {
  const payload = clonePlain(state.pendingSapPayload) || {};
  const docInfo = analisarDocumento(el("clienteCadastroDoc")?.value || payload.doc || "");
  const tipo = el("clienteCadastroTipo")?.value || payload.tipo || "";

  if (![11, 14].includes(docInfo.digitos.length)) {
    showCadastroClienteFeedback("Informe CPF ou CNPJ completo antes de criar o cliente.", false, "clienteCadastroDoc");
    return null;
  }

  if (!tipo) {
    showCadastroClienteFeedback("Selecione o tipo de solicitação para definir o setor inicial.", false, "clienteCadastroTipo");
    return null;
  }

  const cadastro = {
    ...payload,
    doc: docInfo.digitos,
    tipo,
    nome1: el("clienteCadastroNome1").value.trim(),
    nome2: "",
    titulo: el("clienteCadastroTitulo").value,
    rua: el("clienteCadastroRua").value.trim(),
    numero: el("clienteCadastroNumero").value.trim(),
    cep: formatarCepValue(el("clienteCadastroCep").value.trim()),
    bairro: el("clienteCadastroBairro").value.trim(),
    cidade: sanitizarCidade(el("clienteCadastroCidade").value.trim()),
    estado: el("clienteCadastroEstado").value.trim().toUpperCase() || "BA",
    inscricao_estadual: el("clienteCadastroInscricao").value.trim() || "ISENTO",
    telefone: el("clienteCadastroTelefone").value.trim(),
    email: el("clienteCadastroEmail").value.trim()
  };

  const cepDigitos = obterDigitosCep(cadastro.cep);
  const telefoneDigitos = String(cadastro.telefone || "").replace(/\D/g, "");
  const obrigatoriosSequenciais = [
    ["clienteCadastroNome1", "Nome / Razão social", cadastro.nome1],
    ["clienteCadastroRua", "Rua", cadastro.rua],
    ["clienteCadastroNumero", "Número", cadastro.numero],
    ["clienteCadastroCep", "CEP", cepDigitos.length === 8 ? cadastro.cep : ""],
    ["clienteCadastroBairro", "Bairro", cadastro.bairro],
    ["clienteCadastroCidade", "Cidade", cadastro.cidade],
    ["clienteCadastroEstado", "Estado", cadastro.estado]
  ];
  const pendente = obrigatoriosSequenciais.find(([, , value]) => !String(value || "").trim());

  if (pendente) {
    showCadastroClienteFeedback(`Preencha o campo obrigatório: ${pendente[1]}.`, false, pendente[0]);
    return null;
  }

  if (!/^[A-Z]{2}$/.test(cadastro.estado)) {
    showCadastroClienteFeedback("Informe o estado usando a sigla com 2 letras.", false, "clienteCadastroEstado");
    return null;
  }

  if (cepDigitos.length !== 8) {
    showCadastroClienteFeedback("CEP obrigatório deve conter 8 dígitos.", false, "clienteCadastroCep");
    return null;
  }

  if (telefoneDigitos && ![10, 11].includes(telefoneDigitos.length)) {
    showCadastroClienteFeedback("Telefone deve ter 10 ou 11 dígitos quando informado.", false, "clienteCadastroTelefone");
    return null;
  }

  if (cadastro.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cadastro.email)) {
    showCadastroClienteFeedback("Informe um e-mail válido ou deixe o campo em branco.", false, "clienteCadastroEmail");
    return null;
  }

  return cadastro;
}

function preencherBoletoAposCadastroCliente(cadastro = {}) {
  atualizarDocumentoUI(cadastro.doc || "");
  el("tipo").value = cadastro.tipo || "";
  atualizarTipo();
}

function preencherMultaAposCadastroCliente(cadastro = {}, payloadOriginal = {}) {
  atualizarDocumentoMultaUI(cadastro.doc || payloadOriginal.doc || "");

  if (el("multaValor")) {
    el("multaValor").value = payloadOriginal.valor || el("multaValor").value || "";
  }

  if (el("multaContrato")) {
    el("multaContrato").value = String(
      payloadOriginal.contrato || el("multaContrato").value || ""
    ).replace(/\D/g, "").slice(0, 9);
  }

  if (el("multaValidade")) {
    el("multaValidade").value = String(
      payloadOriginal.validade_dias_uteis || el("multaValidade").value || "30"
    ).replace(/\D/g, "") === "60" ? "60" : "30";
    atualizarValidadeMultaUI();
  }
}

async function submitCadastroCliente() {
  const cadastro = coletarCadastroCliente();

  if (!cadastro) {
    return;
  }

  const button = el("clientRegistrationSubmit");
  const payloadOriginal = clonePlain(state.pendingSapPayload) || {};
  const contextoFilaCliente = payloadOriginal?._queue_context?.source === "clientes_fila"
    ? clonePlain(payloadOriginal._queue_context)
    : null;
  const origem = state.clientRegistrationSource
    || (payloadOriginal._cadastro_manual ? "manual" : "boleto");

  try {
    button.disabled = true;
    button.textContent = "Criando cliente...";
    hideCadastroClienteFeedback();
    setStatus("Cadastrando cliente", "running");

    const apiCadastro = origem === "multa"
      ? window.pywebview.api.cadastrar_cliente_multa_contratual_sap
      : window.pywebview.api.cadastrar_cliente_sap;
    const resposta = await apiCadastro(cadastro);

    if (!resposta?.ok) {
      showCadastroClienteFeedback(resposta?.msg || "Não foi possível criar o cliente.");
      log(resposta?.msg || "Falha ao criar cliente.", "error");
      openLogsPopover();
      return;
    }

    if (origem === "multa") {
      preencherMultaAposCadastroCliente(cadastro, payloadOriginal);
    } else {
      preencherBoletoAposCadastroCliente(cadastro);
    }
    state.pendingSapAction = null;
    state.pendingSapPayload = null;
    state.clientRegistrationSource = "";
    fecharAbaCadastroCliente({ mostrarBoleto: false });
    if (origem === "multa") {
      showMultaContratualWorkspace({ status: false });
    } else {
      showBoletoWorkspace({ status: false });
    }

    if (origem === "manual") {
      showSimpleOperationalToast("Cliente criado. Complete os dados do boleto para continuar.");
      log("Cliente criado no SAP. Formulário de boletos preenchido com CPF/CNPJ e tipo solicitado.");
      setStatus("Cliente criado", "success");
      window.setTimeout(() => el("enderecoEmpreendimento")?.focus(), 180);
      return;
    }

    showSimpleOperationalToast("Cliente criado. Retomando pelo XD03.");
    log("Cliente criado no SAP. Retomando fluxo pelo XD03.");
    setStatus("Retomando pelo XD03", "running");
    if (origem === "multa") {
      showSimpleOperationalToast("Cliente criado. Retomando Multa Contratual.");
      log("Cliente criado no SAP. Retomando fluxo de Multa Contratual pelo XD03.");
      setStatus("Retomando Multa Contratual", "running");
      await gerarBoletoMultaContratual();
      return;
    }

    if (contextoFilaCliente && state.clientesFila.length) {
      const { startClientIndex, startPayloadIndex } =
        resolverInicioRetomadaFilaClientes(contextoFilaCliente);

      showSimpleOperationalToast("Cliente criado. Retomando fila de CPF/CNPJ.");
      log(
        `Cliente criado no SAP. Retomando fila de CPF/CNPJ a partir do item ` +
        `${startClientIndex + 1}/${state.clientesFila.length}.`
      );
      setStatus("Retomando fila CPF/CNPJ", "running");
      await executarFilaClientes(state.clientesFila.map(clonePlain), {
        startClientIndex,
        startPayloadIndex
      });
      return;
    }

    await gerarBoleto();
  } catch (error) {
    showCadastroClienteFeedback(`Falha ao criar cliente: ${error}`);
    log(`Falha ao criar cliente: ${error}`, "error");
    openLogsPopover();
  } finally {
    button.disabled = false;
    button.textContent = origem === "multa"
      ? "Criar cliente e continuar multa"
      : "Criar cliente e continuar";
  }
}

async function executarCriacaoSetoresPendentes() {
  const acao = clonePlain(state.pendingSapAction);
  const payload = clonePlain(state.pendingSapPayload);
  const button = el("sapActionConfirm");

  if (!acao || !payload) {
    log("Não foi possível criar setores: pendência ou payload ausente.", "error");
    openLogsPopover();
    return;
  }

  try {
    setMonitorMode("setor");
    resetarEtapas();

    if (button) {
      button.disabled = true;
      button.textContent = "Criando setores...";
    }

    setStatus("Cadastrando setores", "running");

    const resposta = await window.pywebview.api.adicionar_setores_cliente_sap({
      doc: acao.documento || payload.doc,
      tipo: payload.tipo,
      tipo_documento: acao.tipo_documento,
      cliente: acao.cliente,
      setores: acao.setores_necessarios || []
    });

    if (!resposta?.ok) {
      const mensagem = resposta?.msg || "Não foi possível criar os setores.";

      if (el("sapActionMessage")) {
        el("sapActionMessage").textContent = mensagem;
      }

      log(resposta?.msg || "Falha ao criar setores.", "error");
      openLogsPopover();
      return;
    }

    closeSapActionModal();
    showSimpleOperationalToast("Setores criados. Retomando fluxo padrão.");
    log(`Setores criados para o cliente ${acao.cliente || "--"}. Retomando fluxo padrão.`);
    state.pendingSapAction = null;
    if (payload.modalidade === "multa_contratual" || payload.tipo === "multa_contratual") {
      await executarFluxoMultaContratual(payload, { resume: false });
    } else {
      await executarFluxo(payload, { resume: false });
    }
  } catch (error) {
    if (el("sapActionMessage")) {
      el("sapActionMessage").textContent = `Falha ao criar setores: ${error}`;
    }

    log(`Falha ao criar setores: ${error}`, "error");
    openLogsPopover();
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "Criar setores e continuar";
    }
  }
}

async function confirmarAcaoSapPendente() {
  const acao = state.pendingSapAction;

  if (!acao) {
    closeSapActionModal();
    return;
  }

  if (acao.tipo === "cliente_nao_cadastrado") {
    closeSapActionModal();
    abrirAbaCadastroCliente();
    return;
  }

  if (acao.tipo === "setor_ausente") {
    await executarCriacaoSetoresPendentes();
  }
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
  "extratoResumoModal",
  "historyModal",
  "aboutModal",
  "batchConfirmModal",
  "sapActionModal",
  "cancelFlowModal"
];

function modalEstaAberto(id) {
  const modal = el(id);
  return modal && !modal.classList.contains("hidden");
}

function sincronizarLayoutDosModaisOperacionais() {
  const exibirEmConjunto =
    modalEstaAberto("pdfNameModal") &&
    modalEstaAberto("batchConfirmModal");

  if (exibirEmConjunto) {
    el("batchConfirmModal")?.classList.remove("batch-confirm-promote");
  }

  document.body.classList.toggle("operational-modals-split", exibirEmConjunto);
}

// Mantem o scroll preso no modal aberto, evitando que a tela de fundo role.
function sincronizarScrollDosModais() {
  const existeModalAberto = MODAL_IDS.some(modalEstaAberto);
  document.body.classList.toggle("modal-open", existeModalAberto);
  sincronizarLayoutDosModaisOperacionais();
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
  modal.classList.remove("batch-confirm-promote");
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
  lockSidebarCollapsed(true);
  openModal("aboutModal");
  carregarDiagnosticoSobre();
}

function closeAboutModal() {
  closeModal("aboutModal");
  lockSidebarCollapsed(false);
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
  state.currentPaymentFileNotice = "";
  state.lastPaymentFileNotice = "";
  window.clearTimeout(state.paymentFileCopiedTimer);
  state.operationalNoticeQueue = [];
  state.pendingSapAction = null;
  state.pendingSapPayload = null;
  state.clientRegistrationSource = "";
  const workspaceAtual = state.currentWorkspace;
  closePdfNameModal();
  closeSapActionModal();
  fecharAbaCadastroCliente({ mostrarBoleto: false });
  if (workspaceAtual === "multa") {
    limparFormularioMultaContratual();
    showMultaContratualWorkspace({ status: false });
  } else if (workspaceAtual === "extratos") {
    showExtratosWorkspace({ status: false });
  } else {
    showBoletoWorkspace({ status: false });
  }
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

  const enderecos = coletarEnderecosParaExecucao();

  if (!enderecos) {
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
  const multaSubmitButton = el("multaSubmitButton");
  const resumeButton = el("resumeButton");
  const cancelButton = el("cancelFlowButton");
  const multaCancelButton = el("multaCancelFlowButton");

  state.flowRunning = Boolean(isBusy);

  if (!isBusy) {
    state.cancelRequested = false;
  }

  submitButton.disabled = isBusy;
  submitButton.textContent = isBusy
    ? (mode === "batch" ? "Gerando lote..." : "Gerando...")
    : "Gerar Boleto";

  if (multaSubmitButton) {
    multaSubmitButton.disabled = isBusy;
    multaSubmitButton.textContent = isBusy
      ? (mode === "resume-multa" ? "Retomando multa..." : "Gerando multa...")
      : "Gerar Multa Contratual";
  }

  if (cancelButton) {
    cancelButton.disabled = !isBusy || state.cancelRequested;
    cancelButton.textContent = state.cancelRequested ? "Cancelando..." : "Cancelar criação";
  }

  if (multaCancelButton) {
    multaCancelButton.disabled = !isBusy || state.cancelRequested;
    multaCancelButton.textContent = state.cancelRequested ? "Cancelando..." : "Cancelar criação";
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

function aguardarConfirmacaoBoletoLote(payload, resultado, proximoPayload, atual, total) {
  return new Promise((resolve) => {
    const modal = el("batchConfirmModal");
    const message = el("batchConfirmMessage");
    const continueButton = el("batchConfirmContinue");
    const pauseButton = el("batchConfirmPause");
    const nome = payload.endereco?.empreendimento || `empreendimento ${atual}`;
    const proximoNome = proximoPayload?.endereco?.empreendimento || `empreendimento ${atual + 1}`;
    const docFat = resultado?.resultado?.doc_fat || resultado?.resultado?.faturamento || "--";

    message.textContent =
      `Boleto do empreendimento "${nome}" finalizado. Doc. fat: ${docFat}. ` +
      `Confirme para seguir para "${proximoNome}" (${atual + 1} de ${total}).`;

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
        resetProgress: false,
        clearFormOnSuccess: false
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
      removerPayloadConcluidoDaFilaEmpreendimentos(payload);

      if (index < payloads.length - 1) {
        const proximoPayload = payloads[index + 1];
        const proximoNome = payloads[index + 1]?.endereco?.empreendimento || `Empreendimento ${index + 2}`;
        setStatus(`Aguardando confirmação ${index + 1}/${total}`, "idle");
        log(`Aguardando confirmação do boleto de ${nome} para seguir para ${proximoNome}.`);

        const continuar = await aguardarConfirmacaoBoletoLote(
          payload,
          resultado,
          proximoPayload,
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
    limparFormularioCriacaoBoleto();
    setStatus("Lote concluído", "success");
    log("Todos os empreendimentos do lote foram processados.");
  } finally {
    state.batchRunning = false;
    setFlowButtonsBusy(false);
  }
}

function clienteFilaValido(cliente = {}) {
  const doc = limparDocumento(cliente.doc || "");
  const enderecos = Array.isArray(cliente.enderecos) ? cliente.enderecos : [];

  if (![11, 14].includes(doc.length)) {
    return { ok: false, msg: "CPF/CNPJ incompleto na fila de clientes." };
  }

  if (!cliente.tipo) {
    return { ok: false, msg: `Tipo de solicitacao ausente para ${formatarDocumentoResumo(doc)}.` };
  }

  if (!cliente.valor || !limparValor(cliente.valor)) {
    return { ok: false, msg: `Valor ausente para ${formatarDocumentoResumo(doc)}.` };
  }

  if (!enderecos.length) {
    return { ok: false, msg: `Nenhum empreendimento informado para ${formatarDocumentoResumo(doc)}.` };
  }

  return { ok: true };
}

function montarPayloadsClienteFila(cliente = {}, clienteIndex = 0, totalClientes = 1) {
  const enderecos = Array.isArray(cliente.enderecos) ? cliente.enderecos.map(cloneEndereco) : [];
  const queueId = garantirIdClienteFila(cliente);

  return enderecos.map((endereco, index) => ({
    doc: limparDocumento(cliente.doc || ""),
    tipo: cliente.tipo,
    valor: cliente.valor,
    modo_valor: cliente.modo_valor || "auto",
    endereco,
    _batch: {
      index: index + 1,
      total: enderecos.length,
      empreendimento: endereco.empreendimento
    },
    _clientBatch: {
      index: clienteIndex + 1,
      total: totalClientes,
      doc_formatado: cliente.doc_formatado || formatarDocumentoResumo(cliente.doc),
      tipo_label: cliente.tipo_label || getTipoSolicitacaoLabel(cliente.tipo)
    },
    _queue_context: {
      source: "clientes_fila",
      queueId,
      enderecoKey: chaveEnderecoFila(endereco),
      clienteIndex,
      payloadIndex: index,
      totalClientes,
      totalPayloadsCliente: enderecos.length
    }
  }));
}

function obterProximoItemFilaClientes(planos, clienteIndex, payloadIndex) {
  const clienteAtual = planos[clienteIndex];

  if (clienteAtual && payloadIndex + 1 < clienteAtual.payloads.length) {
    return {
      cliente: clienteAtual.cliente,
      payload: clienteAtual.payloads[payloadIndex + 1],
      clienteIndex,
      payloadIndex: payloadIndex + 1
    };
  }

  if (clienteIndex + 1 < planos.length) {
    const proximoCliente = planos[clienteIndex + 1];
    return {
      cliente: proximoCliente.cliente,
      payload: proximoCliente.payloads[0],
      clienteIndex: clienteIndex + 1,
      payloadIndex: 0
    };
  }

  return null;
}

function aguardarConfirmacaoFilaClientes(payload, resultado, proximo, atual, total) {
  return new Promise((resolve) => {
    const message = el("batchConfirmMessage");
    const continueButton = el("batchConfirmContinue");
    const pauseButton = el("batchConfirmPause");
    const nome = payload.endereco?.empreendimento || `boleto ${atual}`;
    const proximoNome = proximo?.payload?.endereco?.empreendimento || `boleto ${atual + 1}`;
    const proximoDoc = proximo?.cliente?.doc_formatado || formatarDocumentoResumo(proximo?.cliente?.doc);
    const docFat = resultado?.resultado?.doc_fat || resultado?.resultado?.faturamento || "--";

    message.textContent =
      `Boleto de "${nome}" finalizado. Doc. fat: ${docFat}. ` +
      `Confirme para seguir para ${proximoDoc} - "${proximoNome}" (${atual + 1} de ${total}).`;

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

async function executarFilaClientes(clientes, options = {}) {
  const planos = clientes.map((cliente, index) => ({
    cliente,
    payloads: montarPayloadsClienteFila(cliente, index, clientes.length)
  }));
  const totalBoletos = planos.reduce((total, item) => total + item.payloads.length, 0);
  const inicioCliente = Math.min(
    Math.max(0, Number(options.startClientIndex) || 0),
    Math.max(planos.length - 1, 0)
  );
  const inicioPayload = Math.max(0, Number(options.startPayloadIndex) || 0);
  const boletosIgnorados = planos.reduce((total, item, index) => {
    if (index < inicioCliente) {
      return total + item.payloads.length;
    }

    if (index === inicioCliente) {
      return total + Math.min(inicioPayload, Math.max(item.payloads.length - 1, 0));
    }

    return total;
  }, 0);
  let boletosConcluidos = boletosIgnorados;

  state.batchRunning = true;
  setFlowButtonsBusy(true, "batch");
  hideResumeBox();

  try {
    for (let clienteIndex = inicioCliente; clienteIndex < planos.length; clienteIndex += 1) {
      const plano = planos[clienteIndex];
      let checkpointCliente = null;
      const payloadInicial = clienteIndex === inicioCliente
        ? Math.min(inicioPayload, Math.max(plano.payloads.length - 1, 0))
        : 0;

      log(`Iniciando cliente ${clienteIndex + 1}/${planos.length}: ${plano.cliente.doc_formatado || formatarDocumentoResumo(plano.cliente.doc)}.`);

      for (let payloadIndex = payloadInicial; payloadIndex < plano.payloads.length; payloadIndex += 1) {
        const payload = plano.payloads[payloadIndex];
        const nome = payload.endereco?.empreendimento || `Empreendimento ${payloadIndex + 1}`;
        const resume = Boolean(payloadIndex > 0 && checkpointCliente);
        const resumoEndereco = formatarEnderecoResumo(payload.endereco || {});
        const posicao = boletosConcluidos + 1;

        window.resetarProgresso();
        log(`Fila CPF/CNPJ ${posicao}/${totalBoletos}: ${nome}.`);
        log(`Documento ${payload._clientBatch.doc_formatado} | ${payload._clientBatch.tipo_label}.`);
        log(`Endereco do empreendimento: ${resumoEndereco}.`);
        setStatus(`Fila ${posicao}/${totalBoletos}`, "running");
        processarEtapaTempoReal(
          "XD03",
          resume ? "concluido" : "processando",
          resume
            ? `Cliente ja validado. Seguindo com ${nome}.`
            : `Validando cliente ${payload._clientBatch.doc_formatado}.`,
          resume ? 100 : 8
        );

        const resultado = await executarFluxo(payload, {
          resume,
          checkpoint: checkpointCliente,
          manageButtons: false,
          resetProgress: false,
          clearFormOnSuccess: false
        });

        if (!resultado || !resultado.ok) {
          if (resultado?.cancelado) {
            log(`Fila cancelada em ${payload._clientBatch.doc_formatado} - ${nome}.`, "error");
            setStatus("Cancelado", "error");
          } else {
            log(`Fila pausada em ${payload._clientBatch.doc_formatado} - ${nome}.`, "error");
            setStatus("Falha no processamento", "error");
          }
          return;
        }

        boletosConcluidos += 1;
        checkpointCliente = montarCheckpointClienteParaProximo(payload, resultado) || checkpointCliente;
        log(`Concluido ${boletosConcluidos}/${totalBoletos}: ${payload._clientBatch.doc_formatado} - ${nome}.`);
        removerPayloadConcluidoDaFilaClientes(payload);

        const proximo = obterProximoItemFilaClientes(planos, clienteIndex, payloadIndex);

        if (proximo) {
          setStatus(`Aguardando confirmacao ${boletosConcluidos}/${totalBoletos}`, "idle");
          log(`Aguardando confirmacao para seguir para ${proximo.cliente.doc_formatado || formatarDocumentoResumo(proximo.cliente.doc)}.`);

          const continuar = await aguardarConfirmacaoFilaClientes(
            payload,
            resultado,
            proximo,
            boletosConcluidos,
            totalBoletos
          );

          if (!continuar) {
            log("Fila de CPF/CNPJ pausada pelo usuario.");
            setStatus("Fila pausada", "idle");
            return;
          }
        }
      }
    }

    limparFilaClientes();
    limparFilaEmpreendimentos();
    limparFormularioCriacaoBoleto();
    setStatus("Fila concluida", "success");
    log("Todos os CPF/CNPJ da fila foram processados.");
  } finally {
    state.batchRunning = false;
    setFlowButtonsBusy(false);
  }
}

function limparFormularioMultaContratual() {
  atualizarDocumentoMultaUI("");

  if (el("multaValor")) {
    el("multaValor").value = "";
  }

  if (el("multaContrato")) {
    el("multaContrato").value = "";
  }

  if (el("multaValidade")) {
    el("multaValidade").value = "30";
  }

  atualizarValidadeMultaUI();

  limparMensagemCampo("multaDoc");
  limparMensagemCampo("multaValor");
  limparMensagemCampo("multaContrato");
  limparMensagemCampo("multaValidade");
}

function montarPayloadMultaContratual() {
  const docInfo = analisarDocumento(el("multaDoc")?.value || "");
  const valor = el("multaValor")?.value || "";
  const contrato = String(el("multaContrato")?.value || "").replace(/\D/g, "").slice(0, 9);
  const validadeDias = String(el("multaValidade")?.value || "30").replace(/\D/g, "");

  limparMensagemCampo("multaDoc");
  limparMensagemCampo("multaValor");
  limparMensagemCampo("multaContrato");
  limparMensagemCampo("multaValidade");

  if (![11, 14].includes(docInfo.digitos.length)) {
    mostrarErroCampo("multaDoc", "Informe CPF ou CNPJ completo para gerar a multa contratual.");
    return null;
  }

  if (!limparValor(valor) || Number(limparValor(valor)) <= 0) {
    mostrarErroCampo("multaValor", "Informe o valor da Multa Contratual.");
    return null;
  }

  if (!contrato) {
    mostrarErroCampo("multaContrato", "Informe o nÃºmero do contrato.");
    return null;
  }

  if (!["30", "60"].includes(validadeDias)) {
    mostrarErroCampo("multaValidade", "Selecione a data de validade da multa contratual.");
    return null;
  }

  return {
    doc: docInfo.digitos,
    tipo: "multa_contratual",
    modalidade: "multa_contratual",
    valor,
    contrato,
    validade_dias_uteis: validadeDias
  };
}

async function executarFluxoMultaContratual(payload, options = {}) {
  const {
    resume = false,
    checkpoint = null,
    manageButtons = true,
    resetProgress = true,
    clearFormOnSuccess = true
  } = options;
  const resumeCheckpoint = resume
    ? cloneCheckpoint(checkpoint || state.resumeCheckpoint)
    : null;

  setMonitorMode("multa");

  if (!resume) {
    hideResumeBox();
    if (resetProgress) {
      window.resetarProgresso();
    }
    setStatus("Processando Multa Contratual", "running");
  } else {
    if (!resumeCheckpoint || !resumeCheckpoint.resume_from) {
      log("NÃ£o foi possÃ­vel retomar: checkpoint ausente ou invÃ¡lido.", "error");
      setStatus("Falha no processamento", "error");
      openLogsPopover();
      return { ok: false, msg: "Checkpoint ausente ou invÃ¡lido." };
    }

    hideResumeBox(false);
    setStatus("Retomando Multa Contratual", "running");
    log(`Retomando Multa Contratual a partir de ${resumeCheckpoint.resume_from}.`);
  }

  if (manageButtons) {
    setFlowButtonsBusy(true, resume ? "resume-multa" : "multa");
  }

  try {
    const dados = {
      ...payload,
      tipo: "multa_contratual",
      modalidade: "multa_contratual",
      _resume_checkpoint: resumeCheckpoint
    };

    const res = await window.pywebview.api.gerar_boleto_multa_contratual(dados);
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

      if (res.msg && !(Array.isArray(res.logs) && res.logs.length)) {
        log(res.msg, "error");
      }

      if (res.acao_pendente?.tipo === "setor_ausente") {
        setPendingSapAction(res.acao_pendente, dados);
        hideResumeBox();
        log("Setor MC ausente identificado. Criando setor automaticamente para Multa Contratual.");
        await executarCriacaoSetoresPendentes();
        return res;
      }

      if (res.acao_pendente && openSapActionModal(res.acao_pendente, dados)) {
        hideResumeBox();
        setStatus("Aguardando cadastro MC", "idle");
        openLogsPopover();
        return res;
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
    setStatus("ConcluÃ­do", "success");

    if (clearFormOnSuccess) {
      limparFormularioMultaContratual();
    }

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

async function gerarBoletoMultaContratual() {
  const payload = montarPayloadMultaContratual();

  if (!payload) {
    return;
  }

  await executarFluxoMultaContratual(payload, { resume: false });
}

// Chama a API Python para iniciar ou retomar o fluxo SAP.
async function executarFluxo(payload, options = {}) {
  const {
    resume = false,
    checkpoint = null,
    manageButtons = true,
    resetProgress = true,
    clearFormOnSuccess = true
  } = options;
  const resumeCheckpoint = resume
    ? cloneCheckpoint(checkpoint || state.resumeCheckpoint)
    : null;

  setMonitorMode("boletos");

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

      if (res.msg && !(Array.isArray(res.logs) && res.logs.length)) {
        log(res.msg, "error");
      }

      if (res.acao_pendente?.tipo === "setor_ausente") {
        setPendingSapAction(res.acao_pendente, payload);
        hideResumeBox();
        log("Setor ausente identificado. Criando setor automaticamente pelo tipo de solicitação informado.");
        await executarCriacaoSetoresPendentes();
        return res;
      }

      if (res.acao_pendente && openSapActionModal(res.acao_pendente, payload)) {
        hideResumeBox();
        setStatus("Aguardando cadastro", "idle");
        openLogsPopover();
        return res;
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
    if (clearFormOnSuccess) {
      limparFormularioCriacaoBoleto();
    }
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
  if (state.clientesFila.length) {
    state.clientesFila.forEach(garantirIdClienteFila);
    renderizarFilaClientes();

    const invalido = state.clientesFila
      .map((cliente) => clienteFilaValido(cliente))
      .find((resultado) => !resultado.ok);

    if (invalido) {
      setStatus("Revise a fila", "error");
      log(invalido.msg, "error");
      openLogsPopover();
      return;
    }

    await executarFilaClientes(state.clientesFila.map(clonePlain));
    return;
  }

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

  const isMulta = state.currentWorkspace === "multa"
    || checkpoint?.contexto?.tipo === "multa_contratual";
  const payload = isMulta
    ? montarPayloadMultaContratual()
    : montarPayloadAtual();

  if (!payload) {
    return;
  }

  if (isMulta) {
    await executarFluxoMultaContratual(payload, { resume: true, checkpoint });
  } else {
    await executarFluxo(payload, { resume: true, checkpoint });
  }
}

document.addEventListener("click", (event) => {
  const menu = el("valueMenu");
  const valueButton = el("valueModeButton");
  const tipoMenu = el("tipoMenu");
  const tipoButton = el("tipoButton");
  const cadastroTipoMenu = el("clienteCadastroTipoMenu");
  const cadastroTipoButton = el("clienteCadastroTipoButton");
  const cadastroTituloMenu = el("clienteCadastroTituloMenu");
  const cadastroTituloButton = el("clienteCadastroTituloButton");
  const popover = el("logPopover");
  const balloon = el("logBalloon");
  const card = el("contactCard");
  const modal = el("contactModal");
  const cancelModal = el("cancelFlowModal");
  const sapActionModal = el("sapActionModal");

  if (menu && valueButton && !menu.contains(event.target) && !valueButton.contains(event.target)) {
    fecharMenuValor();
  }

  if (tipoMenu && tipoButton && !tipoMenu.contains(event.target) && !tipoButton.contains(event.target)) {
    fecharMenuTipo();
  }

  if (
    cadastroTipoMenu &&
    cadastroTipoButton &&
    !cadastroTipoMenu.contains(event.target) &&
    !cadastroTipoButton.contains(event.target)
  ) {
    fecharCadastroTipoMenu();
  }

  if (
    cadastroTituloMenu &&
    cadastroTituloButton &&
    !cadastroTituloMenu.contains(event.target) &&
    !cadastroTituloButton.contains(event.target)
  ) {
    fecharCadastroTituloMenu();
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

  if (
    sapActionModal &&
    !sapActionModal.classList.contains("hidden") &&
    event.target.classList.contains("contact-backdrop")
  ) {
    cancelarAcaoSapPendente();
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
    closePdfNameModal();
    processarProximoAvisoOperacional();
    return;
  }

  if (modalEstaAberto("historyModal")) {
    closeHistoryModal();
    return;
  }

  if (modalEstaAberto("cancelFlowModal")) {
    closeCancelFlowModal();
    return;
  }

  if (modalEstaAberto("sapActionModal")) {
    cancelarAcaoSapPendente();
  }
});

el("valor").addEventListener("input", handleValorInput);
window.addEventListener("resize", atualizarEscalaLogo);

inicializarTema();
atualizarEscalaLogo();
setBaseStatus("active");
construirEtapas();
atualizarDocumentoUI("");
atualizarDocumentoMultaUI("");
atualizarValidadeMultaUI();
atualizarTipo();
atualizarModoValorUI();
preencherMesAnoExtratosPadrao(true);
registrarValidacaoInterativa();
registrarCepAutocomplete();
updateContactCharCount();
handleContactImages();
setEmpreendimentoAberto(false);
setSemNumero(false);
setSemCep(false);
renderizarFilaEmpreendimentos();
renderizarFilaClientes();
carregarRascunhosClientes();
limparPainel();
atualizarRodapeInfo();
window.setInterval(atualizarRodapeInfo, 1000);
