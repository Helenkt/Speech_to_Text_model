const LUCIDE_ICONS = {
  "audio-lines": '<path d="M4 10v4M8 6v12M12 3v18M16 6v12M20 10v4"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V4H4v12h4"/>',
  eye: '<path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6S2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>',
  "refresh-cw": '<path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 11-2l3 3M18 17a7 7 0 0 1-11 2l-3-3"/>',
  save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  trash: '<path d="M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7"/>',
  upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/>',
  user: '<path d="M20 21a8 8 0 0 0-16 0"/><circle cx="12" cy="7" r="4"/>',
  x: '<path d="m6 6 12 12M18 6 6 18"/>',
};

function lucideIcon(name) {
  const icon = LUCIDE_ICONS[name];
  return icon
    ? `<svg class="lucide" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${icon}</svg>`
    : "";
}

function renderLucideIcons(root = document) {
  root.querySelectorAll("[data-lucide]").forEach((host) => {
    const icon = LUCIDE_ICONS[host.dataset.lucide];
    if (!icon || host.querySelector("svg")) return;
    host.insertAdjacentHTML(
      "afterbegin",
      lucideIcon(host.dataset.lucide),
    );
  });
}

renderLucideIcons();

const state = {
  user: null,
  health: null,
  summary: null,
  exams: [],
  accounts: [],
  results: [],
  generatedQuestions: [],
  reviewQueue: [],
  practiceHistory: [],
  candidateExam: null,
  session: null,
  currentQuestion: null,
  pendingResult: null,
  completed: false,
  reportOrigin: "practice",
  recorder: null,
  audioChunks: [],
  mediaStream: null,
  ambientNoiseDbfs: null,
  currentTranscriptionId: null,
  selectedMicrophoneId: "",
  microphoneSelectionInitialized: false,
  microphoneRefreshSequence: 0,
  microphoneDevices: [],
  microphoneLabel: "",
  micTestController: null,
  sessionMicCheck: null,
  examCreating: false,
  questionImporting: false,
  activeViewId: "",
  generationBusy: false,
  questionDeciding: new Set(),
  teacherReportSequence: 0,
  reviewOpenSequence: 0,
  generatedLoadSequence: 0,
  accountImporting: false,
  accountLoadSequence: 0,
  accountChanging: new Set(),
  teacherWorkspaceSequence: 0,
  teacherResultsLoaded: false,
  teacherReviewsLoaded: false,
  teacherResultsStale: false,
  teacherDeleting: new Set(),
  teacherResultPane: "results",
  reviewSessionFilter: "",
  selectedReviewAnswerId: "",
  manualReviewItem: null,
  reviewDrafts: {},
  reviewThreshold: 50,
  reviewSaving: false,
  reviewAnalyzing: new Set(),
  lastReviewedSessionId: "",
  reviewEvidenceSequence: 0,
  reviewReportCache: new Map(),
  reviewHistoryCache: new Map(),
  reviewHistoryLoading: new Set(),
  currentTeacherReport: null,
  currentTeacherReportSessionId: "",
};

const el = Object.fromEntries(
  [...document.querySelectorAll("[id]")].map((node) => [node.id, node]),
);

