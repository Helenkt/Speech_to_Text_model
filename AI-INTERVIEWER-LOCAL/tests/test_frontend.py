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
        "teacherReviewsView",
        "teacherAccountsView",
        "teacherResultsView",
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
        "checkMicrophoneButton",
        "microphoneCheckResult",
        "evaluationReview",
        "partialPoints",
        "contradictedPoints",
        "pointAssessmentList",
        "answerDetails",
    } <= set(ids)
    assert "Đăng ký" not in html
    assert "Tạo và mở đợt Interview" in html
    assert "Kết quả Interview thật chỉ hiển thị cho Giáo viên" in html
    assert "Lịch sử luyện tập" in html
    assert '<option value="text">' not in html
    assert '<option value="both">' not in html
    assert 'id="answerText" maxlength="20000" readonly' in html

    javascript = (project_root / "app" / "static" / "app.js").read_text(
        encoding="utf-8"
    )
    referenced_ids = set(re.findall(r"\bel\.([A-Za-z][A-Za-z0-9_]*)", javascript))
    assert referenced_ids <= set(ids)
    assert "function refreshExams()" in javascript
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
    assert "async function submitTeacherReview(button)" in javascript
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
