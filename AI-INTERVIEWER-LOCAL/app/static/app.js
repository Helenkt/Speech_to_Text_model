const state = {
  user: null,
  health: null,
  summary: null,
  exams: [],
  accounts: [],
  results: [],
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
};

const el = Object.fromEntries(
  [...document.querySelectorAll("[id]")].map((node) => [node.id, node]),
);

const NAV_ITEMS = {
  teacher: [
    ["teacherDashboardView", "Interview"],
    ["teacherAccountsView", "Tài khoản"],
    ["teacherResultsView", "Kết quả"],
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
  if (state.recorder?.state === "recording") {
    state.recorder.onstop = null;
    state.recorder.stop();
  }
  state.mediaStream?.getTracks().forEach((track) => track.stop());
  state.user = null;
  state.session = null;
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
    el.loginButton.textContent = "ĐĂNG NHẬP";
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
  select.innerHTML = languages.map((item) => `<option value="${escapeHtml(item.language)}">${languageName(item.language)} (${item.total})</option>`).join("");
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
    options.push(`<option value="${escapeHtml(subject.name)}">${escapeHtml(subject.name)} (${subject.total})</option>`);
  }
  subjectSelect.innerHTML = options.join("");
  if ([...subjectSelect.options].some((item) => item.value === previous)) subjectSelect.value = previous;
}

function applySummary(summary) {
  state.summary = summary;
  fillLanguageSelect(el.examLanguage);
  fillLanguageSelect(el.practiceLanguage);
  updateSubjectSelect(el.examLanguage, el.examSubject, false);
  updateSubjectSelect(el.practiceLanguage, el.practiceSubject, true);
  const rows = summary.languages || [];
  el.questionBankRows.innerHTML = rows.length
    ? rows.map((item) => `<div class="summary-row"><strong>${languageName(item.language)}</strong><span>${item.total.toLocaleString("vi-VN")} câu · ${item.subjects.length} lĩnh vực</span></div>`).join("")
    : '<div class="empty-state">Chưa có câu hỏi. Hãy import file JSON.</div>';
}

async function refreshSummary() {
  applySummary(await api("/api/questions/summary"));
}

