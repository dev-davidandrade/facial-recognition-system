const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const DECISIONS = {
  identified: { label: "Identificado", tone: "success", icon: "✓" },
  unknown: { label: "Não identificado", tone: "warning", icon: "?" },
  ambiguous: { label: "Resultado ambíguo", tone: "warning", icon: "≈" },
  no_face: { label: "Nenhum rosto encontrado", tone: "warning", icon: "—" },
  multiple_faces: { label: "Múltiplos rostos", tone: "warning", icon: "+" },
  low_quality: { label: "Qualidade insuficiente", tone: "warning", icon: "!" },
  spoof_suspected: { label: "Possível fraude", tone: "error", icon: "!" },
  processing_error: { label: "Falha no processamento", tone: "error", icon: "×" },
};

const REASONS = {
  identification_match: "A identidade mais próxima ultrapassou o limiar e a margem mínima.",
  verification_match: "As duas imagens ultrapassaram o limiar de similaridade.",
  similarity_below_threshold: "A similaridade ficou abaixo do limiar configurado.",
  candidate_margin_too_small: "Os dois melhores candidatos ficaram próximos demais.",
  no_face_detected: "Nenhum rosto foi detectado na imagem.",
  multiple_faces_detected: "A imagem deve conter exatamente um rosto.",
  quality_rejected: "A imagem não passou pelos critérios mínimos de qualidade.",
  first_image_no_face_detected: "Nenhum rosto foi encontrado na primeira imagem.",
  second_image_no_face_detected: "Nenhum rosto foi encontrado na segunda imagem.",
  first_image_multiple_faces_detected: "A primeira imagem contém mais de um rosto.",
  second_image_multiple_faces_detected: "A segunda imagem contém mais de um rosto.",
  first_image_quality_rejected: "A primeira imagem não passou pela análise de qualidade.",
  second_image_quality_rejected: "A segunda imagem não passou pela análise de qualidade.",
  no_compatible_templates: "Não existem templates compatíveis com os modelos ativos.",
  no_active_templates: "A galeria ainda não possui templates ativos.",
  candidate_not_active: "O candidato encontrado não está ativo.",
  face_processing_failed: "Não foi possível concluir o processamento facial.",
};

const QUALITY_REASONS = {
  image_too_blurry: "imagem com pouca nitidez",
  image_too_dark: "imagem escura demais",
  image_too_bright: "imagem clara demais",
  face_too_small: "rosto pequeno demais",
  empty_crop: "não foi possível recortar o rosto",
};

const state = {
  activePerson: loadPerson(),
  previewUrls: new Map(),
  enrollmentCamera: {
    stream: null,
    frames: [],
    previewUrls: [],
    capturing: false,
    personId: null,
  },
  live: {
    stream: null,
    running: false,
    timer: null,
    observations: [],
    startedAt: null,
    lastObservedAt: null,
    policy: {
      confirmations_required: 3,
      window_size: 5,
      max_gap_ms: 1000,
      review_after_ms: 5000,
      frame_interval_ms: 350,
    },
  },
};

function loadPerson() {
  try {
    return JSON.parse(localStorage.getItem("face-access-last-person") || "null");
  } catch {
    return null;
  }
}

function savePerson(person) {
  state.activePerson = person;
  localStorage.setItem("face-access-last-person", JSON.stringify(person));
  renderActivePerson();
}

function navigate(view) {
  if (view !== "identification" && state.live.running) stopLive();
  if (view !== "enrollment") {
    releaseEnrollmentCamera();
    if (state.enrollmentCamera.frames.length) clearEnrollmentFrames({ notify: false });
  }
  $$("[data-view-panel]").forEach((panel) => {
    panel.classList.toggle("is-visible", panel.dataset.viewPanel === view);
  });
  $$(".nav-item").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === view);
  });
  history.replaceState(null, "", `#${view}`);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setChip(element, text, stateName) {
  element.classList.remove("is-ok", "is-error");
  if (stateName) element.classList.add(`is-${stateName}`);
  element.lastChild.textContent = ` ${text}`;
}

function setHealthValue(valueId, detailId, value, detail, stateName) {
  const valueElement = $(valueId);
  valueElement.textContent = value;
  valueElement.classList.remove("is-ok", "is-error");
  if (stateName) valueElement.classList.add(`is-${stateName}`);
  $(detailId).textContent = detail;
}

