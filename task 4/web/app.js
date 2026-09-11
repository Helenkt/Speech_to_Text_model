import { getHealth, transcribeAudio } from "./api-client.js";
import { createRouter } from "./router.js";

const state = {
  screen: "intro",
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
    "introScreen", "candidateScreen", "interviewScreen", "startButton", "candidateForm",
    "candidateBackButton", "candidateFormError", "candidateBadge", "candidateBadgeName",
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
  elements.introScreen.hidden = screen !== "intro";
  elements.candidateScreen.hidden = screen !== "candidate";
  elements.interviewScreen.hidden = screen !== "interview";
  elements.candidateBadge.hidden = screen !== "interview" || !state.candidate;
  window.scrollTo(0, 0);

  if (screen === "intro") setFooter("Sẵn sàng bắt đầu");
  if (screen === "candidate") setFooter("Nhập thông tin ứng viên");
  if (screen === "interview") {
    const candidate = state.candidate;
    elements.candidateBadgeName.textContent = candidate.fullName;
    elements.candidateBadgeMeta.textContent = `${candidate.studentId} · ${candidate.className}`;
    elements.workspaceCandidateName.textContent = candidate.fullName;
    elements.workspaceCandidateMeta.textContent = `${candidate.studentId} · ${candidate.className} · ${candidate.subject}`;
    setFooter(state.audioFile ? "Tệp đã sẵn sàng" : "Sẵn sàng phỏng vấn");
  }
}

const router = createRouter({
  canEnter: (screen) => screen !== "interview" || Boolean(state.candidate),
  onChange: renderScreen,
});

elements.startButton.addEventListener("click", () => router.navigate("candidate"));
elements.candidateBackButton.addEventListener("click", () => router.navigate("intro"));
elements.candidateBadge.addEventListener("click", () => router.navigate("candidate"));

elements.candidateForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.checkValidity()) {
    elements.candidateFormError.hidden = false;
    form.reportValidity();
    return;
  }

  const values = new FormData(form);
  state.candidate = {
    fullName: String(values.get("fullName") || "").trim(),
    studentId: String(values.get("studentId") || "").trim(),
    email: String(values.get("email") || "").trim(),
    className: String(values.get("className") || "").trim(),
    major: String(values.get("major") || "").trim(),
    subject: String(values.get("subject") || "").trim(),
  };
  elements.candidateFormError.hidden = true;
  router.navigate("interview");
});

elements.candidateForm.addEventListener("invalid", () => {
  elements.candidateFormError.hidden = false;
}, true);

elements.candidateForm.addEventListener("input", () => {
  if (elements.candidateForm.checkValidity()) elements.candidateFormError.hidden = true;
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
        `Mã sinh viên: ${candidate.studentId}`,
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