const NAV_ITEMS = {
  teacher: [
    ["teacherDashboardView", "Bài thi"],
    ["teacherQuestionsView", "Câu hỏi"],
    ["teacherAccountsView", "Tài khoản"],
    ["teacherResultsView", "Kết quả & chấm lại"],
  ],
  candidate: [
    ["practiceSetupView", "Luyện tập"],
    ["practiceHistoryView", "Lịch sử"],
    ["realSetupView", "Interview"],
  ],
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function toast(message, isError = false) {
  el.toast.textContent = message;
  el.toast.className = `toast show${isError ? " error" : ""}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.toast.className = "toast"; }, 3600);
}

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", cache: "no-store", ...options });
  let payload = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) payload = await response.json();
  if (!response.ok) {
    if (response.status === 401 && !path.endsWith("/auth/login")) showLogin();
    const detail = payload?.detail;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join("; ") : detail || `HTTP ${response.status}`);
  }
  return payload;
}

function jsonOptions(method, body) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

function showLogin() {
  dismissReportDialog();
  state.micTestController?.abort();
  if (state.recorder?.state === "recording") {
    state.recorder.onstop = null;
    state.recorder.stop();
  }
  state.mediaStream?.getTracks().forEach((track) => track.stop());
  state.teacherWorkspaceSequence += 1; state.generatedLoadSequence += 1; state.accountLoadSequence += 1;
  state.teacherReportSequence += 1; state.reviewEvidenceSequence += 1; state.reviewOpenSequence += 1;
  state.reviewDrafts = {}; state.reviewReportCache.clear(); state.reviewHistoryCache.clear(); state.currentTeacherReport = null;
  state.reviewAnalyzing.clear();
  state.reviewHistoryLoading.clear();
  state.currentTeacherReportSessionId = ""; state.selectedReviewAnswerId = ""; state.manualReviewItem = null;
  state.reviewSessionFilter = ""; state.lastReviewedSessionId = ""; state.teacherResultPane = "results";
  state.results = []; state.reviewQueue = []; state.accounts = []; state.generatedQuestions = [];
  state.teacherResultsLoaded = false; state.teacherReviewsLoaded = false; state.teacherResultsStale = false;
  el.reviewAudio.pause?.();
  state.user = null;
  state.session = null;
  state.sessionMicCheck = null;
  state.ambientNoiseDbfs = null;
  state.practiceHistory = [];
  state.recorder = null;
  state.mediaStream = null;
  el.appShell.classList.add("hidden");
  el.loginView.classList.remove("hidden");
  el.loginPassword.value = "";
  setPasswordVisibility(false);
  setTimeout(() => el.loginUsername.focus(), 0);
}

function renderNavigation() {
  el.roleNav.innerHTML = NAV_ITEMS[state.user.role]
    .map(([view, label]) => `<button class="nav-button" type="button" data-view="${view}">${label}</button>`)
    .join("");
}

function setNavigationLocked(locked) {
  el.roleNav.querySelectorAll("button").forEach((button) => { button.disabled = locked; });
}

function showView(viewId) {
  if (viewId === "teacherReviewsView") viewId = "teacherResultsView";
  state.activeViewId = viewId;
  state.teacherReportSequence += 1;
  if (viewId !== "teacherResultsView") { rememberReviewDraft(); el.reviewAudio.pause?.(); }
  dismissReportDialog();
  if (viewId !== "interviewView") state.micTestController?.abort();
  document.querySelectorAll(".app-view").forEach((view) => view.classList.toggle("active", view.id === viewId));
  el.roleNav.querySelectorAll("[data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === viewId));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function enterApp(user) {
  state.user = user;
  el.loginView.classList.add("hidden");
  el.appShell.classList.remove("hidden");
  el.headerUserName.textContent = user.full_name;
  el.headerUserRole.textContent = user.role === "teacher" ? "Giáo viên" : "Ứng viên";
  el.practiceCandidateName.value = user.full_name;
  el.realCandidateName.value = user.full_name;
  el.realCandidateEmail.value = user.email || user.student_id || "Chưa có thông tin";
  renderNavigation();

  try {
    const [health, summary] = await Promise.all([api("/api/health"), api("/api/questions/summary")]);
    state.health = health;
    applySummary(summary);
    el.questionModelName.textContent = health.question_generation?.model || "Qwen3:8B";
    if (user.role === "teacher") {
      showView("teacherDashboardView");
      setDefaultExamTimes();
      await loadExams();
    } else {
      showView("practiceSetupView");
    }
  } catch (error) {
    toast(`Không thể tải dữ liệu: ${error.message}`, true);
  }
}

async function login(event) {
  event.preventDefault();
  el.loginError.textContent = "";
  el.loginButton.disabled = true;
  el.loginButton.textContent = "ĐANG ĐĂNG NHẬP...";
  try {
    const result = await api("/api/auth/login", jsonOptions("POST", {
      username: el.loginUsername.value.trim(),
      password: el.loginPassword.value,
    }));
    await enterApp(result.user);
  } catch (error) {
    el.loginError.textContent = error.message;
  } finally {
    el.loginButton.disabled = false;
    el.loginButton.textContent = "Đăng nhập";
  }
}

async function logout() {
  try { await api("/api/auth/logout", { method: "POST" }); } catch (_) { /* local logout still applies */ }
  showLogin();
}

function setPasswordVisibility(visible) {
  el.loginPassword.type = visible ? "text" : "password";

  el.togglePasswordButton.classList.toggle("is-visible", visible);
  el.togglePasswordButton.setAttribute(
    "aria-label",
    visible ? "Ẩn mật khẩu" : "Hiện mật khẩu",
  );
  el.togglePasswordButton.setAttribute(
    "aria-pressed",
    String(visible),
  );
}

function togglePasswordVisibility() {
  const passwordIsHidden = el.loginPassword.type === "password";
  setPasswordVisibility(passwordIsHidden);
}

function languageName(code) {
  return code === "vi" ? "Tiếng Việt" : code === "en" ? "English" : code.toUpperCase();
}

function answerModeName(mode) {
  return mode === "text" ? "Văn bản" : mode === "voice" ? "Chỉ Voice" : "Văn bản hoặc Voice";
}

function difficultyName(value) {
  return value === "Easy" ? "Dễ" : value === "Medium" ? "Trung bình" : "Khó";
}

function fillLanguageSelect(select, preserve = true) {
  const oldValue = preserve ? select.value : "";
  const languages = state.summary?.languages || [];
  select.innerHTML = languages.map((item) => `<option value="${escapeHtml(item.language)}">${languageName(item.language)}${select === el.examLanguage ? "" : ` (${item.total})`}</option>`).join("");
  if (languages.some((item) => item.language === oldValue)) {
    select.value = oldValue;
  } else if (languages.some((item) => item.language === "vi")) {
    select.value = "vi";
  }
}

function updateSubjectSelect(languageSelect, subjectSelect, allowAll) {
  const language = state.summary?.languages.find((item) => item.language === languageSelect.value);
  const previous = subjectSelect.value;
  const options = [];
  if (allowAll) options.push('<option value="">Tất cả lĩnh vực</option>');
  for (const subject of language?.subjects || []) {
    options.push(`<option value="${escapeHtml(subject.name)}">${escapeHtml(subject.name)}${subjectSelect === el.examSubject ? "" : ` (${subject.total})`}</option>`);
  }
  subjectSelect.innerHTML = options.join("");
  if ([...subjectSelect.options].some((item) => item.value === previous)) subjectSelect.value = previous;
}

function applySummary(summary) {
  state.summary = summary;
  fillLanguageSelect(el.examLanguage);
  fillLanguageSelect(el.practiceLanguage);
  fillLanguageSelect(el.generatedQuestionLanguage);
  updateSubjectSelect(el.examLanguage, el.examSubject, false);
  updateSubjectSelect(el.practiceLanguage, el.practiceSubject, true);
  updateSubjectSelect(el.generatedQuestionLanguage, el.generatedQuestionSubject, false);
  updateExamBankHint();
  updateGeneratorPreview();
  const rows = summary.languages || [];
  el.questionBankRows.innerHTML = rows.length
    ? rows.map((item) => `<div class="summary-row"><strong>${languageName(item.language)}</strong><span>${item.total.toLocaleString("vi-VN")} câu · ${item.subjects.length} lĩnh vực</span></div>`).join("")
    : '<div class="empty-state">Chưa có câu hỏi. Hãy import file JSON.</div>';
}

async function refreshSummary() {
  applySummary(await api("/api/questions/summary"));
}

function setImportFeedback(message, isError = false) {
  el.questionImportFeedback.textContent = message;
  el.questionImportFeedback.className = `inline-feedback ${isError ? "error" : "success"}${message ? "" : " hidden"}`;
}

function updateQuestionFile() {
  const file = el.questionFile.files?.[0];
  const error = file && (!/\.json$/i.test(file.name) ? "Hãy chọn file .json." : file.size > 25 * 1024 * 1024 ? "File vượt quá 25 MB." : file.size === 0 ? "File đang trống." : "");
  el.questionFileName.textContent = file ? `${file.name} · ${(file.size / 1024 / 1024).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} MB` : "JSON · tối đa 25 MB";
  el.clearQuestionFileButton.classList.toggle("hidden", !file);
  el.questionDropZone.classList.toggle("has-file", Boolean(file) && !error);
  el.questionImportButton.disabled = state.questionImporting || !file || Boolean(error);
  el.questionFile.setCustomValidity(error || "");
  setImportFeedback(error || "", Boolean(error));
  return Boolean(file) && !error;
}

async function importQuestions(event) {
  event.preventDefault();
  if (state.questionImporting || !updateQuestionFile()) return;
  if (el.questionImportMode.value === "replace" && !window.confirm("Thay các câu hỏi của ngôn ngữ có trong file?")) return;
  const file = el.questionFile.files[0];
  const form = new FormData();
  form.append("file", file);
  form.append("mode", el.questionImportMode.value);
  form.append("default_language", el.questionDefaultLanguage.value);
  state.questionImporting = true;
  el.questionImportButton.disabled = true;
  el.questionFile.disabled = true;
  el.clearQuestionFileButton.disabled = true;
  el.questionImportMode.disabled = true;
  el.questionDefaultLanguage.disabled = true;
  el.questionImportButton.textContent = "Đang kiểm tra…";
  try {
    try { JSON.parse(await file.text()); } catch (_) { throw new Error("Nội dung JSON không hợp lệ. Hãy kiểm tra file rồi nhập lại."); }
    const result = await api("/api/questions/import", { method: "POST", body: form });
    el.questionUploadForm.reset();
    updateQuestionFile();
    const message = `Đã nhập ${result.imported} câu: ${result.created} mới, ${result.updated} cập nhật.`;
    setImportFeedback(message);
    toast(message);
    try { await refreshSummary(); } catch (_) { toast("Đã nhập câu hỏi. Chưa tải lại được thống kê; hãy tải lại trang.", true); }
  } catch (error) {
    setImportFeedback(error.message, true);
    toast(error.message, true);
  } finally {
    state.questionImporting = false;
    el.questionImportButton.disabled = !el.questionFile.files?.length || Boolean(el.questionFile.validationMessage);
    el.questionFile.disabled = false;
    el.clearQuestionFileButton.disabled = false;
    el.questionImportMode.disabled = false;
    el.questionDefaultLanguage.disabled = false;
    el.questionImportButton.textContent = "Nhập câu hỏi";
  }
}

async function reloadDemo() {
  if (!window.confirm("Nạp lại hai bộ câu hỏi demo tiếng Việt và tiếng Anh?")) return;
  el.reloadDemoButton.disabled = true;
  try {
    const result = await api("/api/questions/reload-demo", { method: "POST" });
    applySummary(result.summary);
    toast("Đã nạp lại hai bộ câu hỏi demo.");
  } catch (error) {
    toast(error.message, true);
  } finally {
    el.reloadDemoButton.disabled = false;
  }
}

function generatedStatusLabel(status) {
  return {
    draft: ["Chờ duyệt", "waiting"],
    approved: ["Đã duyệt", ""],
    rejected: ["Đã từ chối", "closed"],
  }[status] || [status, "closed"];
}

function teacherFeedback(node, message, isError = true) {
  node.textContent = message;
  node.className = `inline-feedback ${isError ? "error" : "success"}${message ? "" : " hidden"}`;
}

function updateGeneratorPreview() {
  const counts = [el.generatedEasyCount, el.generatedMediumCount, el.generatedHardCount].map((input) => Number(input.value));
  const total = counts.reduce((sum, count) => sum + count, 0);
  el.generatedTotal.textContent = `${Number.isFinite(total) ? total : 0} câu`;
  const bank = state.summary?.languages?.find((item) => item.language === el.generatedQuestionLanguage.value)?.subjects?.find((item) => item.name === el.generatedQuestionSubject.value);
  el.generateQuestionsButton.disabled = state.generationBusy || !bank?.total;
}

function renderGeneratedQuestions() {
  const text = el.generatedQuestionSearch.value.trim().toLocaleLowerCase("vi");
  const items = state.generatedQuestions.filter((item) => {
    const q = item.question || {};
    return (!el.generatedQuestionStatus.value || item.status === el.generatedQuestionStatus.value)
      && (!el.generatedDifficultyFilter.value || q.difficulty === el.generatedDifficultyFilter.value)
      && (!text || [q.question, q.subject, q.topic, q.concept].join(" ").toLocaleLowerCase("vi").includes(text));
  });
  el.generatedQuestionCount.textContent = `${items.length} / ${state.generatedQuestions.length} câu`;
  el.generatedQuestionRows.innerHTML = items.length ? items.map((item) => {
    const q = item.question || {}, rubric = item.rubric || {};
    const [statusLabel, statusClass] = generatedStatusLabel(item.status);
    const id = escapeHtml(item.generated_id), busy = state.questionDeciding.has(String(item.generated_id));
    const actions = item.status === "draft" ? `<div class="generated-actions"><button class="button secondary compact" type="button" data-generated-action="reject" data-generated-id="${id}" ${busy ? "disabled" : ""}>Từ chối</button><button class="button primary compact" type="button" data-generated-action="approve" data-generated-id="${id}" ${busy ? "disabled" : ""}>Duyệt</button></div>` : "";
    const failures = Array.isArray(rubric.hard_gate_failures) ? rubric.hard_gate_failures : [];
    const provenance = Array.isArray(q.source_provenance) ? q.source_provenance : [];
    const sourceRows = provenance.map((source) => `<li><strong>${escapeHtml(source.source_question_id)}</strong> · ${escapeHtml(source.source_name || "nguồn nội bộ")}<br><small title="${escapeHtml(source.source_sha256 || "")}">SHA-256 ${escapeHtml((source.source_sha256 || "—").slice(0, 12))} · ${escapeHtml(source.verification_status || "—")}</small><p>${escapeHtml(source.reference_excerpt || "")}</p></li>`).join("");
    const promptHash = q.generation_provenance?.prompt_sha256 || "";
    return `<article class="generated-question-item"><div class="generated-question-head"><div class="question-tags"><span class="tag">${escapeHtml(difficultyName(q.difficulty))}</span><span>${escapeHtml(q.subject)}</span><span>${escapeHtml(q.topic || q.concept || "")}</span></div><span class="status-badge ${escapeHtml(statusClass)}">${escapeHtml(statusLabel)}</span></div><h3>${escapeHtml(q.question)}</h3><div class="generated-question-footer"><details><summary>Đáp án & kiểm định · ${reportNumber(rubric.score)}/100</summary><div class="generated-detail-grid"><div><h4>Đáp án tham khảo</h4><p>${escapeHtml(q.reference_answer || "—")}</p></div><div><h4>Ý chính</h4><ul>${(Array.isArray(q.key_points) ? q.key_points : []).map((point) => `<li>${escapeHtml(point)}</li>`).join("") || "<li>Chưa có</li>"}</ul></div><div><h4>Truy vết nguồn</h4><ul>${sourceRows || `<li>${(Array.isArray(q.source_question_ids) ? q.source_question_ids : []).map(escapeHtml).join(" · ") || "—"}</li>`}</ul>${promptHash ? `<small title="${escapeHtml(promptHash)}">Prompt SHA-256 ${escapeHtml(promptHash.slice(0, 12))}</small>` : ""}</div><div><h4>Kiểm định</h4><p>${failures.length ? failures.map(escapeHtml).join(" · ") : "Không có lỗi kiểm định được trả về."}</p></div></div></details>${actions}</div></article>`;
  }).join("") : '<div class="empty-state">Không có câu hỏi phù hợp.</div>';
}

async function loadGeneratedQuestions() {
  const sequence = ++state.generatedLoadSequence;
  el.generatedQuestionRows.setAttribute("aria-busy", "true");
  try {
    const result = await api("/api/teacher/questions/generated");
    if (sequence !== state.generatedLoadSequence) return;
    state.generatedQuestions = result.questions || [];
    renderGeneratedQuestions();
  } finally {
    if (sequence === state.generatedLoadSequence) el.generatedQuestionRows.removeAttribute("aria-busy");
  }
}

async function refreshGeneratedQuestions() {
  el.refreshGeneratedQuestionsButton.disabled = true;
  try { await loadGeneratedQuestions(); teacherFeedback(el.generatorFeedback, ""); }
  catch (error) { teacherFeedback(el.generatorFeedback, `Chưa tải được câu hỏi: ${error.message}`); }
  finally { el.refreshGeneratedQuestionsButton.disabled = false; }
}

async function generateQuestions(event) {
  event.preventDefault();
  if (state.generationBusy) return;
  const counts = [el.generatedEasyCount, el.generatedMediumCount, el.generatedHardCount].map((input) => Number(input.value));
  if (counts.some((count) => !Number.isInteger(count) || count < 0 || count > 10) || counts.reduce((a, b) => a + b, 0) < 1) {
    teacherFeedback(el.generatorFeedback, "Chọn ít nhất 1 câu; mỗi độ khó tối đa 10 câu."); return;
  }
  if (!el.generatedQuestionSubject.value) { teacherFeedback(el.generatorFeedback, "Chọn môn có dữ liệu nguồn trước khi tạo câu hỏi."); return; }
  state.generationBusy = true;
  teacherFeedback(el.generatorFeedback, "Đang sinh câu hỏi…", false);
  const controls = [...el.questionGeneratorForm.querySelectorAll("input, select, button")];
  const disabled = controls.map((node) => node.disabled);
  controls.forEach((node) => { node.disabled = true; });
  el.generateQuestionsButton.disabled = true;
  el.generateQuestionsButton.textContent = "Đang tạo…";
  try {
    const result = await api("/api/teacher/questions/generate", jsonOptions("POST", {
      language: el.generatedQuestionLanguage.value, subject: el.generatedQuestionSubject.value,
      topic: el.generatedQuestionTopic.value.trim() || null,
      easy_count: counts[0], medium_count: counts[1], hard_count: counts[2],
    }));
    const created = result.questions || [];
    const ids = new Set(created.map((item) => item.generated_id));
    state.generatedQuestions = [...created, ...state.generatedQuestions.filter((item) => !ids.has(item.generated_id))];
    el.generatedQuestionStatus.value = "draft";
    el.generatedQuestionSearch.value = "";
    el.generatedDifficultyFilter.value = "";
    renderGeneratedQuestions();
    const message = `Đã tạo ${created.length} câu; ${created.filter((item) => item.status === "draft").length} câu chờ duyệt.`;
    teacherFeedback(el.generatorFeedback, message, false);
    try { await loadGeneratedQuestions(); } catch (_) { teacherFeedback(el.generatorFeedback, `${message} Nhấn Làm mới để tải lại danh sách.`, false); }
  } catch (error) { teacherFeedback(el.generatorFeedback, error.message); }
  finally {
    state.generationBusy = false;
    controls.forEach((node, index) => { node.disabled = disabled[index]; });
    updateGeneratorPreview();
    el.generateQuestionsButton.textContent = "Tạo câu hỏi";
  }
}

async function decideGeneratedQuestion(button) {
  const id = String(button.dataset.generatedId), action = button.dataset.generatedAction;
  if (state.questionDeciding.has(id)) return;
  if (action === "approve" && !window.confirm("Duyệt câu hỏi này vào ngân hàng?")) return;
  state.questionDeciding.add(id);
  renderGeneratedQuestions();
  try {
    await api(`/api/teacher/questions/generated/${encodeURIComponent(id)}`, jsonOptions("PATCH", { action }));
    const item = state.generatedQuestions.find((item) => String(item.generated_id) === id);
    if (item) item.status = action === "approve" ? "approved" : "rejected";
    renderGeneratedQuestions();
    const refreshed = await Promise.allSettled([loadGeneratedQuestions(), refreshSummary()]);
    toast(`${action === "approve" ? "Đã duyệt câu hỏi." : "Đã từ chối câu hỏi."}${refreshed.some((r) => r.status === "rejected") ? " Một số dữ liệu chưa tải lại được." : ""}`);
  } catch (error) { toast(error.message, true); }
  finally { state.questionDeciding.delete(id); renderGeneratedQuestions(); }
}


function localInputValue(date) {
  const copy = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return copy.toISOString().slice(0, 16);
}

function getExamEndTime() {
  const start = new Date(el.examStartsAt.value);
  const durationMinutes = Number(el.examDuration.value);

  if (
    Number.isNaN(start.getTime())
    || !Number.isFinite(durationMinutes)
    || durationMinutes <= 0
  ) {
    return null;
  }

  return new Date(start.getTime() + durationMinutes * 60 * 1000);
}

function updateExamEndPreview() {
  const end = getExamEndTime();

  el.examEndPreview.textContent = end
    ? formatDate(end)
    : "Chưa đủ thông tin";
}

function setExamStartOffset(offsetMinutes) {
  const start = new Date(Date.now() + offsetMinutes * 60 * 1000);

  // Bỏ phần giây để thời gian dễ đọc.
  start.setSeconds(0, 0);

  el.examStartsAt.min = localInputValue(new Date());
  el.examStartsAt.value = localInputValue(start);

  updateExamEndPreview();
  el.examForm.querySelectorAll("[data-start-offset]").forEach((button) => button.setAttribute("aria-pressed", String(Number(button.dataset.startOffset) === offsetMinutes)));
}

function setDefaultExamTimes() {
  // Mặc định bắt đầu sau 15 phút và mở trong 2 giờ.
  el.examDuration.value = "120";
  setExamStartOffset(15);

  if (!el.examCode.value) {
    generateExamCode();
  }
  updateExamBankHint();
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function availabilityInfo(exam) {
  const values = {
    available: ["Đang mở", ""],
    not_started: ["Chưa đến giờ", "waiting"],
    expired: ["Đã hết giờ", "closed"],
    closed: ["Đã đóng", "closed"],
    draft: ["Bản nháp", "waiting"],
  };
  return values[exam.availability] || [exam.status, "closed"];
}

function examAvailability(exam) {
  if (exam.status === "closed") return "closed";
  if (exam.status !== "open") return exam.availability || "draft";
  const now = Date.now(), start = new Date(exam.starts_at).getTime(), end = new Date(exam.ends_at).getTime();
  if (Number.isFinite(start) && now < start) return "not_started";
  if (Number.isFinite(end) && now > end) return "expired";
  return "available";
}

function renderExams() {
  const search = el.examSearch.value.trim().toLocaleLowerCase("vi");
  const filter = el.examStatusFilter.value;
  const exams = state.exams.filter((exam) => (!filter || examAvailability(exam) === filter)
    && (!search || [exam.title, exam.exam_code, exam.subject].join(" ").toLocaleLowerCase("vi").includes(search)));
  el.examListCount.textContent = `${exams.length}${exams.length !== state.exams.length ? ` / ${state.exams.length}` : ""} bài thi`;
  el.examRows.innerHTML = exams.length
    ? exams.map((exam) => {
      const [label, style] = availabilityInfo({ ...exam, availability: examAvailability(exam) });
      const nextStatus = exam.status === "open" ? "closed" : "open";
      const cannotReopen = nextStatus === "open" && new Date(exam.ends_at).getTime() < Date.now();
      const id = escapeHtml(exam.exam_round_id);
      return `<article class="round-row">
        <div class="round-main"><div class="round-title"><strong>${escapeHtml(exam.title)}</strong><span class="status-badge ${style}">${escapeHtml(label)}</span></div>
          <div class="round-meta"><button type="button" class="exam-code-button" data-copy-exam-id="${id}" aria-label="Sao chép mã ${escapeHtml(exam.exam_code)}" title="Sao chép mã"><span>${escapeHtml(exam.exam_code)}</span>${lucideIcon("copy")}</button><small>${escapeHtml(exam.subject)} · ${escapeHtml(languageName(exam.language))} · ${escapeHtml(exam.question_count)} câu · ${escapeHtml(difficultyName(exam.starting_difficulty))}</small></div>
        </div>
        <div class="round-time"><strong>${escapeHtml(formatDate(exam.starts_at))}</strong><span>đến ${escapeHtml(formatDate(exam.ends_at))}</span></div>
        <div class="round-attempts"><strong>${escapeHtml(exam.attempt_count || 0)} lượt làm</strong><span>${escapeHtml(exam.completed_count || 0)} hoàn tất</span></div>
        <div class="round-actions">
          <button type="button" class="button secondary compact" data-exam-id="${id}" data-next-status="${nextStatus}" ${cannotReopen ? 'disabled title="Đã hết thời gian mở bài. Hãy tạo bài thi mới."' : ""}>${nextStatus === "closed" ? "Đóng" : "Mở lại"}</button>
          <button type="button" class="teacher-icon-button danger" data-delete-exam-id="${id}" aria-label="Xóa bài thi ${escapeHtml(exam.title)}" title="Xóa bài thi">${lucideIcon("trash")}</button>
        </div>
      </article>`;
    }).join("")
    : `<div class="empty-state">${state.exams.length ? "Không có bài thi phù hợp." : "Chưa có bài thi. Tạo bài thi đầu tiên ở phía trên."}</div>`;
}

async function copyExamCode(examId) {
  const code = state.exams.find((exam) => exam.exam_round_id === examId)?.exam_code;
  if (!code) return;
  try {
    if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
    await navigator.clipboard.writeText(code);
    toast(`Đã sao chép mã ${code}.`);
  } catch (_) {
    toast(`Không thể sao chép tự động. Mã bài thi: ${code}`, true);
  }
}

function generateExamCode() {
  const taken = new Set(state.exams.map((exam) => String(exam.exam_code).toUpperCase()));
  let code;
  do { code = `AI${Math.random().toString(36).slice(2, 9).toUpperCase()}`; } while (taken.has(code) || code.length < 4);
  el.examCode.value = code;
}

function selectedExamBank() {
  return state.summary?.languages?.find((item) => item.language === el.examLanguage.value)?.subjects?.find((subject) => subject.name === el.examSubject.value);
}

function updateExamBankHint() {
  const total = Number(selectedExamBank()?.total || 0);
  el.examBankHint.textContent = total ? `${total.toLocaleString("vi-VN")} câu có sẵn · tối đa ${Math.min(30, total)} câu / bài` : "Chưa có câu hỏi cho môn học này.";
  el.examQuestionCount.max = String(total ? Math.min(30, total) : 30);
  el.createExamButton.disabled = state.examCreating || !total;
}

function clearExamFeedback() {
  el.examFormFeedback.textContent = "";
  el.examFormFeedback.classList.add("hidden");
}

function validateExamForm() {
  const code = el.examCode.value.trim().toUpperCase();
  const count = Number(el.examQuestionCount.value), total = Number(selectedExamBank()?.total || 0);
  const startsAt = new Date(el.examStartsAt.value), endsAt = getExamEndTime();
  const checks = [
    [!el.examTitle.value.trim() || el.examTitle.value.trim().length > 160, "Nhập tên bài thi, tối đa 160 ký tự.", el.examTitle],
    [!total, "Môn học này chưa có câu hỏi. Hãy nhập câu hỏi trước.", el.examSubject],
    [!Number.isInteger(count) || count < 1 || count > Math.min(30, total), `Số câu phải từ 1 đến ${Math.min(30, total)}.`, el.examQuestionCount],
    [!/^[A-Z0-9_-]{4,20}$/.test(code), "Mã bài thi gồm 4–20 ký tự: chữ, số, gạch ngang hoặc gạch dưới.", el.examCode],
    [state.exams.some((exam) => String(exam.exam_code).toUpperCase() === code), "Mã này đã tồn tại. Hãy tạo hoặc nhập mã khác.", el.examCode],
    [!Number.isFinite(startsAt.getTime()) || !endsAt || startsAt.getTime() < Date.now() - 60000, "Chọn thời gian bắt đầu từ bây giờ trở đi.", el.examStartsAt],
  ];
  const failed = checks.find(([invalid]) => invalid);
  if (failed) {
    el.examFormFeedback.textContent = failed[1];
    el.examFormFeedback.classList.remove("hidden");
    failed[2].focus();
    return false;
  }
  clearExamFeedback();
  el.examCode.value = code;
  return true;
}

async function loadExams() {
  el.examRows.setAttribute("aria-busy", "true");
  try {
    const result = await api("/api/teacher/exams");
    state.exams = result.exams;
    renderExams();
  } finally {
    el.examRows.removeAttribute("aria-busy");
  }
}

async function refreshExams() {
  const originalLabel = el.refreshExamsButton.textContent;
  el.refreshExamsButton.disabled = true;
  el.refreshExamsButton.textContent = "Đang tải...";
  try {
    await loadExams();
    const time = new Intl.DateTimeFormat("vi-VN", { timeStyle: "medium" }).format(new Date());
    toast(`Đã làm mới danh sách lúc ${time}.`);
  } catch (error) {
    toast(`Không thể làm mới: ${error.message}`, true);
  } finally {
    el.refreshExamsButton.disabled = false;
    el.refreshExamsButton.textContent = originalLabel;
  }
}

async function createExam(event) {
  event.preventDefault();
  if (state.examCreating || !validateExamForm()) return;
  state.examCreating = true;
  el.createExamButton.disabled = true;
  el.createExamButton.textContent = "Đang tạo…";
  const controls = [...el.examForm.querySelectorAll("input, select, button")].filter((control) => control !== el.createExamButton);
  const disabledStates = controls.map((control) => control.disabled);
  controls.forEach((control) => { control.disabled = true; });
  const language = el.examLanguage.value, subject = el.examSubject.value;
  try {
    const payload = {
      title: el.examTitle.value.trim(),
      exam_code: el.examCode.value.trim().toUpperCase(),
      language, subject,
      question_count: Number(el.examQuestionCount.value),
      starting_difficulty: document.querySelector('input[name="examDifficulty"]:checked').value,
      answer_mode: el.examAnswerMode.value,
      starts_at: new Date(el.examStartsAt.value).toISOString(),
      ends_at: getExamEndTime().toISOString(),
    };
    const result = await api("/api/teacher/exams", jsonOptions("POST", payload));
    // Remember successful creation even if the following list refresh fails.
    state.exams = [result.exam, ...state.exams.filter((exam) => exam.exam_round_id !== result.exam.exam_round_id)];
    renderExams();
    toast(`Đã tạo bài thi · mã ${result.exam.exam_code}.`);
    el.examForm.reset();
    el.examLanguage.value = language;
    updateSubjectSelect(el.examLanguage, el.examSubject, false);
    el.examSubject.value = subject;
    setDefaultExamTimes();
    try { await loadExams(); } catch (_) { toast(`Đã tạo mã ${result.exam.exam_code}. Chưa tải lại được danh sách; nhấn Làm mới.`, true); }
  } catch (error) {
    el.examFormFeedback.textContent = error.message;
    el.examFormFeedback.classList.remove("hidden");
    toast(error.message, true);
  } finally {
    state.examCreating = false;
    controls.forEach((control, index) => { control.disabled = disabledStates[index]; });
    updateExamBankHint();
    el.createExamButton.textContent = "Tạo bài thi";
  }
}

async function changeExamStatus(button) {
  button.disabled = true;
  try {
    await api(`/api/teacher/exams/${button.dataset.examId}/status`, jsonOptions("PATCH", { status: button.dataset.nextStatus }));
    await loadExams();
    toast(button.dataset.nextStatus === "closed" ? "Đã đóng Interview." : "Đã mở lại Interview.");
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function deleteExamRound(examRoundId) {
  const exam = state.exams.find((item) => item.exam_round_id === examRoundId);
  const examLabel = exam ? `“${exam.title}” (${exam.exam_code})` : "này";
  const confirmed = window.confirm(
    `Xóa vĩnh viễn bài Interview ${examLabel}?\n\nToàn bộ lượt làm, câu trả lời và báo cáo liên quan cũng sẽ bị xóa.`,
  );
  if (!confirmed) return;

  try {
    const result = await api(`/api/teacher/exams/${encodeURIComponent(examRoundId)}`, { method: "DELETE" });
    await loadExams();
    toast(`Đã xóa bài Interview ${result.exam_code} cùng ${result.deleted_attempts} lượt làm liên quan.`);
  } catch (error) {
    toast(error.message, true);
  }
}

function renderAccounts() {
  const search = el.accountSearch.value.trim().toLocaleLowerCase("vi");
  const accounts = state.accounts.filter((a) => (!el.accountRoleFilter.value || a.role === el.accountRoleFilter.value)
    && (!el.accountStatusFilter.value || Boolean(a.active) === (el.accountStatusFilter.value === "active"))
    && (!search || [a.username, a.full_name, a.email, a.student_id].join(" ").toLocaleLowerCase("vi").includes(search)));
  el.accountCount.textContent = `${accounts.length} / ${state.accounts.length} tài khoản`;
  el.accountRows.innerHTML = accounts.length ? accounts.map((a) => {
    const own = String(a.user_id) === String(state.user?.user_id), busy = state.accountChanging.has(String(a.user_id));
    return `<tr><td><strong>${escapeHtml(a.username)}</strong>${own ? '<small class="account-self">Bạn</small>' : ""}</td><td>${escapeHtml(a.full_name)}</td><td><span class="role-badge ${a.role === "teacher" ? "teacher" : "candidate"}">${a.role === "teacher" ? "Giáo viên" : "Sinh viên"}</span></td><td><span class="account-meta"><span>${escapeHtml(a.email || "—")}</span><small>${escapeHtml(a.student_id || "")}</small></span></td><td><span class="status-badge ${a.active ? "" : "closed"}">${a.active ? "Hoạt động" : "Đã khóa"}</span></td><td><button type="button" class="button secondary compact" data-account-id="${escapeHtml(a.user_id)}" data-account-active="${!a.active}" ${own || busy ? "disabled" : ""} ${own ? 'title="Không thể tự khóa tài khoản đang đăng nhập"' : ""}>${busy ? "Đang lưu…" : a.active ? "Khóa" : "Mở khóa"}</button></td></tr>`;
  }).join("") : '<tr><td colspan="6" class="empty-state">Không có tài khoản phù hợp.</td></tr>';
}

async function loadAccounts() {
  const sequence = ++state.accountLoadSequence;
  el.accountRows.setAttribute("aria-busy", "true");
  try {
    const result = await api("/api/teacher/accounts");
    if (sequence !== state.accountLoadSequence) return;
    state.accounts = result.accounts || [];
    renderAccounts(); teacherFeedback(el.accountsFeedback, "");
  } catch (error) { if (sequence === state.accountLoadSequence) teacherFeedback(el.accountsFeedback, error.message); throw error; }
  finally { if (sequence === state.accountLoadSequence) el.accountRows.removeAttribute("aria-busy"); }
}

async function refreshAccounts() {
  el.refreshAccountsButton.disabled = true;
  try { await loadAccounts(); } catch (_) { /* The error remains beside the account table. */ }
  finally { el.refreshAccountsButton.disabled = false; }
}

function updateAccountFile() {
  const file = el.accountFile.files?.[0];
  const error = file && (!/\.(xlsx|csv|json)$/i.test(file.name) ? "Chọn file Excel .xlsx, CSV hoặc JSON." : file.size > 25 * 1024 * 1024 ? "File vượt quá 25 MB." : !file.size ? "File đang trống." : "");
  el.accountFileName.textContent = file ? `${file.name} · ${(file.size / 1024 / 1024).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} MB` : "Excel, CSV, JSON · tối đa 25 MB";
  el.accountImportButton.disabled = state.accountImporting || !file || Boolean(error);
  el.clearAccountFileButton.classList.toggle("hidden", !file);
  el.accountFile.setCustomValidity(error || "");
  teacherFeedback(el.accountImportFeedback, error || "");
  return Boolean(file) && !error;
}

async function importAccounts(event) {
  event.preventDefault();
  if (state.accountImporting || !updateAccountFile()) return;
  if (el.accountImportMode.value === "replace" && !window.confirm("Các tài khoản không có trong file sẽ bị khóa. Tiếp tục?")) return;
  const form = new FormData(); form.append("file", el.accountFile.files[0]); form.append("mode", el.accountImportMode.value);
  state.accountImporting = true;
  [el.accountImportButton, el.accountFile, el.accountImportMode, el.clearAccountFileButton].forEach((node) => { node.disabled = true; });
  el.accountImportButton.textContent = "Đang nhập…";
  try {
    const result = await api("/api/teacher/accounts/import", { method: "POST", body: form });
    state.accounts = result.accounts || []; renderAccounts();
    el.accountUploadForm.reset(); updateAccountFile();
    teacherFeedback(el.accountImportFeedback, `Đã nhập ${result.imported} tài khoản: ${result.created} mới, ${result.updated} cập nhật.`, false);
  } catch (error) { teacherFeedback(el.accountImportFeedback, error.message); }
  finally {
    state.accountImporting = false;
    [el.accountFile, el.accountImportMode, el.clearAccountFileButton].forEach((node) => { node.disabled = false; });
    el.accountImportButton.disabled = !el.accountFile.files?.length || Boolean(el.accountFile.validationMessage);
    el.accountImportButton.textContent = "Nhập tài khoản";
  }
}

async function toggleAccount(button) {
  const id = String(button.dataset.accountId), active = button.dataset.accountActive === "true";
  if (id === String(state.user?.user_id) || state.accountChanging.has(id)) return;
  if (!active && !window.confirm("Khóa tài khoản này? Người dùng sẽ không thể đăng nhập khi tài khoản bị khóa.")) return;
  state.accountChanging.add(id); renderAccounts();
  try {
    const result = await api(`/api/teacher/accounts/${encodeURIComponent(id)}/active`, jsonOptions("PATCH", { active }));
    const account = state.accounts.find((a) => String(a.user_id) === id);
    if (account) Object.assign(account, result.account || { active });
    renderAccounts();
    try { await loadAccounts(); } catch (_) { /* Preserve the successfully updated local row. */ }
    toast(active ? "Đã mở khóa tài khoản." : "Đã khóa tài khoản.");
  } catch (error) { toast(error.message, true); }
  finally { state.accountChanging.delete(id); renderAccounts(); }
}


function renderTeacherSummary() {
  const requiredCount = state.reviewQueue.filter((item) => !item.reviewed_at).length;
  el.teacherTotalResults.textContent = state.teacherResultsLoaded ? state.results.length : "—";
  el.teacherCompletedResults.textContent = state.teacherResultsLoaded ? state.results.filter((item) => item.status === "completed").length : "—";
  el.teacherPendingAnswers.textContent = state.teacherReviewsLoaded ? requiredCount : "—";
  el.reviewQueueCount.textContent = state.teacherReviewsLoaded ? String(state.reviewQueue.length) : "—";
}

function renderResults() {
  const search = el.teacherResultSearch.value.trim().toLocaleLowerCase("vi"), status = el.teacherResultStatus.value;
  const results = state.results.filter((r) => (!search || [r.candidate_name, r.student_id, r.username, r.email, r.exam_code, r.subject].join(" ").toLocaleLowerCase("vi").includes(search))
    && (!status || (status === "pending" ? Number(r.pending_review_count) > 0 : status === "completed" ? r.status === "completed" : r.status !== "completed")));
  el.teacherResultCount.textContent = `${results.length} / ${state.results.length} bài làm`;
  el.teacherResultRows.innerHTML = results.length ? results.map((r) => {
    const id = escapeHtml(r.session_id), deleting = state.teacherDeleting.has(String(r.session_id));
    const score = state.teacherResultsStale ? '<span title="Vừa chấm lại; cần làm mới điểm">Chờ cập nhật</span>' : r.average_score == null ? "—" : `<strong>${reportNumber(r.average_score)}/100</strong>`;
    return `<tr><td><strong>${escapeHtml(r.exam_code)}</strong><small class="cell-subtext">${escapeHtml(r.subject)}</small></td><td><strong>${escapeHtml(r.candidate_name)}</strong><small class="cell-subtext">${escapeHtml(r.student_id || r.email || r.username || "")}</small></td><td>${escapeHtml(r.answered_count)}/${escapeHtml(r.requested_count)} câu<small class="cell-subtext">${r.status === "completed" ? "Hoàn tất" : "Đang làm"}</small></td><td>${score}${r.pending_review_count ? `<button type="button" class="pending-review-link" data-review-result-session="${id}" ${deleting ? "disabled" : ""}>Chấm lại ${escapeHtml(r.pending_review_count)} câu</button>` : ""}</td><td>${escapeHtml(formatDate(r.finished_at || r.created_at))}</td><td><div class="table-actions"><button type="button" class="button secondary compact" data-result-session="${id}" ${deleting ? "disabled" : ""}>Báo cáo</button><button type="button" class="teacher-delete-button" data-delete-result-session="${id}" aria-label="Xóa bài làm của ${escapeHtml(r.candidate_name)}" title="Xóa bài làm" ${deleting ? "disabled" : ""}>×</button></div></td></tr>`;
  }).join("") : `<tr><td colspan="6" class="empty-state">${state.teacherResultsLoaded ? state.results.length ? "Không có kết quả phù hợp." : "Chưa có sinh viên làm bài." : "Chưa tải được kết quả. Nhấn Làm mới để thử lại."}</td></tr>`;
  renderTeacherSummary();
}

function setTeacherResultPane(pane) {
  rememberReviewDraft();
  state.teacherResultPane = pane === "reviews" ? "reviews" : "results";
  const reviews = state.teacherResultPane === "reviews";
  el.teacherResultsPanel.classList.toggle("hidden", reviews);
  el.teacherReviewsPanel.classList.toggle("hidden", !reviews);
  el.teacherResultsButton.setAttribute("aria-pressed", String(!reviews));
  el.teacherReviewsButton.setAttribute("aria-pressed", String(reviews));
  if (!reviews) el.reviewAudio.pause?.();
}

async function loadTeacherWorkspace() {
  const sequence = ++state.teacherWorkspaceSequence;
  rememberReviewDraft();
  el.teacherResultRows.setAttribute("aria-busy", "true"); el.teacherReviewRows.setAttribute("aria-busy", "true");
  const response = await Promise.allSettled([api("/api/teacher/results"), api("/api/teacher/reviews")]);
  if (sequence !== state.teacherWorkspaceSequence) return false;
  const errors = [];
  if (response[0].status === "fulfilled") {
    state.results = response[0].value.results || [];
    state.teacherResultsLoaded = true; state.teacherResultsStale = false;
  } else errors.push(`Kết quả: ${response[0].reason.message}`);
  if (response[1].status === "fulfilled") {
    state.reviewQueue = response[1].value.answers || []; state.teacherReviewsLoaded = true;
    const threshold = Number(response[1].value.score_threshold);
    if (Number.isFinite(threshold)) state.reviewThreshold = threshold;
    el.reviewThresholdValue.textContent = Number.isFinite(threshold) ? `Ngưỡng: ${reportNumber(threshold)} điểm` : "Ngưỡng từ hệ thống";
  } else errors.push(`Chấm lại: ${response[1].reason.message}`);
  teacherFeedback(el.teacherWorkspaceFeedback, errors.join(" · "));
  if (state.selectedReviewAnswerId && !reviewItem()) state.selectedReviewAnswerId = "";
  renderResults(); renderReviewQueue(); renderReviewDetail();
  el.teacherResultRows.removeAttribute("aria-busy"); el.teacherReviewRows.removeAttribute("aria-busy");
  return errors.length === 0;
}

async function loadResults() { return loadTeacherWorkspace(); }
async function loadReviewQueue() { return loadTeacherWorkspace(); }

async function refreshTeacherWorkspace() {
  if (state.reviewSaving) { toast("Đang lưu điểm. Vui lòng chờ."); return; }
  el.refreshTeacherWorkspaceButton.disabled = true; el.refreshReviewQueueButton.disabled = true;
  state.reviewReportCache.clear(); state.reviewHistoryCache.clear();
  try {
    await loadTeacherWorkspace();
    const item = reviewItem(); if (item) await loadReviewEvidence(item);
  } finally { el.refreshTeacherWorkspaceButton.disabled = false; el.refreshReviewQueueButton.disabled = false; }
}

async function deleteTeacherResult(sessionId) {
  if (state.reviewSaving || state.teacherDeleting.has(String(sessionId))) return;
  if (!window.confirm("Xóa vĩnh viễn bài làm, câu trả lời và báo cáo này? Nếu bài thi vẫn mở, sinh viên có thể làm lại mã bài thi.")) return;
  state.teacherDeleting.add(String(sessionId)); renderResults();
  try {
    await api(`/api/teacher/results/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    state.results = state.results.filter((r) => r.session_id !== sessionId);
    for (const item of state.reviewQueue.filter((item) => item.session_id === sessionId)) {
      delete state.reviewDrafts[String(item.answer_id)];
      state.reviewHistoryCache.delete(String(item.answer_id));
    }
    state.reviewQueue = state.reviewQueue.filter((item) => item.session_id !== sessionId);
    state.reviewReportCache.delete(sessionId);
    if (state.manualReviewItem?.session_id === sessionId) { delete state.reviewDrafts[String(state.manualReviewItem.answer_id)]; state.manualReviewItem = null; }
    if (state.reviewSessionFilter === sessionId) state.reviewSessionFilter = "";
    if (!reviewItem()) state.selectedReviewAnswerId = "";
    if (state.lastReviewedSessionId === sessionId) state.lastReviewedSessionId = "";
    renderResults(); renderReviewQueue(); renderReviewDetail();
    const refreshed = await loadTeacherWorkspace();
    toast(refreshed ? "Đã xóa bài làm và các câu chờ chấm liên quan." : "Đã xóa bài làm. Một số dữ liệu chưa tải lại được.");
  } catch (error) { toast(error.message, true); }
  finally { state.teacherDeleting.delete(String(sessionId)); renderResults(); }
}

