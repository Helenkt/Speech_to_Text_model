import re


def test_frontend_has_unique_ids_and_both_role_flows(project_root):
    html = (project_root / "app" / "static" / "index.html").read_text(
        encoding="utf-8"
    )
    ids = re.findall(r'id="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    assert {
        "loginForm",
        "teacherDashboardView",
        "teacherQuestionsView",
        "teacherAccountsView",
        "teacherResultsView",
        "teacherResultsPanel",
        "teacherReviewsPanel",
        "teacherResultsButton",
        "teacherReviewsButton",
        "practiceSetupView",
        "practiceHistoryView",
        "practiceHistoryRows",
        "refreshPracticeHistoryButton",
        "realSetupView",
        "interviewView",
        "questionUploadForm",
        "accountUploadForm",
        "examForm",
        "recordButton",
        "microphoneSelect",
        "answerText",
        "voicePipeline",
        "questionGeneratorForm",
        "generatedQuestionRows",
        "teacherReviewRows",
        "reviewPolicyNotice",
        "reviewStrongTranscript",
        "reviewStrongModel",
        "reviewAcceptAiButton",
        "reviewOriginalScore",
        "reviewFinalScore",
        "reviewDecisionStatus",
        "reviewHistoryRows",
        "reviewHistoryCount",
        "checkMicrophoneButton",
        "microphoneCheckResult",
        "evaluationReview",
        "partialPoints",
        "contradictedPoints",
        "pointAssessmentList",
        "answerDetails",
    } <= set(ids)
    assert "Đăng ký" not in html
    assert "Quản lý bài thi" in html
    assert "Kết quả &amp; chấm lại" in html
    assert "Lịch sử luyện tập" in html
    assert "USER LOGIN" not in html
    assert ">ĐĂNG NHẬP<" not in html
    assert 'data-lucide="mic"' in html
    assert 'data-lucide="search"' in html
    assert '<option value="text">' not in html
    assert '<option value="both">' not in html
    assert 'id="answerText" maxlength="20000" readonly' in html

    javascript = (project_root / "app" / "static" / "app.js").read_text(
        encoding="utf-8"
    )
    referenced_ids = set(re.findall(r"\bel\.([A-Za-z][A-Za-z0-9_]*)", javascript))
    assert referenced_ids <= set(ids)
    assert "function refreshExams()" in javascript
    assert "function renderLucideIcons(" in javascript
    assert "function sttAvailable()" in javascript
    assert "function deleteTeacherResult(sessionId)" in javascript
    assert "function deleteCandidatePracticeHistory(sessionId)" in javascript
    assert "function deleteExamRound(examRoundId)" in javascript
    assert "data-delete-result-session" in javascript
    assert "data-delete-practice-session" in javascript
    assert "data-delete-exam-id" in javascript
    assert 'state.health?.speech_to_text?.installed' in javascript
    assert 'el.answerModeHint.textContent = "Chỉ trả lời bằng ghi âm"' in javascript
    assert "function setVoiceStage(stage)" in javascript
    assert "function renderPointAssessments(assessments)" in javascript
    assert "async function generateQuestions(event)" in javascript
    assert 'async function submitTeacherReview(event, action = "manual")' in javascript
    assert "async function acceptAiReview()" in javascript
    assert "async function loadStrongReview(item)" in javascript
    assert "async function loadReviewHistory(item" in javascript
    assert 'api(`/api/teacher/answers/${encodeURIComponent(answerId)}/reviews`)' in javascript
    assert 'method: "POST"' in javascript
    assert 'action: "manual"' not in javascript
    assert '"accept_ai"' in javascript
    assert 'el.reviewAudio.addEventListener("ended"' not in javascript
    assert 'form.append("session_id", state.session.session_id)' in javascript
    assert "Cần nghe hết voice" not in javascript
    assert "async function checkMicrophone()" in javascript
    assert 'api("/api/speech/microphone-check"' in javascript
    assert "item.evidence_quote" in javascript
    assert 'select.value = "vi"' in javascript
    assert 'state.session?.language || state.currentQuestion?.language || "vi"' in javascript
    assert "async function refreshMicrophones" in javascript
    assert 'localStorage.setItem("ai-interview-microphone"' in javascript


def test_project_has_direct_main_entrypoint(project_root):
    main_file = (project_root / "main.py").read_text(encoding="utf-8")
    assert "uvicorn.run" in main_file
    assert 'host="127.0.0.1"' in main_file
    assert (project_root / "data" / "account_template.xlsx").exists()
