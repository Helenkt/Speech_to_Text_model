import { getHealth, transcribeAudio } from "./api-client.js";
import { createRouter } from "./router.js";

const SESSION_KEY = "ai-interviewer-session";

function restoreUser() {
  try {
    const value = JSON.parse(window.sessionStorage.getItem(SESSION_KEY));
    return value && typeof value.identity === "string" ? value : null;
  } catch {
    return null;
  }
}

const state = {
  screen: "login",
  user: restoreUser(),
  candidate: null,
  source: "file",
  audioFile: null,
  audioUrl: null,
  language: "vi",
  model: "small",
  beamSize: 1,
  recorder: null,
  stream: null,
  audioContext: null,
  animationFrame: null,
  chunks: [],
  recordingStartedAt: 0,
  recordingTimer: null,
  transcript: "",
  apiStatus: "idle",
};

const elements = Object.fromEntries(
  [
    "serviceStatus", "serviceStatusText", "filePane", "microphonePane", "audioFile",
    "dropZone", "selectedFile", "fileName", "fileMeta", "removeFile", "audioPreview",
    "recordButton", "recordTime", "recordLabel", "waveform", "languageControl",
    "qualityControl", "hotwordsInput", "transcribeButton", "modelName", "runtimeName", "threadCount",
    "emptyState", "processingState", "transcriptText", "copyButton", "downloadButton",
    "durationMetric", "processingMetric", "rtfMetric", "languageMetric", "footerStatus", "toast",
    "loginScreen", "loginForm", "loginIdentity", "loginPassword", "loginFormError",
    "passwordToggle", "logoutButton", "introScreen", "profileScreen", "interviewScreen",
    "startButton", "profileForm", "profileBackButton", "profileFormError", "candidateBadge", "candidateBadgeName",
    "candidateBadgeMeta", "workspaceCandidateName", "workspaceCandidateMeta", "introModelName",
    "introRuntimeName", "readinessTitle",
  ].map((id) => [id, document.getElementById(id)])
);

lucide.createIcons();

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.classList.toggle("is-error", isError);
  elements.toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => elements.toast.classList.remove("is-visible"), 2600);
}

function setFooter(message) {
  elements.footerStatus.textContent = message;
}

function renderScreen(screen) {
  state.screen = screen;
  elements.loginScreen.hidden = screen !== "login";
  elements.introScreen.hidden = screen !== "intro";
  elements.profileScreen.hidden = screen !== "profile";
  elements.interviewScreen.hidden = screen !== "interview";
  elements.candidateBadge.hidden = screen !== "interview" || !state.candidate;
  elements.logoutButton.hidden = !state.user || screen === "login";
  window.scrollTo(0, 0);

  if (screen === "login") setFooter("Đăng nhập để tiếp tục");
  if (screen === "intro") setFooter("Sẵn sàng bắt đầu");
  if (screen === "profile") setFooter("Cập nhật thông tin cá nhân");
  if (screen === "interview") {
    const candidate = state.candidate;
    elements.candidateBadgeName.textContent = candidate.fullName;
    elements.candidateBadgeMeta.textContent = `${candidate.className} · ${candidate.subject}`;
    elements.workspaceCandidateName.textContent = candidate.fullName;
    elements.workspaceCandidateMeta.textContent = `${candidate.className} · ${candidate.subject}`;
    setFooter(state.audioFile ? "Tệp đã sẵn sàng" : "Sẵn sàng phỏng vấn");
  }
}

const router = createRouter({
  resolveScreen: (screen) => {
    if (!state.user) return "login";
    if (screen === "login") return "intro";
    if (screen === "interview" && !state.candidate) return "profile";
    return screen;
  },
  onChange: renderScreen,
});