function reviewItem() {
  return state.reviewQueue.find((item) => String(item.answer_id) === state.selectedReviewAnswerId)
    || (state.manualReviewItem && String(state.manualReviewItem.answer_id) === state.selectedReviewAnswerId ? state.manualReviewItem : null);
}

function rememberReviewDraft() {
  if (state.selectedReviewAnswerId && reviewItem()) state.reviewDrafts[state.selectedReviewAnswerId] = { score: String(el.reviewScore.value), feedback: el.reviewFeedback.value };
}

function renderReviewQueue() {
  const sessions = new Map();
  for (const item of state.reviewQueue) sessions.set(item.session_id, `${item.candidate_name} · ${item.exam_code || item.subject}`);
  if (state.reviewSessionFilter && !sessions.has(state.reviewSessionFilter)) {
    const result = state.results.find((r) => r.session_id === state.reviewSessionFilter);
    sessions.set(state.reviewSessionFilter, result ? `${result.candidate_name} · ${result.exam_code}` : "Bài làm đã chọn");
  }
  el.reviewSessionSelect.innerHTML = '<option value="">Mọi bài làm</option>' + [...sessions].map(([id, label]) => `<option value="${escapeHtml(id)}">${escapeHtml(label)}</option>`).join("");
  el.reviewSessionSelect.value = state.reviewSessionFilter;
  const search = el.reviewSearch.value.trim().toLocaleLowerCase("vi");
  const items = state.reviewQueue.filter((item) => {
    const r = state.results.find((r) => r.session_id === item.session_id) || {};
    return (!state.reviewSessionFilter || item.session_id === state.reviewSessionFilter)
      && (!search || [item.candidate_name, item.exam_code, item.question, item.subject, r.student_id, r.username].join(" ").toLocaleLowerCase("vi").includes(search));
  });
  el.reviewVisibleCount.textContent = `${items.length} câu`;
  el.teacherReviewRows.innerHTML = items.length ? items.map((item) => {
    const selected = String(item.answer_id) === state.selectedReviewAnswerId;
    const analyzing = state.reviewAnalyzing.has(String(item.answer_id));
    const statusClass = item.reviewed_at ? "reviewed" : analyzing ? "processing" : item.strong_review_ready ? "pending" : "waiting";
    const statusLabel = item.reviewed_at ? "Đã chốt" : analyzing ? "Đang xử lý" : item.strong_review_ready ? "Chờ quyết định" : "Chờ AI";
    const scoreText = item.reviewed_at
      ? `${reportNumber(item.final_score)}/100 điểm cuối`
      : item.strong_review_ready
      ? `${reportNumber(item.review_ai_score)}/100 điểm đề xuất`
      : "Model mạnh chưa hoàn tất";
    return `<button type="button" class="review-answer-choice ${statusClass}${selected ? " selected" : ""}" data-review-answer="${escapeHtml(item.answer_id)}" data-review-session="${escapeHtml(item.session_id)}" aria-pressed="${selected}" ${state.reviewSaving ? "disabled" : ""}><span class="review-choice-heading"><strong>${escapeHtml(item.candidate_name)}</strong><i>${statusLabel}</i></span><span>${escapeHtml(item.exam_code || item.subject)} · Câu ${escapeHtml(item.sequence_number)}</span><small>${escapeHtml(item.question)}</small><span class="review-choice-score">${scoreText}</span></button>`;
  }).join("")
    : `<div class="empty-state">${state.teacherReviewsLoaded ? "Chưa có câu trả lời phù hợp." : "Chưa tải được dữ liệu. Nhấn Làm mới."}</div>`;
  renderTeacherSummary();
}