async function refreshHealth() {
  const apiChip = $("#api-status");
  const readyChip = $("#ready-status");
  try {
    const health = await apiRequest("/health");
    setChip(apiChip, "API online", "ok");
    setHealthValue(
      "#health-api-value",
      "#health-api-detail",
      "online",
      `${health.service} · versão ${health.version}`,
      "ok",
    );
  } catch {
    setChip(apiChip, "API offline", "error");
    setHealthValue("#health-api-value", "#health-api-detail", "offline", "O serviço não respondeu.", "error");
    return;
  }

  try {
    const response = await fetch("/ready", { headers: { Accept: "application/json" } });
    const ready = await response.json();
    const isReady = response.ok && ready.status === "ready";
    setChip(readyChip, isReady ? "sistema pronto" : "atenção necessária", isReady ? "ok" : "error");

    const database = ready.checks?.database || "desconhecido";
    const modelsReady = [ready.checks?.yunet_model, ready.checks?.sface_model].every(
      (value) => value === "ready",
    );
    setHealthValue(
      "#health-db-value",
      "#health-db-detail",
      database === "ready" ? "pronto" : database,
      database === "ready" ? "PostgreSQL e pgvector respondendo." : "Verifique o serviço do banco.",
      database === "ready" || database === "disabled" ? "ok" : "error",
    );
    setHealthValue(
      "#health-model-value",
      "#health-model-detail",
      modelsReady ? "prontos" : "incompletos",
      modelsReady ? "YuNet e SFace encontrados localmente." : "Baixe ou valide os pesos configurados.",
      modelsReady ? "ok" : "error",
    );
  } catch {
    setChip(readyChip, "readiness indisponível", "error");
  }
}

async function apiRequest(url, options = {}) {
  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers: { Accept: "application/json", ...(options.headers || {}) },
    });
  } catch {
    throw new Error("Não foi possível alcançar a API local.");
  }

  if (response.status === 204) return null;
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(formatApiError(body?.detail, response.status));
  return body;
}

function formatApiError(detail, status) {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    if (Number.isInteger(detail.accepted_images) && Number.isInteger(detail.required_images)) {
      const total = detail.accepted_images + (detail.rejected_images || 0);
      const firstReason = detail.quality?.reasons?.[0];
      const reason = firstReason ? ` Primeiro descarte: ${QUALITY_REASONS[firstReason] || firstReason}.` : "";
      return `Apenas ${detail.accepted_images} de ${total} quadros foram aceitos; são necessários pelo menos ${detail.required_images}.${reason}`;
    }
    const base = REASONS[detail.reason_code] || detail.message || detail.reason_code || `Erro HTTP ${status}`;
    const position = Number.isInteger(detail.image_index) ? ` (imagem ${detail.image_index + 1})` : "";
    const quality = detail.quality?.reasons?.length
      ? `: ${detail.quality.reasons.map((reason) => QUALITY_REASONS[reason] || reason).join(", ")}`
      : "";
    return `${base}${position}${quality}`;
  }
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join("; ");
  return `A solicitação falhou com o código ${status}.`;
}

function withBusy(form, task) {
  const button = $("button[type='submit']", form);
  return withButtonBusy(button, task);
}

function withButtonBusy(button, task) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Processando…";
  return task().finally(() => {
    button.disabled = false;
    button.textContent = original;
  });
}

let toastTimer;
function toast(message, type = "ok") {
  const element = $("#toast");
  element.textContent = message;
  element.classList.toggle("is-error", type === "error");
  element.classList.add("is-visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => element.classList.remove("is-visible"), 3500);
}

function clearPreview(preview) {
  const oldUrls = state.previewUrls.get(preview.id) || [];
  oldUrls.forEach((url) => URL.revokeObjectURL(url));
  state.previewUrls.delete(preview.id);
  preview.replaceChildren();
  preview.classList.remove("has-image");
}

function renderFiles(input, preview, countElement = null) {
  clearPreview(preview);
  const files = [...input.files];
  if (countElement) {
    countElement.textContent = files.length
      ? `${files.length} ${files.length === 1 ? "imagem selecionada" : "imagens selecionadas"}`
      : "Nenhuma imagem selecionada";
  }
  const urls = [];
  files.forEach((file, index) => {
    const image = document.createElement("img");
    const url = URL.createObjectURL(file);
    urls.push(url);
    image.src = url;
    image.alt = `Pré-visualização ${index + 1}`;
    preview.append(image);
  });
  state.previewUrls.set(preview.id, urls);
  preview.classList.toggle("has-image", files.length > 0);
}

function setupDropzone(inputId, previewId, countId = null) {
  const input = $(inputId);
  const preview = $(previewId);
  const zone = input.closest(".dropzone");
  const count = countId ? $(countId) : null;

  input.addEventListener("change", () => renderFiles(input, preview, count));
  ["dragenter", "dragover"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      zone.classList.add("is-dragging");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      zone.classList.remove("is-dragging");
    });
  });
  zone.addEventListener("drop", (event) => {
    if (!event.dataTransfer?.files?.length) return;
    const transfer = new DataTransfer();
    [...event.dataTransfer.files].forEach((file) => transfer.items.add(file));
    input.files = transfer.files;
    renderFiles(input, preview, count);
  });
}