const validationMessages = {
  loginIdentity: { empty: "Vui lòng nhập tên đăng nhập hoặc email.", short: "Tên đăng nhập phải có ít nhất 3 ký tự." },
  loginPassword: { empty: "Vui lòng nhập mật khẩu.", short: "Mật khẩu phải có ít nhất 8 ký tự." },
  candidateName: { empty: "Vui lòng nhập họ và tên.", short: "Họ và tên phải có ít nhất 2 ký tự." },
  candidateEmail: { empty: "Vui lòng nhập email.", type: "Email chưa đúng định dạng." },
  candidateClass: { empty: "Vui lòng nhập lớp.", short: "Tên lớp phải có ít nhất 2 ký tự." },
  candidateMajor: { empty: "Vui lòng chọn chuyên ngành." },
  candidateSubject: { empty: "Vui lòng nhập môn phỏng vấn.", short: "Tên môn phải có ít nhất 2 ký tự." },
};

function getFieldError(field) {
  const value = field.type === "password" ? field.value : field.value.trim();
  const messages = validationMessages[field.id] || {};
  if (!value) return messages.empty || "Vui lòng nhập thông tin này.";
  if (field.validity.typeMismatch) return messages.type || "Thông tin chưa đúng định dạng.";
  if (field.minLength > 0 && value.length < field.minLength) return messages.short || `Vui lòng nhập ít nhất ${field.minLength} ký tự.`;
  return "";
}

function validateField(field) {
  const message = getFieldError(field);
  const error = document.getElementById(field.dataset.errorId);
  const container = field.closest(".field");
  if (error) error.textContent = message;
  if (container) container.classList.toggle("is-invalid", Boolean(message));
  field.setAttribute("aria-invalid", String(Boolean(message)));
  return !message;
}

function validateForm(form) {
  const fields = [...form.querySelectorAll("[data-error-id]")];
  const results = fields.map(validateField);
  const firstInvalid = fields.find((field) => field.getAttribute("aria-invalid") === "true");
  if (firstInvalid) firstInvalid.focus();
  return results.every(Boolean);
}

function bindFieldValidation(form, errorSummary) {
  form.querySelectorAll("[data-error-id]").forEach((field) => {
    field.addEventListener("blur", () => validateField(field));
    field.addEventListener("input", () => {
      if (field.getAttribute("aria-invalid") === "true") validateField(field);
      if ([...form.querySelectorAll("[data-error-id]")].every((item) => !getFieldError(item))) {
        errorSummary.hidden = true;
      }
    });
    field.addEventListener("change", () => validateField(field));
  });
}

bindFieldValidation(elements.loginForm, elements.loginFormError);
bindFieldValidation(elements.profileForm, elements.profileFormError);

elements.passwordToggle.addEventListener("click", () => {
  const isVisible = elements.loginPassword.type === "text";
  elements.loginPassword.type = isVisible ? "password" : "text";
  const label = isVisible ? "Hiện mật khẩu" : "Ẩn mật khẩu";
  elements.passwordToggle.title = label;
  elements.passwordToggle.setAttribute("aria-label", label);
  elements.passwordToggle.innerHTML = `<i data-lucide="${isVisible ? "eye" : "eye-off"}"></i>`;
  lucide.createIcons();
});

elements.loginForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!validateForm(event.currentTarget)) {
    elements.loginFormError.hidden = false;
    return;
  }

  state.user = { identity: elements.loginIdentity.value.trim() };
  window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(state.user));
  elements.loginPassword.value = "";
  elements.loginFormError.hidden = true;
  router.navigate("intro");
  showToast("Đăng nhập thành công.");
});

elements.logoutButton.addEventListener("click", () => {
  state.user = null;
  state.candidate = null;
  window.sessionStorage.removeItem(SESSION_KEY);
  elements.loginForm.reset();
  elements.profileForm.reset();
  elements.loginForm.querySelectorAll("[aria-invalid]").forEach((field) => field.removeAttribute("aria-invalid"));
  elements.profileForm.querySelectorAll("[aria-invalid]").forEach((field) => field.removeAttribute("aria-invalid"));
  document.querySelectorAll(".field.is-invalid").forEach((field) => field.classList.remove("is-invalid"));
  document.querySelectorAll(".field-error").forEach((error) => { error.textContent = ""; });
  router.navigate("login", { replace: true });
  showToast("Đã đăng xuất.");
});