function reviewFromReport(report, answer, sessionId) {
  const e = answer.evaluation || {}, r = state.results.find((r) => r.session_id === sessionId) || {};
  return { answer_id: answer.answer_id, session_id: sessionId, sequence_number: answer.sequence_number,
    candidate_name: report.session?.candidate_name || r.candidate_name, exam_code: r.exam_code,
    title: r.title || report.session?.subject, subject: report.session?.subject,
    question: answer.question?.question || "", answer_text: answer.answer,
    original_ai_score: e.ai_score ?? e.score, ai_score: e.review_ai_score ?? e.ai_score ?? e.score,
    review_ai_score: e.review_ai_score, final_score: e.final_score, confidence: e.confidence,
    feedback: e.feedback, teacher_feedback: e.teacher_feedback, reviewed_at: e.reviewed_at,
    transcription_id: answer.voice?.transcription_id, audio_available: Boolean(answer.voice?.audio_available),
    original_transcript: answer.voice?.verified_transcript || answer.answer,
    review_transcript: answer.voice?.review_transcript, review_model: answer.voice?.review_model,
    review_runtime: answer.voice?.review_runtime, review_confidence: answer.voice?.review_confidence,
    review_ai_feedback: e.review_ai_feedback, review_ai_evaluation: e.review_ai_evaluation,
    strong_review_ready: Boolean(answer.voice?.review_processed_at && e.review_ai_at),
    audio_required: false,
    below_threshold: e.review_ai_score != null && Number(e.review_ai_score) < state.reviewThreshold,
    can_accept_ai: e.review_ai_score != null };
}

function renderReviewDetail() {
  const item = reviewItem();
  el.reviewDetailContent.classList.toggle("hidden", !item);
  el.reviewDetailEmpty.classList.toggle("hidden", Boolean(item));
  el.reviewReturnReportButton.classList.toggle("hidden", Boolean(item) || !state.lastReviewedSessionId);
  if (!item) {
    el.reviewAudio.pause?.(); el.reviewAudio.removeAttribute("src"); delete el.reviewAudio.dataset.transcriptionId;
    el.reviewDetailEmpty.textContent = state.lastReviewedSessionId ? "Đã lưu điểm. Chọn câu khác hoặc mở báo cáo vừa chấm." : "Chọn một câu để chấm lại.";
    return;
  }
  const report = state.reviewReportCache.get(item.session_id);
  const answer = report?.answers?.find((answer) => String(answer.answer_id) === String(item.answer_id));
  const evaluation = answer?.evaluation || {};
  const draft = state.reviewDrafts[String(item.answer_id)];
  el.reviewStudentName.textContent = item.candidate_name || "Sinh viên";
  el.reviewExamMeta.textContent = `${item.exam_code || item.subject || "Bài thi"} · Câu ${item.sequence_number}`;
  const analyzing = state.reviewAnalyzing.has(String(item.answer_id));
  const strongReady = Boolean(item.strong_review_ready);
  const strongEvaluation = item.review_ai_evaluation || evaluation.review_ai_evaluation || {};
  const strongScore = item.review_ai_score ?? evaluation.review_ai_score;
  const originalScore = item.original_ai_score ?? evaluation.ai_score ?? item.ai_score;
  const finalScore = item.final_score ?? evaluation.final_score;
  el.reviewOriginalScore.textContent = originalScore == null ? "—" : `${reportNumber(originalScore)}/100`;
  el.reviewAiScore.textContent = strongReady && strongScore != null ? `${reportNumber(strongScore)}/100` : "—";
  el.reviewFinalScore.textContent = finalScore == null ? "Chờ duyệt" : `${reportNumber(finalScore)}/100`;
  el.reviewFinalScore.closest(".final")?.classList.toggle("confirmed", finalScore != null);
  el.reviewDecisionStatus.textContent = finalScore == null ? "Giảng viên quyết định" : `Đã chốt ${formatDate(item.reviewed_at || evaluation.reviewed_at)}`;
  el.reviewConfidence.textContent = analyzing ? "Đang chạy model mạnh…" : strongReady ? `Tin cậy STT ${reportNumber(Number(item.review_confidence || answer?.voice?.review_confidence || 0) * 100)}%` : "Chưa xử lý";
  el.reviewQuestion.textContent = item.question || "";
  el.reviewAnswerText.textContent = item.original_transcript || answer?.voice?.verified_transcript || answer?.answer || item.answer_text || "Chưa có nội dung";
  el.reviewStrongTranscript.textContent = analyzing ? "Đang chuyển lại voice thành text…" : item.review_transcript || answer?.voice?.review_transcript || "Chưa xử lý";
  el.reviewStrongTranscript.closest(".review-answer-block")?.classList.toggle("is-loading", analyzing);
  el.reviewStrongModel.textContent = strongReady ? `${item.review_model || answer?.voice?.review_model || "large-v3"} · ${item.review_runtime || answer?.voice?.review_runtime || "local"}` : "";
  el.reviewAiFeedback.textContent = item.review_ai_feedback || strongEvaluation.feedback || evaluation.review_ai_feedback || "Chưa có nhận xét từ lượt chấm lại";
  el.reviewReferenceAnswer.textContent = answer?.reference_answer || "Chưa tải được đáp án tham khảo";
  el.reviewRawTranscript.textContent = answer?.voice?.raw_transcript || "Chưa có bản STT gốc";
  el.reviewRubric.innerHTML = pointAssessmentHtml(strongEvaluation.point_assessments || []);
  el.reviewEvidenceStatus.textContent = report ? "" : "Đang tải chi tiết…";
  el.reviewManualLabel.classList.toggle("hidden", !state.manualReviewItem || String(state.manualReviewItem.answer_id) !== String(item.answer_id));
  el.reviewScore.value = draft ? draft.score : String(finalScore ?? strongScore ?? item.ai_score ?? 0);
  el.reviewFeedback.value = draft ? draft.feedback : evaluation.teacher_feedback || item.teacher_feedback || item.review_ai_feedback || "";
  const audioId = answer ? answer.voice?.audio_available ? answer.voice.transcription_id : "" : item.audio_available === false ? "" : item.transcription_id;
  const belowThreshold = strongReady && (item.below_threshold ?? Number(strongScore || 0) < state.reviewThreshold);
  const canAcceptAi = strongReady && (item.can_accept_ai ?? true);
  el.reviewPolicyNotice.classList.toggle("required", belowThreshold || !strongReady);
  el.reviewPolicyNotice.textContent = analyzing
    ? "Model large-v3 đang chuyển lại voice và chấm lại theo rubric."
    : !strongReady
    ? "Chưa có kết quả từ model mạnh. Hệ thống sẽ xử lý lại voice trước khi cho phép dùng điểm AI."
    : belowThreshold
    ? "Điểm AI dưới trung bình. Giảng viên có thể nghe voice bao nhiêu lần tùy ý, dùng điểm AI hoặc tự chấm lại."
    : "Giảng viên có thể dùng điểm AI, tự chấm lại, hoặc nghe voice bao nhiêu lần tùy ý.";
  el.reviewAcceptAiButton.classList.toggle("hidden", !canAcceptAi);
  if (el.reviewAudio.dataset.transcriptionId !== (audioId || "")) {
    el.reviewAudio.pause?.();
    if (audioId) el.reviewAudio.src = `/api/teacher/transcriptions/${encodeURIComponent(audioId)}/audio`;
    else el.reviewAudio.removeAttribute("src");
    el.reviewAudio.dataset.transcriptionId = audioId || "";
  }
  el.reviewAudio.classList.toggle("hidden", !audioId);
  el.reviewAudioStatus.classList.toggle("hidden", Boolean(audioId)); el.reviewAudioStatus.textContent = "Không có ghi âm";
  [el.reviewScore, el.reviewFeedback].forEach((node) => { node.disabled = state.reviewSaving; });
  el.reviewAcceptAiButton.disabled = state.reviewSaving || analyzing || !strongReady;
  el.reviewSaveButton.disabled = state.reviewSaving || analyzing;
  el.reviewSaveButton.textContent = state.reviewSaving ? "Đang lưu…" : "Lưu điểm chấm lại";
  renderReviewHistory(item);
}

function renderReviewHistory(item) {
  const answerId = String(item?.answer_id || "");
  const loading = state.reviewHistoryLoading.has(answerId);
  const history = state.reviewHistoryCache.get(answerId);
  el.reviewHistoryCount.textContent = Array.isArray(history) ? String(history.length) : "0";
  if (loading) {
    el.reviewHistoryRows.innerHTML = '<p class="review-history-loading">Đang tải lịch sử…</p>';
    return;
  }
  if (!Array.isArray(history)) {
    el.reviewHistoryRows.innerHTML = '<p class="muted">Lịch sử sẽ hiển thị tại đây.</p>';
    return;
  }
  el.reviewHistoryRows.innerHTML = history.length
    ? history.slice().reverse().map((entry) => `<article class="review-history-item"><div><strong>${reportNumber(entry.teacher_score)}/100</strong><span>${escapeHtml(entry.reviewed_by || "Giảng viên")} · ${escapeHtml(formatDate(entry.created_at))}</span></div><p>${escapeHtml(entry.feedback || "Không có nhận xét")}</p><small>Từ ${reportNumber(entry.previous_final_score)} lên ${reportNumber(entry.teacher_score)} điểm</small></article>`).join("")
    : '<p class="muted">Chưa có lần chấm nào.</p>';
}

async function loadReviewHistory(item, { refresh = false } = {}) {
  const answerId = String(item?.answer_id || "");
  if (!answerId || state.reviewHistoryLoading.has(answerId)) return;
  if (!refresh && state.reviewHistoryCache.has(answerId)) { renderReviewDetail(); return; }
  state.reviewHistoryLoading.add(answerId); renderReviewDetail();
  try {
    const result = await api(`/api/teacher/answers/${encodeURIComponent(answerId)}/reviews`);
    state.reviewHistoryCache.set(answerId, result.reviews || []);
  } catch (error) {
    state.reviewHistoryCache.set(answerId, []);
    teacherFeedback(el.reviewFormFeedback, `Không tải được lịch sử chấm: ${error.message}`);
  } finally {
    state.reviewHistoryLoading.delete(answerId);
    if (String(reviewItem()?.answer_id || "") === answerId) renderReviewDetail();
  }
}

async function loadReviewEvidence(item) {
  const sequence = ++state.reviewEvidenceSequence;
  if (state.reviewReportCache.has(item.session_id)) { if (reviewItem()?.answer_id === item.answer_id) { rememberReviewDraft(); renderReviewDetail(); } return; }
  try {
    const report = await api(`/api/teacher/results/${encodeURIComponent(item.session_id)}`);
    if (sequence !== state.reviewEvidenceSequence) return;
    state.reviewReportCache.set(item.session_id, report);
    if (sequence === state.reviewEvidenceSequence && state.selectedReviewAnswerId === String(item.answer_id)) { rememberReviewDraft(); renderReviewDetail(); }
  } catch (_) {
    if (sequence === state.reviewEvidenceSequence && state.selectedReviewAnswerId === String(item.answer_id)) el.reviewEvidenceStatus.textContent = "Chưa tải được chi tiết. Nhấn Làm mới để thử lại.";
  }
}

async function loadStrongReview(item) {
  const answerId = String(item?.answer_id || "");
  if (!answerId || item.strong_review_ready || state.reviewAnalyzing.has(answerId)) return;
  state.reviewAnalyzing.add(answerId);
  renderReviewQueue(); renderReviewDetail();
  try {
    const result = await api(`/api/teacher/answers/${encodeURIComponent(answerId)}/ai-review`, { method: "POST" });
    Object.assign(item, result, {
      ai_score: result.review_ai_score,
      feedback: result.review_ai_feedback,
      review_policy: result.below_threshold ? "teacher_decision_recommended" : "teacher_choice",
    });
    const report = state.reviewReportCache.get(item.session_id);
    const answer = report?.answers?.find((entry) => String(entry.answer_id) === answerId);
    if (answer) {
      answer.voice = { ...(answer.voice || {}), review_transcript: result.review_transcript,
        review_model: result.review_model, review_runtime: result.review_runtime,
        review_confidence: result.review_confidence, review_processed_at: result.review_processed_at };
      answer.evaluation = { ...(answer.evaluation || {}), review_ai_score: result.review_ai_score,
        review_ai_feedback: result.review_ai_feedback, review_ai_evaluation: result.review_ai_evaluation,
        review_ai_at: result.review_processed_at };
    }
  } catch (error) {
    teacherFeedback(el.reviewFormFeedback, `Không thể chạy model mạnh: ${error.message}`);
  } finally {
    state.reviewAnalyzing.delete(answerId);
    renderReviewQueue(); renderReviewDetail();
  }
}