function renderActivePerson() {
  const summary = $("#person-summary");
  if (!state.activePerson) {
    summary.classList.add("is-hidden");
    return;
  }
  const name = state.activePerson.display_name || state.activePerson.external_id || "Pessoa sem nome";
  $("#person-summary-name").textContent = name;
  $("#person-summary-id").textContent = state.activePerson.id;
  $("#person-avatar").textContent = name.trim().charAt(0).toUpperCase() || "?";
  $("#enroll-person-id").value = state.activePerson.id;
  summary.classList.remove("is-hidden");
}

function formatNumber(value, digits = 3) {
  return typeof value === "number" ? value.toFixed(digits) : "—";
}

function resultCard({ tone = "success", icon = "✓", eyebrow, title, subtitle, metrics = [], score, raw }) {
  const card = document.createElement("div");
  card.className = `result-card is-${tone}`;

  const verdict = document.createElement("div");
  verdict.className = "result-verdict";
  const verdictIcon = document.createElement("span");
  verdictIcon.className = "verdict-icon";
  verdictIcon.textContent = icon;
  const copy = document.createElement("div");
  const small = document.createElement("small");
  small.textContent = eyebrow;
  const strong = document.createElement("strong");
  strong.textContent = title;
  const detail = document.createElement("span");
  detail.textContent = subtitle;
  copy.append(small, strong, detail);
  verdict.append(verdictIcon, copy);
  card.append(verdict);

  if (typeof score === "number") {
    const track = document.createElement("div");
    track.className = "score-track";
    const fill = document.createElement("span");
    fill.style.width = `${Math.max(0, Math.min(100, score * 100))}%`;
    track.append(fill);
    card.append(track);
  }

  if (metrics.length) {
    const grid = document.createElement("div");
    grid.className = "metric-grid";
    metrics.forEach(([label, value]) => {
      const metric = document.createElement("div");
      metric.className = "metric";
      const metricLabel = document.createElement("small");
      metricLabel.textContent = label;
      const metricValue = document.createElement("strong");
      metricValue.textContent = value;
      metric.append(metricLabel, metricValue);
      grid.append(metric);
    });
    card.append(grid);
  }

  if (raw) {
    const details = document.createElement("details");
    details.className = "raw-result";
    const summary = document.createElement("summary");
    summary.textContent = "Ver resposta técnica";
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(raw, null, 2);
    details.append(summary, pre);
    card.append(details);
  }
  return card;
}

function renderError(container, error) {
  container.replaceChildren(
    resultCard({
      tone: "error",
      icon: "×",
      eyebrow: "SOLICITAÇÃO NÃO CONCLUÍDA",
      title: "Não foi possível processar",
      subtitle: error.message || "Ocorreu um erro inesperado.",
    }),
  );
}

function renderIdentification(container, data) {
  const decision = DECISIONS[data.biometric_decision] || DECISIONS.processing_error;
  const identity = data.display_name || data.external_id || decision.label;
  const quality = data.quality;
  container.replaceChildren(
    resultCard({
      tone: decision.tone,
      icon: decision.icon,
      eyebrow: decision.label.toUpperCase(),
      title: identity,
      subtitle: REASONS[data.reason_code] || data.reason_code,
      score: data.best_similarity,
      metrics: [
        ["Similaridade", formatNumber(data.best_similarity)],
        ["Limiar", formatNumber(data.threshold)],
        ["Margem", formatNumber(data.score_margin)],
        ["Tempo", `${formatNumber(data.processing_time_ms, 1)} ms`],
        ["Qualidade", quality ? formatNumber(quality.score) : "—"],
        ["Brilho", quality ? formatNumber(quality.brightness, 1) : "—"],
      ],
      raw: data,
    }),
  );
}

const ENROLLMENT_CAPTURE_PROMPTS = [
  "Olhe de frente",
  "Vire levemente para a esquerda",
  "Volte ao centro",
  "Vire levemente para a direita",
  "Finalize olhando de frente",
];

function setEnrollMode(mode) {
  if (mode !== "camera") releaseEnrollmentCamera();
  $$('[data-enroll-mode]').forEach((button) => {
    const selected = button.dataset.enrollMode === mode;
    button.classList.toggle("is-active", selected);
    button.setAttribute("aria-selected", String(selected));
  });
  $$('[data-enroll-panel]').forEach((panel) => {
    panel.classList.toggle("is-hidden", panel.dataset.enrollPanel !== mode);
  });
}