elements.startButton.addEventListener("click", () => router.navigate("profile"));
elements.profileBackButton.addEventListener("click", () => router.navigate("intro"));
elements.candidateBadge.addEventListener("click", () => router.navigate("profile"));

elements.profileForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  if (!validateForm(form)) {
    elements.profileFormError.hidden = false;
    return;
  }

  const values = new FormData(form);
  state.candidate = {
    fullName: String(values.get("fullName") || "").trim(),
    email: String(values.get("email") || "").trim(),
    className: String(values.get("className") || "").trim(),
    major: String(values.get("major") || "").trim(),
    subject: String(values.get("subject") || "").trim(),
  };
  elements.profileFormError.hidden = true;
  router.navigate("interview");
});

async function loadHealth() {
  state.apiStatus = "loading";
  try {
    const health = await getHealth();
    state.apiStatus = "ready";
    elements.serviceStatus.className = "service-status is-ready";
    elements.serviceStatusText.textContent = "Model sẵn sàng";
    const modelLabel = health.model
      ? health.model.charAt(0).toUpperCase() + health.model.slice(1)
      : "--";
    elements.modelName.textContent = `Whisper ${modelLabel}`;
    elements.runtimeName.textContent = `${health.device.toUpperCase()} · ${health.compute_type.toUpperCase()}`;
    elements.threadCount.textContent = `${health.cpu_threads} luồng`;
    elements.introModelName.textContent = `Whisper ${modelLabel}`;
    elements.introRuntimeName.textContent = `${health.device.toUpperCase()} · ${health.compute_type.toUpperCase()}`;
    elements.readinessTitle.textContent = "Sẵn sàng phỏng vấn";
  } catch (error) {
    state.apiStatus = "error";
    elements.serviceStatus.className = "service-status is-error";
    elements.serviceStatusText.textContent = "Mất kết nối";
    elements.introModelName.textContent = "Không khả dụng";
    elements.introRuntimeName.textContent = "Chưa kết nối";
    elements.readinessTitle.textContent = "Dịch vụ chưa sẵn sàng";
    setFooter("Không thể kết nối model");
  }
}

function revokeAudioUrl() {
  if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
  state.audioUrl = null;
}

function setAudioFile(file) {
  if (!file) return;
  if (file.size > 100 * 1024 * 1024) {
    showToast("Tệp vượt quá giới hạn 100 MB", true);
    return;
  }
  revokeAudioUrl();
  state.audioFile = file;
  state.audioUrl = URL.createObjectURL(file);
  elements.dropZone.hidden = true;
  elements.selectedFile.hidden = false;
  elements.fileName.textContent = file.name;
  elements.fileMeta.textContent = `${formatBytes(file.size)} · ${file.type || "audio"}`;
  elements.audioPreview.src = state.audioUrl;
  elements.audioPreview.hidden = false;
  elements.transcribeButton.disabled = false;
  setFooter("Tệp đã sẵn sàng");
}

function clearAudioFile() {
  revokeAudioUrl();
  state.audioFile = null;
  elements.audioFile.value = "";
  elements.dropZone.hidden = false;
  elements.selectedFile.hidden = true;
  elements.audioPreview.hidden = true;
  elements.audioPreview.removeAttribute("src");
  elements.transcribeButton.disabled = true;
  setFooter("Sẵn sàng");
}

document.querySelectorAll(".source-tab").forEach((button) => {
  button.addEventListener("click", () => {
    state.source = button.dataset.source;
    document.querySelectorAll(".source-tab").forEach((tab) => {
      const selected = tab === button;
      tab.classList.toggle("is-active", selected);
      tab.setAttribute("aria-selected", String(selected));
    });
    elements.filePane.hidden = state.source !== "file";
    elements.microphonePane.hidden = state.source !== "microphone";
  });
});