async function selectReviewAnswer(answerId) {
  if (state.reviewSaving) return;
  rememberReviewDraft(); el.reviewAudio.pause?.();
  state.selectedReviewAnswerId = String(answerId);
  teacherFeedback(el.reviewFormFeedback, "");
  renderReviewQueue(); renderReviewDetail();
  const item = reviewItem();
  if (item) {
    await Promise.all([loadReviewEvidence(item), loadReviewHistory(item)]);
    await loadStrongReview(item);
  }
}

async function openReviewSession(sessionId, answerId = "") {
  if (state.reviewSaving) return;
  const sequence = ++state.reviewOpenSequence;
  const cached = state.currentTeacherReportSessionId === sessionId ? state.currentTeacherReport : state.reviewReportCache.get(sessionId);
  const answer = cached?.answers?.find((item) => String(item.answer_id) === String(answerId));
  if (answer) {
    state.reviewReportCache.set(sessionId, cached);
    state.manualReviewItem = reviewFromReport(cached, answer, sessionId);
  } else state.manualReviewItem = null;
  dismissReportDialog(); showView("teacherResultsView"); setTeacherResultPane("reviews");
  state.reviewSessionFilter = sessionId; el.reviewSearch.value = "";
  await loadTeacherWorkspace();
  if (sequence !== state.reviewOpenSequence) return;
  const pending = state.reviewQueue.filter((item) => item.session_id === sessionId);
  const selected = answerId || pending[0]?.answer_id || "";
  await selectReviewAnswer(selected);
  el.teacherReviewsPanel.scrollIntoView?.({ behavior: "smooth", block: "start" });
}

async function refreshOpenTeacherReport(sessionId) {
  if (!el.reportDialog.open || state.reportOrigin !== "teacher" || state.currentTeacherReportSessionId !== sessionId) return;
  const sequence = state.teacherReportSequence;
  const report = await api(`/api/teacher/results/${encodeURIComponent(sessionId)}`);
  if (sequence !== state.teacherReportSequence) return;
  state.reviewReportCache.set(sessionId, report);
  if (el.reportDialog.open && state.currentTeacherReportSessionId === sessionId && state.reportOrigin === "teacher") { state.currentTeacherReport = report; renderReport(report); }
}

async function submitTeacherReview(event, action = "manual") {
  event.preventDefault();
  const item = reviewItem(); if (!item || state.reviewSaving) return;
  const scoreText = String(el.reviewScore.value).trim(), score = Number(scoreText), feedback = el.reviewFeedback.value.trim();
  if (!scoreText || !Number.isFinite(score) || score < 0 || score > 100) { teacherFeedback(el.reviewFormFeedback, "Nhập điểm từ 0 đến 100."); el.reviewScore.focus(); return; }
  if (!feedback || feedback.length > 2000) { teacherFeedback(el.reviewFormFeedback, "Nhập nhận xét, tối đa 2000 ký tự."); el.reviewFeedback.focus(); return; }
  rememberReviewDraft(); state.reviewSaving = true; teacherFeedback(el.reviewFormFeedback, ""); renderReviewDetail(); renderReviewQueue();
  let saved = false;
  try {
    await api(`/api/teacher/answers/${encodeURIComponent(item.answer_id)}/review`, jsonOptions("PATCH", { action, score, feedback }));
    saved = true; state.reviewEvidenceSequence += 1; state.lastReviewedSessionId = item.session_id;
    state.reviewHistoryCache.delete(String(item.answer_id));
    delete state.reviewDrafts[String(item.answer_id)]; state.reviewReportCache.delete(item.session_id);
    state.reviewQueue = state.reviewQueue.map((q) => String(q.answer_id) === String(item.answer_id)
      ? { ...q, final_score: score, teacher_score: score, teacher_feedback: feedback, reviewed_at: new Date().toISOString() }
      : q);
    state.manualReviewItem = null; state.selectedReviewAnswerId = ""; state.teacherResultsStale = true;
    const r = state.results.find((r) => r.session_id === item.session_id); if (r && r.pending_review_count) r.pending_review_count = Math.max(0, Number(r.pending_review_count) - 1);
    renderResults(); renderReviewQueue(); renderReviewDetail();
    const refreshed = await Promise.allSettled([loadTeacherWorkspace(), refreshOpenTeacherReport(item.session_id)]);
    const ok = refreshed[0].status === "fulfilled" && refreshed[0].value && refreshed[1].status === "fulfilled";
    toast(ok ? "Đã lưu điểm và cập nhật kết quả." : "Đã lưu điểm. Nhấn Làm mới để cập nhật dữ liệu còn thiếu.");
  } catch (error) {
    teacherFeedback(el.reviewFormFeedback, error.message);
  } finally {
    state.reviewSaving = false;
    renderReviewQueue(); renderReviewDetail();
    if (!saved) el.reviewSaveButton.disabled = false;
  }
}

async function acceptAiReview() {
  const item = reviewItem();
  if (!item || state.reviewSaving || !item.strong_review_ready || item.can_accept_ai === false) return;
  state.reviewScore.value = String(item.review_ai_score);
  state.reviewFeedback.value = "Giảng viên xác nhận sử dụng kết quả chấm của AI.";
  await submitTeacherReview(new Event("submit", { cancelable: true }), "accept_ai");
}


function renderPracticeHistory() {
  el.practiceHistoryCount.textContent = `${state.practiceHistory.length} buổi`;
  el.practiceHistoryRows.innerHTML = state.practiceHistory.length
    ? state.practiceHistory.map((session) => {
      const completed = session.status === "completed";
      const score = session.average_score == null ? "—" : `${Math.round(session.average_score)}/100`;
      return `<tr>
        <td><strong>${formatDate(session.finished_at || session.created_at)}</strong></td>
        <td><span class="history-subject"><strong>${escapeHtml(session.subject || "Tất cả lĩnh vực")}</strong><small>${languageName(session.language)}</small></span></td>
        <td>${session.answered_count}/${session.requested_count} câu</td>
        <td><strong>${score}</strong></td>
        <td><span class="status-badge ${completed ? "" : "waiting"}">${completed ? "Hoàn tất" : "Chưa hoàn tất"}</span></td>
        <td><div class="table-actions"><button class="button secondary compact" data-practice-session="${escapeHtml(session.session_id)}" ${session.can_view_report ? "" : "disabled"}>${session.can_view_report ? "Xem báo cáo" : "Chưa có kết quả"}</button><button class="button secondary danger compact" data-delete-practice-session="${escapeHtml(session.session_id)}">Xóa</button></div></td>
      </tr>`;
    }).join("")
    : '<tr><td colspan="6"><div class="empty-state">Bạn chưa có buổi luyện tập nào.</div></td></tr>';
}

async function loadPracticeHistory() {
  el.practiceHistoryRows.setAttribute("aria-busy", "true");
  try {
    const result = await api("/api/candidate/practice-history");
    state.practiceHistory = result.sessions;
    renderPracticeHistory();
  } finally {
    el.practiceHistoryRows.removeAttribute("aria-busy");
  }
}

async function refreshPracticeHistory() {
  const originalLabel = el.refreshPracticeHistoryButton.textContent;
  el.refreshPracticeHistoryButton.disabled = true;
  el.refreshPracticeHistoryButton.textContent = "Đang tải...";
  try {
    await loadPracticeHistory();
    toast("Đã làm mới lịch sử luyện tập.");
  } catch (error) {
    toast(`Không thể làm mới: ${error.message}`, true);
  } finally {
    el.refreshPracticeHistoryButton.disabled = false;
    el.refreshPracticeHistoryButton.textContent = originalLabel;
  }
}