function setEnrollmentCameraState(text) {
  $("#enroll-camera-state span").textContent = text;
}

function releaseEnrollmentCamera({ keepLastFrame = false } = {}) {
  state.enrollmentCamera.capturing = false;
  if (state.enrollmentCamera.stream) {
    state.enrollmentCamera.stream.getTracks().forEach((track) => track.stop());
  }
  state.enrollmentCamera.stream = null;
  $("#enroll-capture-prompt").classList.add("is-hidden");
  $("#open-enroll-camera").disabled = false;
  $("#open-enroll-camera").textContent = keepLastFrame ? "Reabrir câmera" : "Ativar câmera";
  $("#capture-enroll-frames").disabled = true;
  if (!keepLastFrame) {
    $("#enroll-video").srcObject = null;
    $("#enroll-camera-stage").classList.remove("is-streaming");
    setEnrollmentCameraState("Câmera desligada");
  }
}

function renderEnrollmentFrames() {
  state.enrollmentCamera.previewUrls.forEach((url) => URL.revokeObjectURL(url));
  state.enrollmentCamera.previewUrls = [];
  const preview = $("#enroll-camera-preview");
  preview.replaceChildren();
  state.enrollmentCamera.frames.forEach((frame, index) => {
    const url = URL.createObjectURL(frame);
    state.enrollmentCamera.previewUrls.push(url);
    const image = document.createElement("img");
    image.src = url;
    image.alt = `Amostra da webcam ${index + 1}`;
    preview.append(image);
  });
  const hasFrames = state.enrollmentCamera.frames.length > 0;
  $("#captured-samples").classList.toggle("is-hidden", !hasFrames);
  $("#clear-enroll-frames").disabled = state.enrollmentCamera.capturing;
  $("#submit-enroll-camera").disabled = state.enrollmentCamera.frames.length < 2;
}

function clearEnrollmentFrames({ notify = true } = {}) {
  state.enrollmentCamera.frames = [];
  state.enrollmentCamera.personId = null;
  renderEnrollmentFrames();
  if (notify) toast("Amostras temporárias descartadas.");
}

async function openEnrollmentCamera() {
  const personId = $("#enroll-person-id").value.trim();
  if (!personId) {
    toast("Crie ou consulte uma pessoa antes de ativar a câmera.", "error");
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    renderError($("#enroll-result"), new Error("Este navegador não oferece acesso à webcam."));
    return;
  }
  stopLive();
  releaseEnrollmentCamera();
  $("#open-enroll-camera").disabled = true;
  setEnrollmentCameraState("Solicitando câmera…");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        facingMode: "user",
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
    });
    const video = $("#enroll-video");
    video.srcObject = stream;
    await video.play();
    state.enrollmentCamera.stream = stream;
    $("#enroll-camera-stage").classList.add("is-streaming");
    $("#open-enroll-camera").disabled = true;
    $("#open-enroll-camera").textContent = "Câmera ativa";
    $("#capture-enroll-frames").disabled = false;
    setEnrollmentCameraState("Pronta para capturar");
  } catch (error) {
    releaseEnrollmentCamera();
    const message = cameraErrorMessage(error);
    setEnrollmentCameraState("Câmera indisponível");
    renderError($("#enroll-result"), new Error(message));
  }
}

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function captureEnrollmentFrames() {
  if (!state.enrollmentCamera.stream || state.enrollmentCamera.capturing) return;
  const personId = $("#enroll-person-id").value.trim();
  if (!personId) return toast("Informe a pessoa que receberá o cadastro.", "error");

  state.enrollmentCamera.frames = [];
  state.enrollmentCamera.personId = personId;
  state.enrollmentCamera.capturing = true;
  renderEnrollmentFrames();
  $("#capture-enroll-frames").disabled = true;
  const prompt = $("#enroll-capture-prompt");
  prompt.classList.remove("is-hidden");
  setEnrollmentCameraState("Coletando amostras");

  try {
    for (let index = 0; index < ENROLLMENT_CAPTURE_PROMPTS.length; index += 1) {
      if (!state.enrollmentCamera.capturing || !state.enrollmentCamera.stream) return;
      $("strong", prompt).textContent = ENROLLMENT_CAPTURE_PROMPTS[index];
      $("span", prompt).textContent = `${index + 1} de ${ENROLLMENT_CAPTURE_PROMPTS.length}`;
      await wait(index === 0 ? 1000 : 900);
      if (!state.enrollmentCamera.capturing || !state.enrollmentCamera.stream) return;
      const frame = await captureVideoFrame($("#enroll-video"), $("#enroll-canvas"));
      state.enrollmentCamera.frames.push(frame);
      renderEnrollmentFrames();
    }
    state.enrollmentCamera.capturing = false;
    prompt.classList.add("is-hidden");
    setEnrollmentCameraState("5 quadros prontos");
    releaseEnrollmentCamera({ keepLastFrame: true });
    renderEnrollmentFrames();
    toast("Cinco quadros capturados. Revise e confirme o cadastro.");
  } catch (error) {
    releaseEnrollmentCamera();
    renderError($("#enroll-result"), error);
  }
}