elements.audioFile.addEventListener("change", (event) => setAudioFile(event.target.files[0]));
elements.removeFile.addEventListener("click", clearAudioFile);

["dragenter", "dragover"].forEach((eventName) => {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.add("is-dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove("is-dragging");
  });
});

elements.dropZone.addEventListener("drop", (event) => setAudioFile(event.dataTransfer.files[0]));

function bindSegmented(control, stateKey, parser = (value) => value) {
  control.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      control.querySelectorAll("button").forEach((item) => item.classList.toggle("is-active", item === button));
      state[stateKey] = parser(button.dataset.value);
    });
  });
}

bindSegmented(elements.languageControl, "language");
elements.qualityControl.querySelectorAll("button").forEach((button) => {
  button.addEventListener("click", () => {
    elements.qualityControl.querySelectorAll("button").forEach((item) => {
      item.classList.toggle("is-active", item === button);
    });
    state.model = button.dataset.model;
    state.beamSize = Number(button.dataset.beam);
    const modelLabel = state.model.charAt(0).toUpperCase() + state.model.slice(1);
    elements.modelName.textContent = `Whisper ${modelLabel}`;
    setFooter(`${button.textContent.trim()} · Whisper ${modelLabel}`);
  });
});

function drawIdleWaveform() {
  const canvas = elements.waveform;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.strokeStyle = "#9aacA4";
  context.lineWidth = 2;
  context.beginPath();
  for (let x = 0; x < canvas.width; x += 8) {
    const height = 4 + Math.abs(Math.sin(x * 0.07)) * 10;
    context.moveTo(x, canvas.height / 2 - height / 2);
    context.lineTo(x, canvas.height / 2 + height / 2);
  }
  context.stroke();
}