async function importQuestions(event) {
  event.preventDefault();
  const file = el.questionFile.files[0];
  if (!file) return;
  if (el.questionImportMode.value === "replace" && !window.confirm("Thay các câu hỏi của ngôn ngữ có trong file?")) return;
  const form = new FormData();
  form.append("file", file);
  form.append("mode", el.questionImportMode.value);
  form.append("default_language", el.questionDefaultLanguage.value);
  el.questionImportButton.disabled = true;
  el.questionImportButton.textContent = "Đang kiểm tra...";
  try {
    const result = await api("/api/questions/import", { method: "POST", body: form });
    await refreshSummary();
    el.questionUploadForm.reset();
    el.questionFileName.textContent = "Tối đa 25 MB · kiểm tra toàn bộ trước khi ghi";
    toast(`Đã nhập ${result.imported} câu: ${result.created} mới, ${result.updated} cập nhật.`);
  } catch (error) {
    toast(error.message, true);
  } finally {
    el.questionImportButton.disabled = false;
    el.questionImportButton.textContent = "Kiểm tra và import";
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
}

function setDefaultExamTimes() {
  // Mặc định bắt đầu sau 15 phút và mở trong 2 giờ.
  el.examDuration.value = "120";
  setExamStartOffset(15);

  if (!el.examCode.value) {
    el.examCode.value = `AI${String(Date.now()).slice(-6)}`;
  }
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

function renderExams() {
  el.examRows.innerHTML = state.exams.length
    ? state.exams.map((exam) => {
      const [label, style] = availabilityInfo(exam);
      const nextStatus = exam.status === "open" ? "closed" : "open";
      return `<div class="round-row">
        <div><strong>${escapeHtml(exam.title)}</strong><small>${escapeHtml(exam.exam_code)} · ${escapeHtml(exam.subject)}</small><span class="status-badge ${style}">${label}</span></div>
        <div><strong>${languageName(exam.language)} · ${exam.question_count} câu</strong><span>${difficultyName(exam.starting_difficulty)} · ${answerModeName(exam.answer_mode)}</span></div>
        <div><strong>${formatDate(exam.starts_at)}</strong><span>đến ${formatDate(exam.ends_at)}</span></div>
        <div><strong>${exam.attempt_count || 0} lượt làm</strong><span>${exam.completed_count || 0} đã hoàn tất</span></div>
        <div class="round-actions">
          <button class="button secondary compact" data-exam-id="${escapeHtml(exam.exam_round_id)}" data-next-status="${nextStatus}">${nextStatus === "closed" ? "Đóng" : "Mở lại"}</button>
          <button class="button secondary danger compact" data-delete-exam-id="${escapeHtml(exam.exam_round_id)}">Xóa đợt</button>
        </div>
      </div>`;
    }).join("")
    : '<div class="empty-state">Chưa có bài Interview.</div>';
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
  el.createExamButton.disabled = true;
  el.createExamButton.textContent = "Đang tạo...";
  try {
    const difficulty = document.querySelector('input[name="examDifficulty"]:checked').value;
    const startsAt = new Date(el.examStartsAt.value);
    const endsAt = getExamEndTime();
    const payload = {
      title: el.examTitle.value.trim(),
      exam_code: el.examCode.value.trim(),
      language: el.examLanguage.value,
      subject: el.examSubject.value,
      question_count: Number(el.examQuestionCount.value),
      starting_difficulty: difficulty,
      answer_mode: el.examAnswerMode.value,
      starts_at: startsAt.toISOString(),
      ends_at: endsAt.toISOString(),
    };
    const result = await api("/api/teacher/exams", jsonOptions("POST", payload));
    toast(`Đã mở đợt Interview với mã ${result.exam.exam_code}.`);
    el.examForm.reset();
    setDefaultExamTimes();
    await loadExams();
  } catch (error) {
    toast(error.message, true);
  } finally {
    el.createExamButton.disabled = false;
    el.createExamButton.textContent = "Tạo và mở Interview →";
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
  el.accountCount.textContent = `${state.accounts.length} tài khoản`;
  el.accountRows.innerHTML = state.accounts.length
    ? state.accounts.map((account) => `<tr>
      <td><strong>${escapeHtml(account.username)}</strong></td>
      <td>${escapeHtml(account.full_name)}</td>
      <td><span class="role-badge ${account.role}">${account.role === "teacher" ? "Giáo viên" : "Ứng viên"}</span></td>
      <td><span class="account-meta"><span>${escapeHtml(account.email || "—")}</span><small>${escapeHtml(account.student_id || "")}</small></span></td>
      <td>${account.active ? "Đang hoạt động" : "Đã khóa"}</td>
      <td><button class="button secondary compact" data-account-id="${account.user_id}" data-account-active="${!account.active}" ${account.user_id === state.user.user_id ? "disabled" : ""}>${account.active ? "Khóa" : "Mở"}</button></td>
    </tr>`).join("")
    : '<tr><td colspan="6">Chưa có tài khoản.</td></tr>';
}

async function loadAccounts() {
  const result = await api("/api/teacher/accounts");
  state.accounts = result.accounts;
  renderAccounts();
}

async function importAccounts(event) {
  event.preventDefault();
  const file = el.accountFile.files[0];
  if (!file) return;
  if (el.accountImportMode.value === "replace" && !window.confirm("Các tài khoản không có trong file sẽ bị khóa. Tiếp tục?")) return;
  const form = new FormData();
  form.append("file", file);
  form.append("mode", el.accountImportMode.value);
  el.accountImportButton.disabled = true;
  el.accountImportButton.textContent = "Đang kiểm tra...";
  try {
    const result = await api("/api/teacher/accounts/import", { method: "POST", body: form });
    state.accounts = result.accounts;
    renderAccounts();
    el.accountUploadForm.reset();
    toast(`Đã nhập ${result.imported} tài khoản: ${result.created} mới, ${result.updated} cập nhật.`);
  } catch (error) {
    toast(error.message, true);
  } finally {
    el.accountImportButton.disabled = false;
    el.accountImportButton.textContent = "Kiểm tra và import";
  }
}

async function toggleAccount(button) {
  button.disabled = true;
  try {
    await api(`/api/teacher/accounts/${button.dataset.accountId}/active`, jsonOptions("PATCH", { active: button.dataset.accountActive === "true" }));
    await loadAccounts();
    toast("Đã cập nhật trạng thái tài khoản.");
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

function renderResults() {
  el.teacherResultRows.innerHTML = state.results.length
    ? state.results.map((result) => `<tr>
      <td><strong>${escapeHtml(result.exam_code)}</strong><br><small>${escapeHtml(result.subject)}</small></td>
      <td>${escapeHtml(result.candidate_name)}<br><small>${escapeHtml(result.student_id || result.email || result.username)}</small></td>
      <td>${result.answered_count}/${result.requested_count} câu · ${result.status === "completed" ? "Hoàn tất" : "Đang làm"}</td>
      <td><strong>${result.average_score == null ? "—" : `${Math.round(result.average_score)}/100`}</strong></td>
      <td>${formatDate(result.finished_at || result.created_at)}</td>
      <td><div class="table-actions"><button class="button secondary compact" data-result-session="${escapeHtml(result.session_id)}">Xem chi tiết</button><button class="button secondary danger compact" data-delete-result-session="${escapeHtml(result.session_id)}">Xóa</button></div></td>
    </tr>`).join("")
    : '<tr><td colspan="6">Chưa có ứng viên làm bài Interview.</td></tr>';
}

async function loadResults() {
  const result = await api("/api/teacher/results");
  state.results = result.results;
  renderResults();
}

async function deleteTeacherResult(sessionId) {
  if (!window.confirm("Xóa vĩnh viễn kết quả Interview này? Nếu bài Interview vẫn mở, ứng viên có thể làm lại mã đề.")) return;
  try {
    await api(`/api/teacher/results/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    await loadResults();
    toast("Đã xóa kết quả Interview.");
  } catch (error) {
    toast(error.message, true);
  }
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
    showView("reportView");
  } catch (error) {
    toast(error.message, true);
  }
}

async function showTeacherResult(sessionId) {
  try {
    const report = await api(`/api/teacher/results/${sessionId}`);
    state.reportOrigin = "teacher";
    renderReport(report);
    showView("reportView");
  } catch (error) {
    toast(error.message, true);
  }
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

async function refreshMicrophones(preferredId = "") {
  if (!navigator.mediaDevices?.enumerateDevices) return;
  try {
    const devices = (await navigator.mediaDevices.enumerateDevices())
      .filter((device) => device.kind === "audioinput");
    const selected = preferredId || state.selectedMicrophoneId || savedMicrophoneId();
    el.microphoneSelect.innerHTML = [
      '<option value="">Microphone mặc định</option>',
      ...devices.map((device, index) => `<option value="${escapeHtml(device.deviceId)}">${escapeHtml(device.label || `Microphone ${index + 1}`)}</option>`),
    ].join("");
    if (devices.some((device) => device.deviceId === selected)) {
      el.microphoneSelect.value = selected;
      state.selectedMicrophoneId = selected;
    } else {
      state.selectedMicrophoneId = "";
    }
  } catch (_) {
    el.microphoneSelect.innerHTML = '<option value="">Microphone mặc định</option>';
  }
}

function selectMicrophone() {
  state.selectedMicrophoneId = el.microphoneSelect.value;
  try {
    localStorage.setItem("ai-interview-microphone", state.selectedMicrophoneId);
  } catch (_) { /* Browser storage is optional. */ }
}

function beginSession(session) {
  state.session = session;
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
  state.ambientNoiseDbfs = null;
  el.charCount.textContent = "0 ký tự";
  el.submitAnswerButton.disabled = true;

  el.answerText.readOnly = true;
  el.answerText.placeholder = "Bản chuyển giọng nói sẽ xuất hiện tại đây...";
  el.answerModeHint.textContent = "Chỉ trả lời bằng ghi âm";
  el.recordButton.classList.remove("hidden");
  el.recordButton.textContent = "● Ghi âm";
  el.microphoneSelect.disabled = false;
  refreshMicrophones();
  el.recordButton.disabled = !sttAvailable();
  if (sttReady()) {
    el.sttStatus.textContent = `${state.health.speech_to_text.model} · ${languageName(sessionLanguage)}`;
    el.sttStatus.className = "status-pill";
    el.recordingStatus.textContent = "Bấm Ghi âm để trả lời";
  } else if (sttAvailable()) {
    el.sttStatus.textContent = `${state.health.speech_to_text.model} · khởi tạo khi dùng`;
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
    showView("reportView");
  } catch (error) {
    toast(error.message, true);
  }
}

function renderReport(report) {
  const session = report.session;
  el.reportTitle.textContent = `Báo cáo · ${session.candidate_name}`;
  el.reportMeta.textContent = `${languageName(session.language)} · ${session.subject || "Tất cả lĩnh vực"} · ${session.answered_count}/${session.requested_count} câu`;
  el.reportScore.textContent = Math.round(report.summary.average_score);
  el.reportVerdict.textContent = report.summary.overall_verdict;
  fillList(el.strengthList, report.summary.strengths, "Chưa đủ dữ liệu");
  fillList(el.gapList, report.summary.gaps, "Chưa đủ dữ liệu");
  el.competencyRows.innerHTML = report.summary.competencies.length
    ? report.summary.competencies.map((item) => `<div class="competency-row"><strong>${escapeHtml(item.name)}</strong><div class="competency-bar"><i style="width:${Math.max(0, Math.min(100, item.average_score))}%"></i></div><span>${Math.round(item.average_score)}/100 · ${item.question_count} câu</span></div>`).join("")
    : "<p>Chưa có câu trả lời để tổng hợp.</p>";
  el.answerDetails.innerHTML = report.answers.length
    ? report.answers.map((item) => {
      const review = item.evaluation.review_required
        ? '<div class="review-notice">Cần giáo viên xem lại kết quả và bằng chứng của câu này.</div>'
        : "";
      const assessments = pointAssessmentHtml(item.evaluation.point_assessments);
      return `<details class="detail-item"><summary><span class="detail-number">${item.sequence_number}</span><span>${escapeHtml(item.question.question)}</span><span class="detail-score">${Math.round(item.evaluation.score)}/100</span></summary><div class="detail-content">${review}<h4>Câu trả lời</h4><p>${escapeHtml(item.answer)}</p><h4>Phản hồi</h4><p>${escapeHtml(item.evaluation.feedback)}</p>${assessments ? `<h4>Đối chiếu rubric</h4><div class="assessment-list">${assessments}</div>` : ""}<h4>Đáp án tham khảo</h4><p>${escapeHtml(item.reference_answer)}</p><h4>Bộ chấm</h4><p>${escapeHtml(item.evaluation.evaluator)} · độ tin cậy ${Math.round(item.evaluation.confidence * 100)}% · rubric ${escapeHtml(item.evaluation.rubric_version || "mặc định")}</p></div></details>`;
    }).join("")
    : '<div class="empty-state">Phiên kết thúc trước khi có câu trả lời.</div>';
}

function reportBack() {
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

async function toggleRecording() {
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
    await refreshMicrophones(activeDeviceId);
    el.microphoneSelect.disabled = true;
    el.recordingStatus.textContent = "Giữ im lặng 1,5 giây để kiểm tra tiếng nền...";
    const ambient = await measureAmbientNoise(state.mediaStream, 1500);
    state.ambientNoiseDbfs = ambient.dbfs;
    const dangerouslyNoisy = ambient.dbfs > -12 || ambient.clippingRatio > 0.05;
    if (dangerouslyNoisy) {
      state.mediaStream.getTracks().forEach((track) => track.stop());
      state.mediaStream = null;
      el.microphoneSelect.disabled = false;
      el.recordingStatus.textContent = `Môi trường quá ồn (${ambient.dbfs.toFixed(1)} dBFS)`;
      setVoiceStage("error");
      toast("Âm thanh đang quá lớn hoặc bị vỡ tiếng. Hãy đưa microphone xa hơn nguồn ồn rồi thử lại.", true);
      return;
    }
    const preferred = typeof MediaRecorder.isTypeSupported === "function"
      ? ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((type) => MediaRecorder.isTypeSupported(type))
      : null;
    state.audioChunks = [];
    state.recorder = preferred ? new MediaRecorder(state.mediaStream, { mimeType: preferred }) : new MediaRecorder(state.mediaStream);
    state.recorder.ondataavailable = (event) => { if (event.data.size) state.audioChunks.push(event.data); };
    state.recorder.onstop = transcribeRecording;
    state.recorder.start(250);
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
        : `Không mở được microphone: ${error.message}`;
    toast(message, true);
    setVoiceStage("error");
    el.microphoneSelect.disabled = false;
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
  el.microphoneSelect.disabled = false;
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
    el.recordButton.textContent = "● Ghi âm lại";
    setVoiceStage("verify");
  } catch (error) {
    el.recordingStatus.textContent = "Nhận dạng chưa thành công";
    setVoiceStage("error");
    toast(error.message, true);
  } finally {
    state.recorder = null;
    state.audioChunks = [];
    el.recordButton.disabled = !sttAvailable();
  }
}

async function handleNavigation(viewId) {
  showView(viewId);
  try {
    if (viewId === "teacherDashboardView") await loadExams();
    if (viewId === "teacherAccountsView") await loadAccounts();
    if (viewId === "teacherResultsView") await loadResults();
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

  el.questionFile.addEventListener("change", () => { el.questionFileName.textContent = el.questionFile.files[0]?.name || "Tối đa 25 MB · kiểm tra toàn bộ trước khi ghi"; });
  el.questionUploadForm.addEventListener("submit", importQuestions);
  el.reloadDemoButton.addEventListener("click", reloadDemo);
  el.examLanguage.addEventListener("change", () => updateSubjectSelect(el.examLanguage, el.examSubject, false));
  el.examStartsAt.addEventListener("input", updateExamEndPreview);
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
    if (statusButton) changeExamStatus(statusButton);
    if (deleteButton) deleteExamRound(deleteButton.dataset.deleteExamId);
  });

  el.accountUploadForm.addEventListener("submit", importAccounts);
  el.accountRows.addEventListener("click", (event) => {
    const button = event.target.closest("[data-account-id]");
    if (button) toggleAccount(button);
  });
  el.teacherResultRows.addEventListener("click", (event) => {
    const viewButton = event.target.closest("[data-result-session]");
    const deleteButton = event.target.closest("[data-delete-result-session]");
    if (viewButton) showTeacherResult(viewButton.dataset.resultSession);
    if (deleteButton) deleteTeacherResult(deleteButton.dataset.deleteResultSession);
  });

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
  el.microphoneSelect.addEventListener("change", selectMicrophone);
  navigator.mediaDevices?.addEventListener?.("devicechange", () => refreshMicrophones());
  el.backToRealButton.addEventListener("click", () => {
    state.candidateExam = null;
    el.examPreview.classList.add("hidden");
    el.candidateExamCode.value = "";
    showView("realSetupView");
  });
  el.reportBackButton.addEventListener("click", reportBack);
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