async function deleteCandidatePracticeHistory(sessionId) {
  if (!window.confirm("Xóa vĩnh viễn buổi luyện tập này và toàn bộ câu trả lời?")) return;
  try {
    await api(`/api/candidate/practice-history/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    await loadPracticeHistory();
    toast("Đã xóa lịch sử luyện tập.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function showPracticeHistoryReport(sessionId) {
  try {
    const report = await api(`/api/interviews/${sessionId}/report`);
    state.reportOrigin = "history";
    renderReport(report);
    openReportDialog();
  } catch (error) {
    toast(error.message, true);
  }
}

async function showTeacherResult(sessionId) {
  const sequence = ++state.teacherReportSequence;
  el.reviewAudio.pause?.();
  try {
    const report = await api(`/api/teacher/results/${encodeURIComponent(sessionId)}`);
    if (sequence !== state.teacherReportSequence) return;
    state.currentTeacherReport = report;
    state.currentTeacherReportSessionId = sessionId;
    state.reviewReportCache.set(sessionId, report);
    state.reportOrigin = "teacher";
    renderReport(report);
    openReportDialog();
  } catch (error) { if (sequence === state.teacherReportSequence) toast(error.message, true); }
}

async function startPractice(event) {
  event.preventDefault();
  el.startPracticeButton.disabled = true;
  try {
    const difficulty = document.querySelector('input[name="practiceDifficulty"]:checked').value;
    const result = await api("/api/interviews/start", jsonOptions("POST", {
      language: el.practiceLanguage.value,
      subject: el.practiceSubject.value || null,
      question_count: Number(el.practiceQuestionCount.value),
      starting_difficulty: difficulty,
    }));
    beginSession(result);
  } catch (error) {
    toast(error.message, true);
  } finally {
    el.startPracticeButton.disabled = false;
  }
}

function renderCandidateExam(exam) {
  state.candidateExam = exam;
  el.previewSubject.textContent = exam.subject;
  el.previewLanguage.textContent = languageName(exam.language);
  el.previewQuestionCount.textContent = `${exam.question_count} câu`;
  el.previewAnswerMode.textContent = answerModeName(exam.answer_mode);
  el.previewTime.textContent = `${formatDate(exam.starts_at)} → ${formatDate(exam.ends_at)}`;
  const [statusLabel] = availabilityInfo(exam);
  const available = exam.availability === "available";
  el.previewAvailability.textContent = available ? "Bài Interview đang mở. Bạn có thể bắt đầu." : statusLabel;
  el.previewAvailability.classList.toggle("error", !available);
  el.startRealButton.disabled = !available;
  el.examPreview.classList.remove("hidden");
}

async function checkExam(event) {
  event.preventDefault();
  el.checkExamButton.disabled = true;
  try {
    const result = await api(`/api/candidate/exams/${encodeURIComponent(el.candidateExamCode.value.trim())}`);
    renderCandidateExam(result.exam);
  } catch (error) {
    state.candidateExam = null;
    el.examPreview.classList.add("hidden");
    toast(error.message, true);
  } finally {
    el.checkExamButton.disabled = false;
  }
}

async function startReal() {
  if (!state.candidateExam) return;
  el.startRealButton.disabled = true;
  try {
    const result = await api(`/api/candidate/exams/${encodeURIComponent(state.candidateExam.exam_code)}/start`, { method: "POST" });
    beginSession(result);
    if (result.resumed) toast("Đã mở lại phiên Interview đang làm.");
  } catch (error) {
    toast(error.message, true);
  } finally {
    el.startRealButton.disabled = false;
  }
}

function sttReady() {
  return Boolean(state.health?.speech_to_text?.ready);
}

function sttAvailable() {
  return Boolean(state.health?.speech_to_text?.installed);
}

function setVoiceStage(stage) {
  const stages = ["record", "transcribe", "verify"];
  const activeIndex = stages.indexOf(stage);
  el.voicePipeline.querySelectorAll("[data-voice-stage]").forEach((item, index) => {
    item.classList.toggle("active", index === activeIndex);
    item.classList.toggle("complete", activeIndex >= 0 && index < activeIndex);
  });
  el.voicePipeline.classList.toggle("has-error", stage === "error");
}

function savedMicrophoneId() {
  try {
    return localStorage.getItem("ai-interview-microphone") || "";
  } catch (_) {
    return "";
  }
}

function rememberMicrophone(id) {
  try { localStorage.setItem("ai-interview-microphone", id); } catch (_) { /* Storage is optional. */ }
}

function physicalMicrophones(devices) {
  const seen = new Set();
  return devices.filter((device) => {
    if (device.kind !== "audioinput" || !device.deviceId || ["default", "communications"].includes(device.deviceId) || seen.has(device.deviceId)) return false;
    seen.add(device.deviceId);
    return true;
  });
}

async function refreshMicrophones() {
  if (!navigator.mediaDevices?.enumerateDevices) return;
  const sequence = ++state.microphoneRefreshSequence;
  try {
    const allDevices = await navigator.mediaDevices.enumerateDevices();
    if (sequence !== state.microphoneRefreshSequence) return;
    const devices = physicalMicrophones(allDevices);
    if (!state.microphoneSelectionInitialized) {
      state.selectedMicrophoneId = savedMicrophoneId();
      state.microphoneSelectionInitialized = true;
    }
    let selected = state.selectedMicrophoneId;
    // Migrate old Default/Communications entries to the real endpoint only once.
    if (["default", "communications"].includes(selected)) {
      const alias = allDevices.find((device) => device.kind === "audioinput" && device.deviceId === selected);
      const real = devices.find((device) => alias?.groupId && device.groupId === alias.groupId)
        || (devices.length === 1 ? devices[0] : null);
      if (real) selected = real.deviceId;
    }
    if (!selected && devices.length) {
      const defaultAlias = allDevices.find((device) => device.kind === "audioinput" && device.deviceId === "default");
      selected = (devices.find((device) => defaultAlias?.groupId && device.groupId === defaultAlias.groupId) || devices[0]).deviceId;
    }
    const chosen = devices.find((device) => device.deviceId === selected);
    state.microphoneDevices = devices;
    state.selectedMicrophoneId = selected;
    if (chosen) {
      state.microphoneLabel = chosen.label || "Microphone đã chọn";
      rememberMicrophone(selected);
    }
    const permissionHidden = allDevices.some((device) => device.kind === "audioinput" && !device.deviceId);
    const options = devices.map((device, index) => `<option value="${escapeHtml(device.deviceId)}">${escapeHtml(device.label || `Microphone ${index + 1}`)}</option>`);
    if (selected && !chosen) {
      options.unshift(`<option value="${escapeHtml(selected)}">${escapeHtml(state.microphoneLabel || "Microphone đã chọn")} · ${permissionHidden ? "Cần cấp quyền" : "Không khả dụng"}</option>`);
      // Do not silently replace an unplugged mic with another one.
      if (!permissionHidden && state.sessionMicCheck?.ready && !state.micTestController) {
        resetMicTestPanel();
        el.micTestInstruction.textContent = "Microphone đã chọn không còn khả dụng. Hãy chọn thiết bị và kiểm tra lại.";
      }
    }
    if (!options.length) options.push('<option value="">Microphone hệ thống · nhấn Kiểm tra để cấp quyền</option>');
    el.microphoneSelect.innerHTML = options.join("");
    el.microphoneSelect.value = selected;
  } catch (_) {
    // Keep the previous selection and list when enumeration temporarily fails.
  }
}

function selectMicrophone() {
  const selected = el.microphoneSelect.value;
  if (selected === state.selectedMicrophoneId) return;
  state.selectedMicrophoneId = selected;
  state.microphoneSelectionInitialized = true;
  state.microphoneLabel = state.microphoneDevices.find((device) => device.deviceId === selected)?.label || "Microphone đã chọn";
  rememberMicrophone(selected);
  resetMicTestPanel();
}

async function pinTestMicrophone(stream, signal) {
  const track = stream.getAudioTracks()[0];
  const actualId = track?.getSettings?.().deviceId || "";
  const selected = state.selectedMicrophoneId;
  if (actualId && !["default", "communications"].includes(actualId)) {
    if (selected && !["default", "communications"].includes(selected) && actualId !== selected) {
      throw new Error("Thiết bị ghi âm không khớp microphone đã chọn. Hãy chọn mic và kiểm tra lại.");
    }
    // Resolve a system-default capture before checking, then pin this physical ID.
    state.selectedMicrophoneId = actualId;
    state.microphoneSelectionInitialized = true;
    rememberMicrophone(actualId);
  }
  await refreshMicrophones();
  if (signal.aborted) throw new DOMException("Đã hủy kiểm tra", "AbortError");
}

function beginSession(session) {
  state.session = session;
  resetMicTestPanel();
  state.currentQuestion = session.question;
  state.pendingResult = null;
  state.completed = false;
  setNavigationLocked(true);
  el.finishPracticeButton.classList.toggle("hidden", session.interview_mode === "real");
  showView("interviewView");
  renderQuestion();
}

function renderQuestion() {
  const question = state.currentQuestion;
  el.answerRecordingQuality.className = "microphone-result hidden";
  el.answerRecordingQuality.replaceChildren();
  const answered = Number(state.session.answered_count || 0);
  const requested = Number(state.session.requested_count);
  el.sessionMode.textContent = state.session.interview_mode === "real" ? `Interview · ${state.session.exam?.exam_code || ""}` : "Luyện tập";
  el.sessionCandidate.textContent = state.user.full_name;
  el.sessionProgress.textContent = `Câu ${Math.min(answered + 1, requested)}/${requested}`;
  el.progressBar.style.width = `${Math.round((answered / requested) * 100)}%`;
  el.questionDifficulty.textContent = difficultyName(question.difficulty);
  const sessionLanguage = state.session.language || question.language || "vi";
  el.questionMeta.textContent = `${languageName(sessionLanguage)} · ${question.subject} · ${question.topic}`;
  el.questionText.textContent = question.question;
  el.answerCard.classList.remove("hidden");
  el.evaluationCard.classList.add("hidden");
  el.answerText.value = "";
  setVoiceStage("idle");
  state.currentTranscriptionId = null;
  el.charCount.textContent = "0 ký tự";
  el.submitAnswerButton.disabled = true;

  el.answerText.readOnly = true;
  el.answerText.placeholder = "Bản chuyển giọng nói sẽ xuất hiện tại đây...";
  el.answerModeHint.textContent = "Chỉ trả lời bằng ghi âm";
  el.recordButton.classList.remove("hidden");
  el.recordButton.textContent = "● Ghi âm";
  el.microphoneSelect.disabled = false;
  refreshMicrophones();
  el.recordButton.disabled = !sttAvailable() || !state.sessionMicCheck?.ready;
  const runtimeLabel = state.health?.speech_to_text?.label || "Tự động";
  if (sttReady()) {
    el.sttStatus.textContent = `${state.health.speech_to_text.model} · ${runtimeLabel} · ${languageName(sessionLanguage)}`;
    el.sttStatus.className = "status-pill";
    el.recordingStatus.textContent = state.sessionMicCheck?.ready ? "Bấm Ghi âm để trả lời" : "Kiểm tra microphone ở cột bên trái trước khi trả lời";
  } else if (sttAvailable()) {
    el.sttStatus.textContent = `${state.health.speech_to_text.model} · ${runtimeLabel} · khởi tạo khi dùng`;
    el.sttStatus.className = "status-pill warn";
    el.recordingStatus.textContent = "Lần đầu cần Internet và có thể mất vài phút";
  } else {
    el.sttStatus.textContent = "Thiếu thư viện Voice/STT";
    el.sttStatus.className = "status-pill warn";
    el.recordingStatus.textContent = "Cài lại requirements.txt để dùng ghi âm";
  }
  setTimeout(() => el.recordButton.focus(), 0);
}

function fillList(list, values, fallback) {
  list.innerHTML = values?.length
    ? values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")
    : `<li>${escapeHtml(fallback)}</li>`;
}

const ASSESSMENT_STATUS = {
  met: { label: "Đạt", className: "met" },
  partial: { label: "Một phần", className: "partial" },
  contradicted: { label: "Mâu thuẫn", className: "contradicted" },
  missing: { label: "Thiếu", className: "missing" },
};

function assessmentGroups(evaluation) {
  const assessments = Array.isArray(evaluation.point_assessments) ? evaluation.point_assessments : [];
  if (!assessments.length) {
    return {
      met: evaluation.matched_points || [],
      partial: [],
      contradicted: [],
      missing: evaluation.missing_points || [],
    };
  }
  return Object.fromEntries(
    Object.keys(ASSESSMENT_STATUS).map((status) => [
      status,
      assessments.filter((item) => item.status === status).map((item) => item.point),
    ]),
  );
}

function pointAssessmentHtml(assessments) {
  if (!Array.isArray(assessments) || !assessments.length) return "";
  return assessments.map((item) => {
    const status = ASSESSMENT_STATUS[item.status] || ASSESSMENT_STATUS.missing;
    const evidence = item.evidence_quote
      ? `<q>${escapeHtml(item.evidence_quote)}</q>`
      : "<span class=\"no-evidence\">Không tìm thấy bằng chứng trong câu trả lời.</span>";
    return `<div class="assessment-row"><span class="assessment-status ${status.className}">${status.label}</span><div><strong>${escapeHtml(item.point)}</strong><p>${escapeHtml(item.reason || "Chưa có giải thích.")}</p>${evidence}</div></div>`;
  }).join("");
}

function renderPointAssessments(assessments) {
  el.pointAssessmentList.innerHTML = pointAssessmentHtml(assessments);
  el.pointAssessmentList.classList.toggle("hidden", !assessments?.length);
}

function renderEvaluation(evaluation, completed) {
  el.evaluationScore.textContent = Math.round(evaluation.score);
  el.evaluationVerdict.textContent = evaluation.verdict;
  el.evaluationFeedback.textContent = evaluation.feedback;
  el.evaluationEngine.textContent = `${evaluation.evaluator} · độ tin cậy ${Math.round(evaluation.confidence * 100)}%`;
  const groups = assessmentGroups(evaluation);
  fillList(el.matchedPoints, groups.met, "Chưa có tiêu chí đạt hoàn toàn");
  fillList(el.partialPoints, groups.partial, "Không có");
  fillList(el.contradictedPoints, groups.contradicted, "Không có");
  fillList(el.missingPoints, groups.missing, "Không có tiêu chí bị thiếu");
  renderPointAssessments(evaluation.point_assessments);
  el.evaluationReview.classList.toggle("hidden", !evaluation.review_required);
  el.evaluationReview.textContent = evaluation.review_required
    ? "Kết quả này có độ tin cậy thấp hoặc chứa nội dung mâu thuẫn. Giáo viên cần xem lại bằng chứng trước khi dùng điểm."
    : "";
  el.nextQuestionButton.textContent = completed ? "Xem báo cáo →" : "Câu tiếp theo →";
  el.answerCard.classList.add("hidden");
  el.evaluationCard.classList.remove("hidden");
}

async function submitCurrentAnswer() {
  const answer = el.answerText.value.trim();
  if (!answer || !state.currentTranscriptionId) {
    toast("Vui lòng ghi âm câu trả lời trước khi gửi.", true);
    return;
  }
  el.submitAnswerButton.disabled = true;
  el.submitAnswerButton.textContent = "Đang đánh giá...";
  try {
    const result = await api(
      `/api/interviews/${state.session.session_id}/answer`,
      jsonOptions("POST", {
        answer,
        transcription_id: state.currentTranscriptionId,
      }),
    );
    state.session.answered_count = result.answered_count;
    state.pendingResult = result;
    el.progressBar.style.width = `${Math.round((result.answered_count / result.requested_count) * 100)}%`;
    if (state.session.interview_mode === "practice") {
      renderEvaluation(result.evaluation, result.completed);
    } else if (result.completed) {
      completeRealInterview();
    } else {
      state.currentQuestion = result.next_question;
      toast("Đã lưu câu trả lời.");
      renderQuestion();
    }
  } catch (error) {
    toast(error.message, true);
    el.submitAnswerButton.disabled = false;
  } finally {
    el.submitAnswerButton.textContent = "Gửi câu trả lời";
  }
}

async function nextPracticeQuestion() {
  if (!state.pendingResult) return;
  if (state.pendingResult.completed) {
    await loadPracticeReport();
    return;
  }
  state.currentQuestion = state.pendingResult.next_question;
  state.pendingResult = null;
  renderQuestion();
}

async function finishPractice() {
  if (!state.session || !window.confirm("Kết thúc buổi luyện tập và tạo báo cáo với các câu đã trả lời?")) return;
  try {
    await api(`/api/interviews/${state.session.session_id}/finish`, { method: "POST" });
    await loadPracticeReport();
  } catch (error) {
    toast(error.message, true);
  }
}

function completeRealInterview() {
  state.completed = true;
  state.session = null;
  state.currentQuestion = null;
  setNavigationLocked(false);
  showView("realCompleteView");
}

async function loadPracticeReport() {
  try {
    const report = await api(`/api/interviews/${state.session.session_id}/report`);
    state.reportOrigin = "practice";
    state.completed = true;
    setNavigationLocked(false);
    renderReport(report);
    openReportDialog();
  } catch (error) {
    toast(error.message, true);
  }
}

function reportNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString("vi-VN", { maximumFractionDigits: 2 }) : "—";
}

function dismissReportDialog() {
  if (!el.reportDialog) return;
  if (el.reportDialog.open) el.reportDialog.close();
  document.body.classList.remove("report-modal-open");
  el.reportDialog.querySelectorAll("audio").forEach((audio) => audio.pause());
}

function openReportDialog() {
  state.micTestController?.abort();
  el.reportDialogBody.scrollTop = 0;
  document.body.classList.add("report-modal-open");
  if (!el.reportDialog.open) el.reportDialog.showModal();
}

function renderReport(report) {
  const session = report.session || {};
  const summary = report.summary || {};
  const answers = Array.isArray(report.answers) ? report.answers : [];
  const average = Number(summary.average_score || 0);
  const scoredAnswerCount = Number(summary.scored_answer_count ?? answers.length);
  const total = answers.reduce((sum, item) => {
    const evaluation = item.evaluation || {};
    const score = Number(session.interview_mode === "real" ? evaluation.final_score : evaluation.final_score ?? evaluation.score);
    return sum + (Number.isFinite(score) ? score : 0);
  }, 0);
  const completed = session.answered_count ?? answers.length;
  const requested = session.requested_count ?? answers.length;
  el.reportTitle.textContent = session.subject || session.title || "Kết quả phỏng vấn kiến thức";
  el.reportCandidate.textContent = session.candidate_name || "Sinh viên";
  el.reportMeta.textContent = `${languageName(session.language || "vi")} · ${completed}/${requested} câu`;
  el.reportTotalScore.textContent = scoredAnswerCount ? `${reportNumber(total)}/${scoredAnswerCount * 100}` : "—";
  el.reportPercentage.textContent = scoredAnswerCount ? `${reportNumber(average)}%` : "—";
  el.reportScore.textContent = scoredAnswerCount ? reportNumber(average) : "—";
  el.reportVerdict.textContent = scoredAnswerCount ? summary.overall_verdict || "Đã chấm" : "Chờ giảng viên xác nhận";
  el.reportSummaryText.textContent = answers.length
    ? `Báo cáo tổng hợp ${answers.length} câu đã trả lời. Xem các điểm mạnh, nội dung cần cải thiện và nhận xét từng câu bên dưới.`
    : "Phiên kết thúc trước khi có câu trả lời để chấm điểm.";
  fillList(el.strengthList, summary.strengths, "Chưa đủ dữ liệu");
  fillList(el.gapList, summary.gaps, "Chưa đủ dữ liệu");
  const competencies = Array.isArray(summary.competencies) ? summary.competencies : [];
  el.competencyRows.innerHTML = competencies.length
    ? competencies.map((item) => `<div class="competency-row"><strong>${escapeHtml(item.name)}</strong><div class="competency-bar"><i style="width:${Math.max(0, Math.min(100, Number(item.average_score) || 0))}%"></i></div><span>${reportNumber(item.average_score)}/100 · ${escapeHtml(item.question_count)} câu</span></div>`).join("")
    : "<p>Chưa có câu trả lời để tổng hợp.</p>";
  el.answerDetails.innerHTML = answers.length
    ? answers.map((item) => {
      const evaluation = item.evaluation || {};
      const proposedScore = evaluation.review_ai_score ?? evaluation.ai_score ?? evaluation.score ?? 0;
      const hasFinalScore = evaluation.final_score != null;
      const score = hasFinalScore ? evaluation.final_score : proposedScore;
      const review = evaluation.review_required
        ? '<div class="review-notice">Cần giáo viên xem lại kết quả và bằng chứng của câu này.</div>' : "";
      const assessments = pointAssessmentHtml(evaluation.point_assessments);
      const voice = state.reportOrigin === "teacher" && item.voice?.audio_available
        ? `<div class="report-voice"><h4>Voice gốc</h4><audio controls preload="none" src="/api/teacher/transcriptions/${encodeURIComponent(item.voice.transcription_id)}/audio">Trình duyệt không phát được voice.</audio><div class="transcript-compare"><div><span>STT gốc</span><p>${escapeHtml(item.voice.raw_transcript || "—")}</p></div><div><span>Bản xác minh</span><p>${escapeHtml(item.voice.verified_transcript || item.answer)}</p></div></div></div>` : "";
      const scoreAudit = `<div class="score-audit"><div><span>Điểm AI đề xuất</span><strong>${reportNumber(proposedScore)}</strong></div><div><span>Điểm cuối</span><strong>${hasFinalScore ? reportNumber(evaluation.final_score) : "Chờ duyệt"}</strong></div>${evaluation.teacher_score == null ? "" : `<div><span>Giảng viên</span><strong>${reportNumber(evaluation.teacher_score)}</strong></div>`}</div>`;
      const teacherFeedback = evaluation.teacher_feedback
        ? `<div class="teacher-feedback"><strong>Nhận xét của giảng viên</strong><p>${escapeHtml(evaluation.teacher_feedback)}</p></div>` : "";
      return `<article class="report-answer-card">
        <h3>Câu ${escapeHtml(item.sequence_number)}: ${escapeHtml(item.question?.question || "")}</h3>
        <p class="report-answer-score">${hasFinalScore || session.interview_mode !== "real" ? `${reportNumber(score)}/100 điểm` : `${reportNumber(score)}/100 điểm AI đề xuất · Chờ giảng viên`}${evaluation.verdict ? ` · ${escapeHtml(evaluation.verdict)}` : ""}</p>
        ${review}
        ${state.reportOrigin === "teacher" && item.answer_id != null ? `<button type="button" class="button secondary compact report-review-button" data-report-review-session="${escapeHtml(state.currentTeacherReportSessionId)}" data-report-review-answer="${escapeHtml(item.answer_id)}">Chấm lại câu này</button>` : ""}
        <p class="report-answer-text"><strong>Trả lời:</strong> ${escapeHtml(item.answer || "Chưa có nội dung")}</p>
        <p class="report-answer-feedback"><strong>Nhận xét:</strong> ${escapeHtml(evaluation.feedback || "Chưa có nhận xét")}</p>
        ${teacherFeedback}
        <p class="report-reference"><strong>Đáp án tham khảo:</strong> ${escapeHtml(item.reference_answer || "Chưa có đáp án tham khảo")}</p>
        <details class="report-answer-extra"><summary>Chi tiết chấm điểm${state.reportOrigin === "teacher" && item.voice?.audio_available ? " và ghi âm" : ""}</summary>
          ${scoreAudit}${voice}
          ${assessments ? `<h4>Đối chiếu rubric</h4><div class="assessment-list">${assessments}</div>` : ""}
          <p class="report-engine">Bộ chấm: ${escapeHtml(evaluation.evaluator || "—")} · độ tin cậy ${reportNumber(Number(evaluation.confidence || 0) * 100)}% · rubric ${escapeHtml(evaluation.rubric_version || "mặc định")}</p>
        </details>
      </article>`;
    }).join("")
    : '<div class="empty-state">Chưa có câu trả lời.</div>';
}

function reportBack() {
  dismissReportDialog();
  state.session = null;
  state.currentQuestion = null;
  state.pendingResult = null;
  state.completed = false;
  if (state.reportOrigin === "teacher") {
    showView("teacherResultsView");
  } else if (state.reportOrigin === "history") {
    showView("practiceHistoryView");
    loadPracticeHistory().catch((error) => toast(error.message, true));
  } else {
    showView("practiceSetupView");
  }
}

function micTestSentence() {
  const name = state.user?.full_name?.trim() || "[tên của bạn]";
  const studentId = state.user?.student_id?.trim() || "[mã sinh viên của bạn]";
  return `Tôi là ${name}, có mã sinh viên là ${studentId}.`;
}

function resetMicTestPanel() {
  state.sessionMicCheck = null;
  state.ambientNoiseDbfs = null;
  el.recordButton.disabled = true;
  el.micCheckButtonLabel.textContent = "Kiểm tra";
  el.micTestSentence.textContent = `“${micTestSentence()}”`;
  el.micTestBadge.textContent = "Chưa kiểm tra";
  el.micTestPanel.dataset.stage = "idle";
  el.micTestInstruction.textContent = "";
  el.micLiveMeter.value = 0;
  el.micNoiseMeter.value = 0;
  el.micLiveLabel.textContent = "Chưa đo";
  el.micNoiseLabel.textContent = "Chưa đo";
  delete el.micNoiseMeter.dataset.level;
  delete el.micLiveMeter.dataset.level;
  el.cancelMicTestButton.classList.add("hidden");
  el.finishMicTestButton.classList.add("hidden");
  el.microphoneCheckResult.className = "microphone-result hidden";
  el.microphoneCheckResult.replaceChildren();
}

function showMicTestStage(stage, message) {
  el.micTestPanel.dataset.stage = stage;
  if (el.micTestInstruction.textContent !== message) el.micTestInstruction.textContent = message;
  const labels = { permission: "Cấp quyền", noise: "Đo tiếng nền", voice: "Ghi thử", processing: "Đang xử lý", done: "Sẵn sàng", error: "Thử lại" };
  el.micTestBadge.textContent = labels[stage] || "Chưa kiểm tra";
  el.cancelMicTestButton.classList.toggle("hidden", !["permission", "noise", "voice", "processing"].includes(stage));
}

function showNoiseLevel(dbfs, label) {
  if (!Number.isFinite(dbfs)) return;
  el.micNoiseMeter.value = Math.max(0, Math.min(100, (dbfs + 80) / 80 * 100));
  el.micNoiseLabel.textContent = label || (dbfs <= -42 ? "Yên tĩnh" : dbfs <= -32 ? "Trung bình" : dbfs <= -20 ? "Ồn" : "Rất ồn");
  el.micNoiseMeter.dataset.level = dbfs <= -42 ? "quiet" : dbfs <= -32 ? "moderate" : "noisy";
}

function startMicLevelMeter(context, stream) {
  const source = context.createMediaStreamSource(stream);
  const analyser = context.createAnalyser();
  analyser.fftSize = 2048;
  source.connect(analyser);
  const samples = new Float32Array(analyser.fftSize);
  let frame = 0;
  function update() {
    analyser.getFloatTimeDomainData(samples);
    let squares = 0;
    let peak = 0;
    for (const sample of samples) {
      squares += sample * sample;
      peak = Math.max(peak, Math.abs(sample));
    }
    const dbfs = 20 * Math.log10(Math.max(0.00001, Math.sqrt(squares / samples.length)));
    el.micLiveMeter.value = Math.max(0, Math.min(100, (dbfs + 60) / 60 * 100));
    el.micLiveLabel.textContent = peak >= 0.98 ? "Vỡ tiếng" : dbfs < -42 ? "Nhỏ" : dbfs > -6 ? "Lớn" : "Đang thu";
    el.micLiveMeter.dataset.level = peak >= 0.98 ? "noisy" : dbfs > -6 ? "moderate" : "quiet";
    frame = requestAnimationFrame(update);
  }
  update();
  return () => {
    cancelAnimationFrame(frame);
    source.disconnect();
    analyser.disconnect();
  };
}

function renderMicrophoneResult(result, mode = "microphone") {
  const isRecording = mode === "recording";
  const rawScore = Number(isRecording ? result.recording_quality_percent : result.microphone_score_percent);
  const score = Math.max(0, Math.min(100, Number.isFinite(rawScore) ? rawScore : 0));
  const status = isRecording ? (score >= 80 ? "good" : score >= 60 ? "acceptable" : "poor") : result.status;
  const safeStatus = ["good", "acceptable", "poor"].includes(status) ? status : "acceptable";
  const title = isRecording ? "Chất lượng bản ghi" : result.status_label || "Kết quả kiểm tra microphone";
  const noise = result.noise || {};
  const noiseDbfs = noise.dbfs == null ? NaN : Number(noise.dbfs);
  const recommendations = Array.isArray(result.recommendations) ? result.recommendations : [];
  const resultContainer = isRecording ? el.answerRecordingQuality : el.microphoneCheckResult;
  resultContainer.className = `microphone-result ${safeStatus}`;
  if (!isRecording) {
    const label = state.sessionMicCheck?.ready ? "Đã kiểm tra cho cả bài" : "Cần điều chỉnh";
    resultContainer.innerHTML = `
      <div class="mic-result-summary"><span>${escapeHtml(label)}</span><strong>${Math.round(score)}<small>/100</small></strong></div>
      <progress max="100" value="${score}" aria-label="Điểm chất lượng âm thanh">${score}</progress>
      ${!state.sessionMicCheck?.ready && recommendations.length ? `<p class="mic-action-hint">${escapeHtml(recommendations[0])}</p>` : ""}
      <details class="mic-technical"><summary>Chi tiết</summary>
        <p>${escapeHtml(title)} · Tiếng nền: ${Number.isFinite(noiseDbfs) ? `${noiseDbfs.toFixed(1)} dBFS` : "Chưa đo"}.</p>
        ${recommendations.length ? `<ul class="mic-recommendations">${recommendations.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}
        <p>Điểm chất lượng âm thanh, không phải điểm bài thi. Kiểm tra lại khi đổi mic hoặc môi trường.</p>
      </details>`;
    showNoiseLevel(noiseDbfs, noise.label);
    // The live bar is only meaningful while the microphone is actually open.
    el.micLiveMeter.value = 0;
    el.micLiveLabel.textContent = "Đã dừng";
    delete el.micLiveMeter.dataset.level;
    return;
  }
  resultContainer.innerHTML = `
    <div class="microphone-result-head"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(noise.label || "Chưa đo tiếng nền")}</span></div>
    <div class="mic-quality-row"><strong>${Math.round(score)}<small>/100</small></strong><div><span>Điểm chất lượng âm thanh</span><progress max="100" value="${score}" aria-label="Điểm chất lượng âm thanh">${score}</progress></div></div>
    ${recommendations.length ? `<ul class="mic-recommendations">${recommendations.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : '<p>Âm thanh đã được kiểm tra. Bạn có thể tiếp tục ghi câu trả lời.</p>'}
    <details class="mic-technical"><summary>Chi tiết âm thanh</summary><p>Tiếng nền: ${Number.isFinite(noiseDbfs) ? `${noiseDbfs.toFixed(1)} dBFS` : "Chưa đo"}. Điểm này phản ánh chất lượng âm thanh, không phải độ chính xác nhận dạng.</p></details>`;
}

async function checkMicrophone() {
  if (state.micTestController || state.recorder?.state === "recording") return;
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined" || !AudioContextClass) {
    toast("Trình duyệt chưa hỗ trợ kiểm tra microphone. Hãy dùng Chrome hoặc Edge.", true);
    return;
  }
  const previousCheck = state.sessionMicCheck;
  const checkedSession = state.session;
  const controller = new AbortController();
  state.micTestController = controller;
  const { signal } = controller;
  const controls = [el.checkMicrophoneButton, el.recordButton, el.microphoneSelect, el.submitAnswerButton, el.finishPracticeButton];
  const disabledStates = controls.map((control) => control.disabled);
  controls.forEach((control) => { control.disabled = true; });
  resetMicTestPanel();
  showMicTestStage("permission", "Cho phép truy cập mic.");
  let context = null;
  let stream = null;
  let recorder = null;
  let stopMeter = null;
  let countdownTimer = null;
  const throwIfCancelled = () => { if (signal.aborted) throw new DOMException("Đã hủy kiểm tra", "AbortError"); };
  const cancelCapture = () => {
    if (recorder?.state === "recording") recorder.stop();
    stream?.getTracks().forEach((track) => track.stop());
    stopMeter?.();
    stopMeter = null;
    if (context && context.state !== "closed") context.close().catch(() => {});
  };
  signal.addEventListener("abort", cancelCapture, { once: true });
  try {
    context = new AudioContextClass();
    await context.resume();
    throwIfCancelled();
    const constraints = { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true };
    if (state.selectedMicrophoneId) constraints.deviceId = { exact: state.selectedMicrophoneId };
    stream = await new Promise((resolve, reject) => {
      const abortPermission = () => reject(new DOMException("Đã hủy kiểm tra", "AbortError"));
      signal.addEventListener("abort", abortPermission, { once: true });
      navigator.mediaDevices.getUserMedia({ audio: constraints }).then((openedStream) => {
        signal.removeEventListener("abort", abortPermission);
        if (signal.aborted) {
          // A permission prompt may resolve after cancellation; never leave that mic open.
          openedStream.getTracks().forEach((track) => track.stop());
          abortPermission();
        } else resolve(openedStream);
      }, (error) => {
        signal.removeEventListener("abort", abortPermission);
        reject(error);
      });
    });
    throwIfCancelled();
    await pinTestMicrophone(stream, signal);
    throwIfCancelled();
    stopMeter = startMicLevelMeter(context, stream);
    showMicTestStage("noise", "Giữ im lặng · 2 giây");
    const ambient = await measureAmbientNoise(stream, 2000);
    throwIfCancelled();
    showNoiseLevel(ambient.dbfs);
    const preferred = typeof MediaRecorder.isTypeSupported === "function"
      ? ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((type) => MediaRecorder.isTypeSupported(type)) : null;
    recorder = preferred ? new MediaRecorder(stream, { mimeType: preferred }) : new MediaRecorder(stream);
    const chunks = [];
    recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
    const stopped = new Promise((resolve, reject) => {
      recorder.onstop = resolve;
      recorder.onerror = (event) => reject(event.error || new Error("Không thu được bản ghi thử."));
    });
    // Attach a rejection handler immediately while awaiting the capture timer.
    stopped.catch(() => {});
    recorder.start(250);
    const startAt = performance.now();
    el.finishMicTestButton.classList.remove("hidden");
    el.finishMicTestButton.disabled = true;
    await new Promise((resolve) => {
      const finish = () => { clearInterval(countdownTimer); countdownTimer = null; resolve(); };
      signal.addEventListener("abort", finish, { once: true });
      el.finishMicTestButton.onclick = finish;
      const tick = () => {
        const elapsed = performance.now() - startAt;
        el.finishMicTestButton.disabled = elapsed < 2000;
        showMicTestStage("voice", `Đọc câu mẫu · ${Math.max(0, Math.ceil((12000 - elapsed) / 1000))} giây`);
        if (elapsed >= 12000) finish();
      };
      countdownTimer = setInterval(tick, 100);
      tick();
    });
    throwIfCancelled();
    if (recorder.state === "recording") recorder.stop();
    await stopped;
    throwIfCancelled();
    cancelCapture();
    el.finishMicTestButton.classList.add("hidden");
    showMicTestStage("processing", "Đang phân tích…");
    const mimeType = recorder.mimeType || "audio/webm";
    const form = new FormData();
    form.append("file", new Blob(chunks, { type: mimeType }), `microphone-check.${mimeType.includes("mp4") ? "m4a" : "webm"}`);
    form.append("session_id", state.session.session_id);
    form.append("ambient_noise_dbfs", String(ambient.dbfs));
    const result = await api("/api/speech/microphone-check", { method: "POST", body: form, signal });
    throwIfCancelled();
    state.sessionMicCheck = { ready: Boolean(result.ready), baselineDbfs: ambient.dbfs, result, deviceId: state.selectedMicrophoneId };
    state.ambientNoiseDbfs = ambient.dbfs;
    el.micCheckButtonLabel.textContent = "Kiểm tra lại";
    renderMicrophoneResult(result);
    showMicTestStage(result.ready ? "done" : "error", "");
    toast(result.ready ? "Microphone sẵn sàng để ghi âm." : "Microphone cần điều chỉnh trước khi ghi.", !result.ready);
  } catch (error) {
    if (!signal.aborted) {
      const message = error.name === "NotAllowedError" ? "Chưa được cấp quyền microphone. Hãy cho phép microphone trên trình duyệt rồi thử lại."
        : error.name === "NotFoundError" ? "Không tìm thấy microphone. Hãy kiểm tra thiết bị đầu vào."
        : error.name === "OverconstrainedError" ? "Microphone đã chọn không còn khả dụng. Hãy chọn đúng thiết bị rồi kiểm tra lại."
        : error.message;
      showMicTestStage("error", "");
      el.microphoneCheckResult.className = "microphone-result poor";
      el.microphoneCheckResult.innerHTML = `<p class="mic-action-hint">${escapeHtml(message)}</p>`;
      toast(message, true);
    } else if (state.micTestController === controller && state.session === checkedSession && state.user) {
      resetMicTestPanel();
      if (previousCheck?.ready && previousCheck.deviceId === state.selectedMicrophoneId) {
        state.sessionMicCheck = previousCheck;
        state.ambientNoiseDbfs = previousCheck.baselineDbfs;
        el.micCheckButtonLabel.textContent = "Kiểm tra lại";
        renderMicrophoneResult(previousCheck.result);
        showMicTestStage("done", "");
      }
    }
  } finally {
    clearInterval(countdownTimer);
    cancelCapture();
    signal.removeEventListener("abort", cancelCapture);
    el.finishMicTestButton.onclick = null;
    el.finishMicTestButton.classList.add("hidden");
    el.cancelMicTestButton.classList.add("hidden");
    if (el.micTestPanel.dataset.stage === "error") {
      el.micLiveMeter.value = 0;
      el.micLiveLabel.textContent = "Đã dừng";
      delete el.micLiveMeter.dataset.level;
    }
    controls.forEach((control, index) => { control.disabled = disabledStates[index]; });
    if (state.micTestController === controller) state.micTestController = null;
    el.recordButton.disabled = !sttAvailable() || !state.sessionMicCheck?.ready;
  }
}

async function toggleRecording() {
  if (state.micTestController) return;
  if (!state.sessionMicCheck?.ready) {
    toast("Hãy kiểm tra microphone và môi trường ở cột bên trái trước khi trả lời.", true);
    return;
  }
  if (state.recorder?.state === "recording") {
    state.recorder.stop();
    return;
  }
  if (!sttAvailable()) {
    toast("Chưa cài thư viện Voice/STT. Hãy chạy lại: python -m pip install -r requirements.txt", true);
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    toast("Trình duyệt chưa hỗ trợ ghi âm. Hãy dùng Chrome hoặc Edge.", true);
    return;
  }
  el.checkMicrophoneButton.disabled = true;
  try {
    state.currentTranscriptionId = null;
    el.answerText.value = "";
    el.answerText.dispatchEvent(new Event("input"));
    el.submitAnswerButton.disabled = true;
    setVoiceStage("record");
    const audioConstraints = {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    };
    if (state.selectedMicrophoneId) {
      audioConstraints.deviceId = { exact: state.selectedMicrophoneId };
    }
    state.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
    const activeDeviceId = state.mediaStream.getAudioTracks()[0]?.getSettings?.().deviceId || "";
    if (activeDeviceId && !["default", "communications"].includes(activeDeviceId) && activeDeviceId !== state.sessionMicCheck.deviceId) {
      resetMicTestPanel();
      throw new Error("Thiết bị ghi âm đã thay đổi. Hãy chọn microphone và kiểm tra lại.");
    }
    el.microphoneSelect.disabled = true;
    // Reuse the baseline measured once for this interview, without another silence test.
    state.ambientNoiseDbfs = state.sessionMicCheck.baselineDbfs;
    const ambient = { dbfs: state.ambientNoiseDbfs };
    const preferred = typeof MediaRecorder.isTypeSupported === "function"
      ? ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((type) => MediaRecorder.isTypeSupported(type))
      : null;
    state.audioChunks = [];
    state.recorder = preferred ? new MediaRecorder(state.mediaStream, { mimeType: preferred }) : new MediaRecorder(state.mediaStream);
    state.recorder.ondataavailable = (event) => { if (event.data.size) state.audioChunks.push(event.data); };
    state.recorder.onstop = transcribeRecording;
    state.recorder.start(250);
    el.checkMicrophoneButton.disabled = true;
    el.recordButton.classList.add("recording");
    el.recordButton.textContent = "■ Dừng ghi";
    el.recordingStatus.textContent = ambient.dbfs > -28
      ? `Đang ghi · có tiếng nền, hệ thống sẽ lọc (${ambient.dbfs.toFixed(1)} dBFS)`
      : ambient.dbfs > -38
        ? `Đang ghi · tiếng nền trung bình (${ambient.dbfs.toFixed(1)} dBFS)`
      : "Đang ghi âm...";
  } catch (error) {
    const message = error?.name === "NotAllowedError"
      ? "Trình duyệt chưa được cấp quyền microphone. Hãy bấm biểu tượng ổ khóa cạnh địa chỉ và chọn Cho phép microphone."
      : error?.name === "NotFoundError"
        ? "Không tìm thấy microphone trên máy."
        : error?.name === "OverconstrainedError"
          ? "Microphone đã chọn không còn khả dụng. Hãy chọn thiết bị và kiểm tra lại."
          : `Không mở được microphone: ${error.message}`;
    toast(message, true);
    setVoiceStage("error");
    state.mediaStream?.getTracks().forEach((track) => track.stop());
    state.mediaStream = null;
    el.microphoneSelect.disabled = false;
    el.checkMicrophoneButton.disabled = false;
  }
}

async function measureAmbientNoise(stream, durationMs) {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return { dbfs: -60, clippingRatio: 0 };
  const context = new AudioContextClass();
  const source = context.createMediaStreamSource(stream);
  const analyser = context.createAnalyser();
  analyser.fftSize = 2048;
  source.connect(analyser);
  const samples = new Float32Array(analyser.fftSize);
  const rmsValues = [];
  let clipped = 0;
  let observed = 0;
  const endAt = performance.now() + durationMs;
  while (performance.now() < endAt) {
    analyser.getFloatTimeDomainData(samples);
    let sumSquares = 0;
    for (const sample of samples) {
      sumSquares += sample * sample;
      if (Math.abs(sample) >= 0.98) clipped += 1;
      observed += 1;
    }
    rmsValues.push(Math.sqrt(sumSquares / samples.length));
    await new Promise((resolve) => setTimeout(resolve, 80));
  }
  source.disconnect();
  await context.close();
  const averageRms = rmsValues.reduce((sum, value) => sum + value, 0) / Math.max(1, rmsValues.length);
  return {
    dbfs: Math.max(-100, 20 * Math.log10(Math.max(averageRms, 0.00001))),
    clippingRatio: clipped / Math.max(1, observed),
  };
}

async function transcribeRecording() {
  state.mediaStream?.getTracks().forEach((track) => track.stop());
  state.mediaStream = null;
  el.microphoneSelect.disabled = true;
  el.checkMicrophoneButton.disabled = true;
  el.recordButton.classList.remove("recording");
  el.recordButton.textContent = "● Ghi âm";
  el.recordButton.disabled = true;
  setVoiceStage("transcribe");
  el.recordingStatus.textContent = sttReady()
    ? "Đang chuyển thành văn bản..."
    : "Đang tải/khởi tạo model và chuyển thành văn bản...";
  try {
    const recorder = state.recorder;
    const chunks = [...state.audioChunks];
    if (!recorder || !chunks.length) throw new Error("Không nhận được dữ liệu ghi âm. Hãy thử ghi lâu hơn.");
    const mimeType = recorder.mimeType || "audio/webm";
    const extension = mimeType.includes("mp4") ? "m4a" : "webm";
    const form = new FormData();
    form.append("file", new Blob(chunks, { type: mimeType }), `answer.${extension}`);
    form.append("language", state.session?.language || state.currentQuestion?.language || "vi");
    form.append("session_id", state.session.session_id);
    if (Number.isFinite(state.ambientNoiseDbfs)) {
      form.append("ambient_noise_dbfs", String(state.ambientNoiseDbfs));
    }
    const result = await api("/api/speech/transcribe", { method: "POST", body: form });
    state.health.speech_to_text.ready = true;
    state.health.speech_to_text.initialization_required = false;
    state.currentTranscriptionId = result.transcription_id || null;
    el.answerText.value = result.text;
    el.answerText.dispatchEvent(new Event("input"));
    el.submitAnswerButton.disabled = false;
    const confidence = Math.round(Number(result.metrics?.confidence || 0) * 100);
    const quality = Math.round(Number(result.metrics?.quality_score || 0) * 100);
    const correction = result.correction_applied ? " · đã sửa lỗi ASR an toàn" : "";
    const warning = result.quality_warnings?.length ? " · đã xử lý vùng chưa chắc chắn" : "";
    el.recordingStatus.textContent = `Đã xác minh · tin cậy ${confidence}% · chất lượng ${quality}%${correction}${warning}`;
    if (result.recording_report) renderMicrophoneResult(result.recording_report, "recording");
    el.recordButton.textContent = "● Ghi âm lại";
    setVoiceStage("verify");
  } catch (error) {
    el.recordingStatus.textContent = "Nhận dạng chưa thành công";
    setVoiceStage("error");
    toast(error.message, true);
  } finally {
    state.recorder = null;
    state.audioChunks = [];
    el.recordButton.disabled = !sttAvailable() || !state.sessionMicCheck?.ready;
    el.microphoneSelect.disabled = false;
    el.checkMicrophoneButton.disabled = false;
  }
}

async function handleNavigation(viewId) {
  showView(viewId);
  try {
    if (viewId === "teacherDashboardView") await loadExams();
    if (viewId === "teacherQuestionsView") await loadGeneratedQuestions();
    if (viewId === "teacherAccountsView") await loadAccounts();
    if (viewId === "teacherResultsView") { setTeacherResultPane(state.teacherResultPane); await loadTeacherWorkspace(); }
    if (viewId === "practiceHistoryView") await loadPracticeHistory();
  } catch (error) {
    toast(error.message, true);
  }
}

function bindEvents() {
  el.loginForm.addEventListener("submit", login);
  el.togglePasswordButton.addEventListener(
    "click",
    togglePasswordVisibility,
  );
  el.logoutButton.addEventListener("click", logout);
  el.roleNav.addEventListener("click", (event) => {
    const button = event.target.closest("[data-view]");
    if (button && !button.disabled) handleNavigation(button.dataset.view);
  });

  el.questionFile.addEventListener("change", updateQuestionFile);
  el.clearQuestionFileButton.addEventListener("click", () => { if (state.questionImporting) return; el.questionFile.value = ""; updateQuestionFile(); });
  for (const type of ["dragenter", "dragover"]) el.questionDropZone.addEventListener(type, (event) => { event.preventDefault(); if (!state.questionImporting) el.questionDropZone.classList.add("drag-over"); });
  el.questionDropZone.addEventListener("dragleave", () => el.questionDropZone.classList.remove("drag-over"));
  el.questionDropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    el.questionDropZone.classList.remove("drag-over");
    if (state.questionImporting) return;
    const files = event.dataTransfer?.files;
    if (files?.length !== 1) { setImportFeedback("Chọn một file JSON mỗi lần.", true); return; }
    try { el.questionFile.files = files; updateQuestionFile(); } catch (_) { setImportFeedback("Hãy nhấn Chọn file để tải JSON.", true); }
  });
  el.questionUploadForm.addEventListener("submit", importQuestions);
  el.reloadDemoButton.addEventListener("click", reloadDemo);
  el.generatedQuestionLanguage.addEventListener("change", () => { updateSubjectSelect(el.generatedQuestionLanguage, el.generatedQuestionSubject, false); updateGeneratorPreview(); });
  el.generatedQuestionSubject.addEventListener("change", updateGeneratorPreview);
  el.questionGeneratorForm.addEventListener("input", updateGeneratorPreview);
  el.generatedQuestionSearch.addEventListener("input", renderGeneratedQuestions);
  el.generatedDifficultyFilter.addEventListener("change", renderGeneratedQuestions);
  el.questionGeneratorForm.addEventListener("submit", generateQuestions);
  el.generatedQuestionStatus.addEventListener("change", renderGeneratedQuestions);
  el.refreshGeneratedQuestionsButton.addEventListener("click", refreshGeneratedQuestions);
  el.generatedQuestionRows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-generated-action]");
    if (button && !button.disabled) decideGeneratedQuestion(button);
  });
  el.examLanguage.addEventListener("change", () => { updateSubjectSelect(el.examLanguage, el.examSubject, false); updateExamBankHint(); });
  el.examSubject.addEventListener("change", updateExamBankHint);
  el.examForm.addEventListener("input", clearExamFeedback);
  el.generateExamCodeButton.addEventListener("click", () => { generateExamCode(); clearExamFeedback(); });
  el.examSearch.addEventListener("input", renderExams);
  el.examStatusFilter.addEventListener("change", renderExams);
  el.examStartsAt.addEventListener("input", () => { updateExamEndPreview(); el.examForm.querySelectorAll("[data-start-offset]").forEach((button) => button.setAttribute("aria-pressed", "false")); });
  el.examDuration.addEventListener("change", updateExamEndPreview);

  el.examForm.addEventListener("click", (event) => {
    const shortcut = event.target.closest("[data-start-offset]");

    if (shortcut) {
      setExamStartOffset(Number(shortcut.dataset.startOffset));
    }
  });
  el.examForm.addEventListener("submit", createExam);
  el.refreshExamsButton.addEventListener("click", refreshExams);
  el.examRows.addEventListener("click", (event) => {
    const statusButton = event.target.closest("[data-exam-id]");
    const deleteButton = event.target.closest("[data-delete-exam-id]");
    const copyButton = event.target.closest("[data-copy-exam-id]");
    if (statusButton && !statusButton.disabled) changeExamStatus(statusButton);
    if (deleteButton) deleteExamRound(deleteButton.dataset.deleteExamId);
    if (copyButton) copyExamCode(copyButton.dataset.copyExamId);
  });

  el.accountUploadForm.addEventListener("submit", importAccounts);
  el.accountFile.addEventListener("change", updateAccountFile);
  el.clearAccountFileButton.addEventListener("click", () => { if (state.accountImporting) return; el.accountFile.value = ""; updateAccountFile(); });
  for (const type of ["dragenter", "dragover"]) el.accountDropZone.addEventListener(type, (event) => { event.preventDefault(); if (!state.accountImporting) el.accountDropZone.classList.add("drag-over"); });
  el.accountDropZone.addEventListener("dragleave", () => el.accountDropZone.classList.remove("drag-over"));
  el.accountDropZone.addEventListener("drop", (event) => {
    event.preventDefault(); el.accountDropZone.classList.remove("drag-over"); if (state.accountImporting) return;
    if (event.dataTransfer?.files?.length !== 1) { teacherFeedback(el.accountImportFeedback, "Chọn một file mỗi lần."); return; }
    try { el.accountFile.files = event.dataTransfer.files; updateAccountFile(); } catch (_) { teacherFeedback(el.accountImportFeedback, "Hãy nhấn Chọn file để tải lên."); }
  });
  el.accountSearch.addEventListener("input", renderAccounts);
  el.accountRoleFilter.addEventListener("change", renderAccounts);
  el.accountStatusFilter.addEventListener("change", renderAccounts);
  el.refreshAccountsButton.addEventListener("click", refreshAccounts);
  el.accountRows.addEventListener("click", (event) => { const button = event.target.closest("[data-account-id]"); if (button && !button.disabled) toggleAccount(button); });
  el.teacherResultSearch.addEventListener("input", renderResults);
  el.teacherResultStatus.addEventListener("change", renderResults);
  el.teacherResultsButton.addEventListener("click", () => setTeacherResultPane("results"));
  el.teacherReviewsButton.addEventListener("click", () => { setTeacherResultPane("reviews"); const item = reviewItem() || state.reviewQueue.find((item) => !state.reviewSessionFilter || item.session_id === state.reviewSessionFilter); if (item) selectReviewAnswer(item.answer_id); });
  el.refreshTeacherWorkspaceButton.addEventListener("click", refreshTeacherWorkspace);
  el.refreshReviewQueueButton.addEventListener("click", refreshTeacherWorkspace);
  el.teacherResultRows.addEventListener("click", (event) => {
    const report = event.target.closest("[data-result-session]"), review = event.target.closest("[data-review-result-session]"), remove = event.target.closest("[data-delete-result-session]");
    if (report && !report.disabled) showTeacherResult(report.dataset.resultSession);
    if (review && !review.disabled) openReviewSession(review.dataset.reviewResultSession);
    if (remove && !remove.disabled) deleteTeacherResult(remove.dataset.deleteResultSession);
  });
  el.reviewSearch.addEventListener("input", renderReviewQueue);
  el.reviewSessionSelect.addEventListener("change", () => {
    if (state.reviewSaving) { el.reviewSessionSelect.value = state.reviewSessionFilter; return; }
    rememberReviewDraft(); state.reviewSessionFilter = el.reviewSessionSelect.value; state.manualReviewItem = null;
    const item = state.reviewQueue.find((item) => !state.reviewSessionFilter || item.session_id === state.reviewSessionFilter);
    selectReviewAnswer(item?.answer_id || "");
  });
  el.teacherReviewRows.addEventListener("click", (event) => { const button = event.target.closest("[data-review-answer]"); if (button && !button.disabled) selectReviewAnswer(button.dataset.reviewAnswer); });
  el.teacherReviewForm.addEventListener("submit", submitTeacherReview);
  el.reviewAcceptAiButton.addEventListener("click", acceptAiReview);
  el.teacherReviewForm.addEventListener("input", () => { rememberReviewDraft(); teacherFeedback(el.reviewFormFeedback, ""); });
  el.reviewReportButton.addEventListener("click", () => { const item = reviewItem(); if (item) showTeacherResult(item.session_id); });
  el.reviewReturnReportButton.addEventListener("click", () => { if (state.lastReviewedSessionId) showTeacherResult(state.lastReviewedSessionId); });
  el.reviewAudio.addEventListener("error", () => { el.reviewAudioStatus.textContent = "Không tải được ghi âm."; el.reviewAudioStatus.classList.remove("hidden"); });
  el.answerDetails.addEventListener("click", (event) => { const button = event.target.closest("[data-report-review-answer]"); if (button) openReviewSession(button.dataset.reportReviewSession, button.dataset.reportReviewAnswer); });

  el.refreshPracticeHistoryButton.addEventListener("click", refreshPracticeHistory);
  el.practiceHistoryRows.addEventListener("click", (event) => {
    const viewButton = event.target.closest("[data-practice-session]");
    const deleteButton = event.target.closest("[data-delete-practice-session]");
    if (viewButton && !viewButton.disabled) showPracticeHistoryReport(viewButton.dataset.practiceSession);
    if (deleteButton) deleteCandidatePracticeHistory(deleteButton.dataset.deletePracticeSession);
  });

  el.practiceLanguage.addEventListener("change", () => updateSubjectSelect(el.practiceLanguage, el.practiceSubject, true));
  el.practiceForm.addEventListener("submit", startPractice);
  el.examLookupForm.addEventListener("submit", checkExam);
  el.startRealButton.addEventListener("click", startReal);
  el.answerText.addEventListener("input", () => { el.charCount.textContent = `${el.answerText.value.length.toLocaleString("vi-VN")} ký tự`; });
  el.submitAnswerButton.addEventListener("click", submitCurrentAnswer);
  el.nextQuestionButton.addEventListener("click", nextPracticeQuestion);
  el.finishPracticeButton.addEventListener("click", finishPractice);
  el.recordButton.addEventListener("click", toggleRecording);
  el.checkMicrophoneButton.addEventListener("click", checkMicrophone);
  el.cancelMicTestButton.addEventListener("click", () => state.micTestController?.abort());
  el.microphoneSelect.addEventListener("change", selectMicrophone);
  navigator.mediaDevices?.addEventListener?.("devicechange", () => refreshMicrophones());
  el.backToRealButton.addEventListener("click", () => {
    state.candidateExam = null;
    el.examPreview.classList.add("hidden");
    el.candidateExamCode.value = "";
    showView("realSetupView");
  });
  el.reportBackButton.addEventListener("click", reportBack);
  el.reportCloseButton.addEventListener("click", reportBack);
  el.reportDialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    reportBack();
  });
  let reportBackdropPressed = false;
  el.reportDialog.addEventListener("pointerdown", (event) => {
    reportBackdropPressed = event.target === el.reportDialog;
  });
  el.reportDialog.addEventListener("click", (event) => {
    const bounds = el.reportDialog.getBoundingClientRect();
    const outside = event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom;
    if (reportBackdropPressed && event.target === el.reportDialog && outside) reportBack();
    reportBackdropPressed = false;
  });
  el.reportDialog.addEventListener("close", () => {
    document.body.classList.remove("report-modal-open");
    el.reportDialog.querySelectorAll("audio").forEach((audio) => audio.pause());
  });
}

async function initialize() {
  bindEvents();
  try {
    const response = await fetch("/api/auth/me", { credentials: "same-origin" });
    if (!response.ok) {
      showLogin();
      return;
    }
    const result = await response.json();
    await enterApp(result.user);
  } catch (_) {
    showLogin();
  }
}

document.addEventListener("DOMContentLoaded", initialize);