function setIdentifyMode(mode) {
  if (mode !== "live") stopLive();
  $$('[data-identify-mode]').forEach((button) => {
    const selected = button.dataset.identifyMode === mode;
    button.classList.toggle("is-active", selected);
    button.setAttribute("aria-selected", String(selected));
  });
  $$('[data-identify-panel]').forEach((panel) => {
    panel.classList.toggle("is-hidden", panel.dataset.identifyPanel !== mode);
  });
  const result = $("#identify-result");
  result.replaceChildren();
  const placeholder = document.createElement("span");
  placeholder.className = "result-placeholder";
  placeholder.textContent = mode === "live"
    ? "Inicie a câmera. A análise começará automaticamente quando um rosto aparecer."
    : "Aguardando uma imagem para análise.";
  result.append(placeholder);
}

async function loadTemporalPolicy() {
  try {
    state.live.policy = await apiRequest("/v1/identifications/temporal-policy");
  } catch {
    toast("Usando a política temporal padrão da interface.", "error");
  }
  resetTemporalSession();
}

function resetTemporalSession() {
  state.live.observations = [];
  state.live.startedAt = null;
  state.live.lastObservedAt = null;
  const policy = state.live.policy;
  $("#temporal-title").textContent = "Confirmação temporal";
  $("#temporal-detail").textContent = (
    `${policy.confirmations_required} confirmações da mesma pessoa em `
    + `${policy.window_size} quadros.`
  );
  renderFrameDots();
}

function dominantCandidate() {
  const candidates = new Map();
  state.live.observations.forEach((observation) => {
    if (!observation.personId) return;
    const current = candidates.get(observation.personId) || { count: 0, result: observation.result };
    current.count += 1;
    if ((observation.result.best_similarity || 0) >= (current.result.best_similarity || 0)) {
      current.result = observation.result;
    }
    candidates.set(observation.personId, current);
  });
  return [...candidates.entries()]
    .map(([personId, candidate]) => ({ personId, ...candidate }))
    .sort((first, second) => second.count - first.count)[0] || null;
}

function renderFrameDots(targetPersonId = null) {
  const container = $("#frame-dots");
  container.replaceChildren();
  const observations = state.live.observations;
  for (let index = 0; index < state.live.policy.window_size; index += 1) {
    const dot = document.createElement("span");
    dot.className = "frame-dot";
    const observation = observations[index];
    if (observation) {
      const matchesTarget = observation.personId
        && (!targetPersonId || observation.personId === targetPersonId);
      dot.classList.add(matchesTarget ? "is-match" : "is-rejected");
      dot.title = matchesTarget ? "Identidade compatível" : "Quadro sem confirmação";
    } else {
      dot.title = "Aguardando quadro";
    }
    container.append(dot);
  }
}

function setCameraState(text) {
  $("#camera-state span").textContent = text;
}

function releaseCamera({ keepLastFrame = false } = {}) {
  clearTimeout(state.live.timer);
  state.live.timer = null;
  state.live.running = false;
  if (state.live.stream) {
    state.live.stream.getTracks().forEach((track) => track.stop());
  }
  state.live.stream = null;
  if (!keepLastFrame) {
    $("#live-video").srcObject = null;
    $("#camera-stage").classList.remove("is-streaming", "is-confirmed", "is-review");
  }
  $("#start-live").disabled = false;
  $("#start-live").textContent = keepLastFrame ? "Nova tentativa" : "Iniciar câmera";
  $("#stop-live").disabled = true;
}

function stopLive() {
  const wasRunning = state.live.running;
  releaseCamera();
  resetTemporalSession();
  setCameraState("Câmera desligada");
  if (wasRunning) toast("Câmera encerrada.");
}

function cameraErrorMessage(error) {
  if (error?.name === "NotAllowedError") {
    return "A permissão da câmera foi negada. Libere o acesso do localhost no navegador.";
  }
  if (error?.name === "NotFoundError") return "Nenhuma câmera disponível foi encontrada.";
  if (error?.name === "NotReadableError") return "A câmera está sendo usada por outro aplicativo.";
  return "Não foi possível iniciar a câmera neste navegador.";
}