function drawLiveWaveform(analyser) {
  const canvas = elements.waveform;
  const context = canvas.getContext("2d");
  const data = new Uint8Array(analyser.frequencyBinCount);
  const render = () => {
    analyser.getByteTimeDomainData(data);
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.strokeStyle = "#08745b";
    context.lineWidth = 2;
    context.beginPath();
    data.forEach((value, index) => {
      const x = index / (data.length - 1) * canvas.width;
      const y = value / 255 * canvas.height;
      if (index === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.stroke();
    state.animationFrame = requestAnimationFrame(render);
  };
  render();
}

function updateRecordTime() {
  const elapsed = Math.floor((Date.now() - state.recordingStartedAt) / 1000);
  const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const seconds = String(elapsed % 60).padStart(2, "0");
  elements.recordTime.textContent = `${minutes}:${seconds}`;
}

async function startRecording() {
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.chunks = [];
    state.recorder = new MediaRecorder(state.stream);
    state.recorder.addEventListener("dataavailable", (event) => {
      if (event.data.size) state.chunks.push(event.data);
    });
    state.recorder.addEventListener("stop", () => {
      const blob = new Blob(state.chunks, { type: state.recorder.mimeType || "audio/webm" });
      setAudioFile(new File([blob], `ghi-am-${Date.now()}.webm`, { type: blob.type }));
      state.stream.getTracks().forEach((track) => track.stop());
      state.audioContext.close();
      cancelAnimationFrame(state.animationFrame);
      clearInterval(state.recordingTimer);
      drawIdleWaveform();
      elements.recordButton.classList.remove("is-recording");
      elements.recordButton.innerHTML = '<i data-lucide="circle"></i><span>Ghi lại</span>';
      elements.recordLabel.textContent = "Bản ghi đã sẵn sàng";
      lucide.createIcons();
    });

    state.audioContext = new AudioContext();
    const source = state.audioContext.createMediaStreamSource(state.stream);
    const analyser = state.audioContext.createAnalyser();
    analyser.fftSize = 1024;
    source.connect(analyser);
    drawLiveWaveform(analyser);

    state.recorder.start();
    state.recordingStartedAt = Date.now();
    updateRecordTime();
    state.recordingTimer = setInterval(updateRecordTime, 250);
    elements.recordButton.classList.add("is-recording");
    elements.recordButton.innerHTML = '<i data-lucide="square"></i><span>Dừng ghi</span>';
    elements.recordLabel.textContent = "Đang ghi âm";
    lucide.createIcons();
  } catch (error) {
    showToast("Không thể truy cập microphone", true);
  }
}

function stopRecording() {
  if (state.recorder?.state === "recording") state.recorder.stop();
}

elements.recordButton.addEventListener("click", () => {
  if (state.recorder?.state === "recording") stopRecording();
  else startRecording();
});

function setProcessing(isProcessing) {
  elements.processingState.hidden = !isProcessing;
  elements.emptyState.hidden = isProcessing || Boolean(state.transcript);
  elements.transcriptText.hidden = isProcessing || !state.transcript;
  elements.transcribeButton.disabled = isProcessing || !state.audioFile;
  elements.transcribeButton.innerHTML = isProcessing
    ? '<i data-lucide="loader-circle"></i><span>Đang xử lý...</span>'
    : '<i data-lucide="sparkles"></i><span>Chuyển thành văn bản</span>';
  lucide.createIcons();
  if (isProcessing) elements.transcribeButton.querySelector("svg")?.classList.add("spin");
}

function renderResult(result) {
  state.transcript = result.text || "Không phát hiện nội dung giọng nói trong tệp âm thanh.";
  elements.processingState.hidden = true;
  elements.transcriptText.hidden = false;
  elements.transcriptText.textContent = state.transcript;
  elements.durationMetric.textContent = `${result.duration_seconds.toFixed(2)} s`;
  elements.processingMetric.textContent = `${result.processing_seconds.toFixed(2)} s`;
  elements.rtfMetric.textContent = result.real_time_factor.toFixed(3);
  elements.languageMetric.textContent = String(result.language || "--").toUpperCase();
  const modelLabel = result.model.charAt(0).toUpperCase() + result.model.slice(1);
  elements.modelName.textContent = `Whisper ${modelLabel}`;
  elements.runtimeName.textContent = `${result.device.toUpperCase()} · ${result.compute_type.toUpperCase()}`;
  elements.copyButton.disabled = false;
  elements.downloadButton.disabled = false;
  setFooter(`Hoàn thành · ${result.device.toUpperCase()} ${result.compute_type}`);
}

elements.transcribeButton.addEventListener("click", async () => {
  if (!state.audioFile) return;
  state.apiStatus = "loading";
  setProcessing(true);
  setFooter("Đang xử lý trên thiết bị...");
  try {
    const payload = await transcribeAudio({
      file: state.audioFile,
      language: state.language,
      beamSize: state.beamSize,
      model: state.model,
      hotwords: elements.hotwordsInput.value.trim(),
    });
    state.apiStatus = "success";
    renderResult(payload);
  } catch (error) {
    state.apiStatus = "error";
    state.transcript = "";
    setFooter("Xử lý thất bại");
    showToast(error.message, true);
  } finally {
    setProcessing(false);
  }
});

elements.copyButton.addEventListener("click", async () => {
  await navigator.clipboard.writeText(state.transcript);
  showToast("Đã sao chép transcript");
});

elements.downloadButton.addEventListener("click", () => {
  const candidate = state.candidate;
  const candidateDetails = candidate
    ? [
        `Ứng viên: ${candidate.fullName}`,
        `Lớp: ${candidate.className}`,
        `Chuyên ngành: ${candidate.major}`,
        `Môn phỏng vấn: ${candidate.subject}`,
        "",
      ].join("\n")
    : "";
  const blob = new Blob([`${candidateDetails}${state.transcript}\n`], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "transcript.txt";
  link.click();
  URL.revokeObjectURL(url);
});

drawIdleWaveform();
router.start();
loadHealth();