async function startLive() {
  if (!navigator.mediaDevices?.getUserMedia) {
    renderError($("#identify-result"), new Error("Este navegador não oferece acesso à webcam."));
    return;
  }
  releaseCamera();
  resetTemporalSession();
  const stage = $("#camera-stage");
  stage.classList.remove("is-confirmed", "is-review");
  $("#start-live").disabled = true;
  setCameraState("Solicitando câmera…");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        facingMode: "user",
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
    });
    const video = $("#live-video");
    video.srcObject = stream;
    await video.play();
    state.live.stream = stream;
    state.live.running = true;
    stage.classList.add("is-streaming");
    $("#start-live").disabled = true;
    $("#start-live").textContent = "Analisando…";
    $("#stop-live").disabled = false;
    setCameraState("Aguardando rosto");
    analyzeLiveFrame();
  } catch (error) {
    releaseCamera();
    const message = cameraErrorMessage(error);
    setCameraState("Câmera indisponível");
    renderError($("#identify-result"), new Error(message));
  }
}

function captureVideoFrame(video, canvas) {
  if (!video.videoWidth || !video.videoHeight) {
    return Promise.reject(new Error("A câmera ainda não produziu um quadro."));
  }
  const width = Math.min(video.videoWidth, 960);
  const height = Math.round(width * (video.videoHeight / video.videoWidth));
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", { alpha: false });
  context.drawImage(video, 0, 0, width, height);
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => blob ? resolve(blob) : reject(new Error("Falha ao preparar o quadro.")),
      "image/jpeg",
      0.86,
    );
  });
}

function finishTemporalConfirmation(candidate) {
  const result = candidate.result;
  const policy = state.live.policy;
  $("#camera-stage").classList.add("is-confirmed");
  setCameraState("Identidade confirmada");
  $("#temporal-title").textContent = "Confirmação concluída";
  $("#temporal-detail").textContent = (
    `${candidate.count}/${policy.confirmations_required} confirmações compatíveis.`
  );
  releaseCamera({ keepLastFrame: true });
  $("#identify-result").replaceChildren(
    resultCard({
      tone: "success",
      icon: "✓",
      eyebrow: "IDENTIDADE CONFIRMADA NO TEMPO",
      title: result.display_name || result.external_id || "Pessoa cadastrada",
      subtitle: "A mesma identidade apareceu repetidamente na janela de quadros.",
      score: result.best_similarity,
      metrics: [
        ["Confirmações", `${candidate.count}/${policy.confirmations_required}`],
        ["Janela", `${policy.window_size} quadros`],
        ["Similaridade", formatNumber(result.best_similarity)],
        ["Tempo por quadro", `${formatNumber(result.processing_time_ms, 1)} ms`],
      ],
      raw: result,
    }),
  );
}

function finishTemporalReview(lastResult) {
  const policy = state.live.policy;
  $("#camera-stage").classList.add("is-review");
  setCameraState("Revisão necessária");
  $("#temporal-title").textContent = "Sessão inconclusiva";
  $("#temporal-detail").textContent = "Não houve evidência consistente dentro do tempo limite.";
  releaseCamera({ keepLastFrame: true });
  $("#identify-result").replaceChildren(
    resultCard({
      tone: "warning",
      icon: "!",
      eyebrow: "REVISÃO NECESSÁRIA",
      title: "Identidade não confirmada",
      subtitle: "Tente novamente com o rosto centralizado e boa iluminação.",
      metrics: [
        ["Limite", `${(policy.review_after_ms / 1000).toFixed(1)} s`],
        ["Quadros na janela", String(state.live.observations.length)],
        ["Última decisão", DECISIONS[lastResult?.biometric_decision]?.label || "—"],
        ["Melhor similaridade", formatNumber(lastResult?.best_similarity)],
      ],
      raw: lastResult,
    }),
  );
}

function applyTemporalObservation(result) {
  const now = performance.now();
  const policy = state.live.policy;
  const containsFace = result.biometric_decision !== "no_face";
  if (state.live.startedAt === null && !containsFace) {
    setCameraState("Aguardando rosto");
    $("#temporal-title").textContent = "Posicione o rosto";
    $("#temporal-detail").textContent = "O cronômetro só começa após a primeira detecção.";
    return;
  }
  if (state.live.startedAt === null) state.live.startedAt = now;
  if (state.live.lastObservedAt !== null && now - state.live.lastObservedAt > policy.max_gap_ms) {
    state.live.observations = [];
  }
  state.live.lastObservedAt = now;
  state.live.observations.push({
    personId: result.biometric_decision === "identified" ? result.person_id : null,
    result,
  });
  state.live.observations = state.live.observations.slice(-policy.window_size);

  const candidate = dominantCandidate();
  renderFrameDots(candidate?.personId || null);
  if (candidate && candidate.count >= policy.confirmations_required) {
    finishTemporalConfirmation(candidate);
    return;
  }

  const elapsed = now - state.live.startedAt;
  if (elapsed >= policy.review_after_ms) {
    finishTemporalReview(result);
    return;
  }
  const confirmations = candidate?.count || 0;
  setCameraState("Analisando quadros");
  $("#temporal-title").textContent = `${confirmations}/${policy.confirmations_required} confirmações`;
  $("#temporal-detail").textContent = (
    `${Math.max(0, (policy.review_after_ms - elapsed) / 1000).toFixed(1)} s restantes nesta tentativa.`
  );
  renderIdentification($("#identify-result"), result);
}

async function analyzeLiveFrame() {
  if (!state.live.running) return;
  try {
    const image = await captureVideoFrame($("#live-video"), $("#live-canvas"));
    const body = new FormData();
    body.append("image", image, "webcam-frame.jpg");
    body.append("source_id", "demo-ui-webcam");
    const result = await apiRequest("/v1/identifications/identify", { method: "POST", body });
    if (state.live.running) applyTemporalObservation(result);
  } catch (error) {
    if (!state.live.running) return;
    setCameraState("Tentando novamente");
    $("#temporal-detail").textContent = error.message;
    if (
      state.live.startedAt !== null
      && performance.now() - state.live.startedAt >= state.live.policy.review_after_ms
    ) {
      finishTemporalReview(null);
    }
  } finally {
    if (state.live.running) {
      state.live.timer = setTimeout(analyzeLiveFrame, state.live.policy.frame_interval_ms);
    }
  }
}

function renderVerification(container, data) {
  const decision = DECISIONS[data.biometric_decision] || DECISIONS.processing_error;
  const title = data.is_match === true
    ? "Mesma pessoa"
    : data.is_match === false
      ? "Pessoas diferentes"
      : decision.label;
  container.replaceChildren(
    resultCard({
      tone: data.is_match === true ? "success" : decision.tone,
      icon: data.is_match === true ? "✓" : decision.icon,
      eyebrow: "RESULTADO DA COMPARAÇÃO",
      title,
      subtitle: REASONS[data.reason_code] || data.reason_code,
      score: data.similarity,
      metrics: [
        ["Similaridade", formatNumber(data.similarity)],
        ["Limiar", formatNumber(data.threshold)],
        ["Imagem A", data.first_quality ? formatNumber(data.first_quality.score) : "—"],
        ["Imagem B", data.second_quality ? formatNumber(data.second_quality.score) : "—"],
        ["Tempo", `${formatNumber(data.processing_time_ms, 1)} ms`],
        ["Modelo", data.embedding_model_version || "—"],
      ],
      raw: data,
    }),
  );
}

$("#create-person-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  withBusy(form, async () => {
    try {
      const body = {
        consent_confirmed: $("#consent-confirmed").checked,
        consent_version: $("#consent-version").value.trim(),
        external_id: $("#external-id").value.trim() || null,
        display_name: $("#display-name").value.trim() || null,
      };
      const person = await apiRequest("/v1/persons", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      savePerson(person);
      toast("Pessoa criada. Agora selecione as imagens do cadastro.");
    } catch (error) {
      toast(error.message, "error");
    }
  });
});

$("#lookup-person").addEventListener("click", async () => {
  const personId = $("#enroll-person-id").value.trim();
  if (!personId) return toast("Informe um ID para consultar.", "error");
  try {
    const person = await apiRequest(`/v1/persons/${encodeURIComponent(personId)}`);
    savePerson(person);
    toast("Pessoa encontrada e selecionada.");
  } catch (error) {
    toast(error.message, "error");
  }
});

$("#copy-person-id").addEventListener("click", async () => {
  if (!state.activePerson?.id) return;
  await navigator.clipboard.writeText(state.activePerson.id);
  toast("ID copiado.");
});

async function submitEnrollment(images, sourceId) {
  if (images.length < 2 || images.length > 10) {
    throw new Error("Selecione ou capture entre 2 e 10 imagens para o cadastro.");
  }
  const personId = $("#enroll-person-id").value.trim();
  if (!personId) throw new Error("Informe o ID da pessoa.");
  const body = new FormData();
  images.forEach((image, index) => {
    body.append("images", image, image.name || `webcam-frame-${index + 1}.jpg`);
  });
  body.append("source_id", sourceId);
  const result = await apiRequest(`/v1/persons/${encodeURIComponent(personId)}/enroll`, {
    method: "POST",
    body,
  });
  $("#enroll-result").replaceChildren(
    resultCard({
      tone: "success",
      icon: "✓",
      eyebrow: "CADASTRO CONCLUÍDO",
      title: `${result.templates_created} templates criados`,
      subtitle: result.images_rejected
        ? `${result.images_rejected} quadro(s) sem qualidade suficiente foram descartados; os demais foram cadastrados.`
        : "Todos os quadros foram aceitos. As imagens não foram armazenadas pela API.",
      metrics: [
        ["Pessoa", result.person_id],
        ["Aceitos", result.templates_created],
        ["Descartados", result.images_rejected],
        ["Modelo", result.embedding_model_version],
      ],
      raw: result,
    }),
  );
  toast("Cadastro facial concluído.");
  return result;
}

$("#enroll-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  withBusy(form, async () => {
    const container = $("#enroll-result");
    try {
      const files = [...$("#enroll-images").files];
      await submitEnrollment(files, "demo-ui-enrollment");
    } catch (error) {
      renderError(container, error);
    }
  });
});

$("#submit-enroll-camera").addEventListener("click", async () => {
  const button = $("#submit-enroll-camera");
  await withButtonBusy(button, async () => {
    try {
      const currentPersonId = $("#enroll-person-id").value.trim();
      if (currentPersonId !== state.enrollmentCamera.personId) {
        throw new Error("A pessoa selecionada mudou após a captura. Descarte e capture novamente.");
      }
      await submitEnrollment(state.enrollmentCamera.frames, "demo-ui-webcam-enrollment");
      clearEnrollmentFrames({ notify: false });
    } catch (error) {
      renderError($("#enroll-result"), error);
    }
  });
  button.disabled = state.enrollmentCamera.frames.length < 2;
});

$("#identify-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  withBusy(form, async () => {
    const container = $("#identify-result");
    try {
      const image = $("#identify-image").files[0];
      if (!image) throw new Error("Selecione uma imagem para identificar.");
      const body = new FormData();
      body.append("image", image);
      body.append("source_id", "demo-ui-identification");
      const result = await apiRequest("/v1/identifications/identify", { method: "POST", body });
      renderIdentification(container, result);
    } catch (error) {
      renderError(container, error);
    }
  });
});

$("#verify-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  withBusy(form, async () => {
    const container = $("#verify-result");
    try {
      const first = $("#verify-first").files[0];
      const second = $("#verify-second").files[0];
      if (!first || !second) throw new Error("Selecione as duas imagens da comparação.");
      const body = new FormData();
      body.append("first_image", first);
      body.append("second_image", second);
      body.append("source_id", "demo-ui-verification");
      const result = await apiRequest("/v1/verifications/verify", { method: "POST", body });
      renderVerification(container, result);
    } catch (error) {
      renderError(container, error);
    }
  });
});

$$('[data-identify-mode]').forEach((button) => {
  button.addEventListener("click", () => setIdentifyMode(button.dataset.identifyMode));
});
$$('[data-enroll-mode]').forEach((button) => {
  button.addEventListener("click", () => setEnrollMode(button.dataset.enrollMode));
});
$("#open-enroll-camera").addEventListener("click", openEnrollmentCamera);
$("#capture-enroll-frames").addEventListener("click", captureEnrollmentFrames);
$("#clear-enroll-frames").addEventListener("click", clearEnrollmentFrames);
$("#start-live").addEventListener("click", startLive);
$("#stop-live").addEventListener("click", stopLive);
window.addEventListener("pagehide", () => {
  releaseCamera();
  releaseEnrollmentCamera();
  clearEnrollmentFrames({ notify: false });
});

$$('[data-go]').forEach((button) => button.addEventListener("click", () => navigate(button.dataset.go)));
$$('.nav-item').forEach((button) => button.addEventListener("click", () => navigate(button.dataset.view)));

setupDropzone("#enroll-images", "#enroll-preview", "#enroll-count");
setupDropzone("#identify-image", "#identify-preview");
setupDropzone("#verify-first", "#verify-first-preview");
setupDropzone("#verify-second", "#verify-second-preview");

renderActivePerson();
loadTemporalPolicy();
const initialView = location.hash.slice(1);
if (["overview", "enrollment", "identification", "verification"].includes(initialView)) {
  navigate(initialView);
}
refreshHealth();
setInterval(refreshHealth, 30000);
