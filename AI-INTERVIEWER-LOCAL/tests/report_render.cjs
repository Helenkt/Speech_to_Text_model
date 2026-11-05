// DOM-double tests of production JS. These are not visual or microphone tests.
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const test = require("node:test");
const source = fs.readFileSync(process.argv[2], "utf8");
const fixture = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

function setup(report = fixture.mixed, origin = "practice") {
  const nodes = new Map(fixture.ids.map(id => {
    const classes = new Set();
    return [id, { id, textContent: "", innerHTML: "", value: "", dataset: {}, open: true,
      classList: {
        toggle(name, force) {
          const include = force === undefined ? !classes.has(name) : force;
          if (include) classes.add(name); else classes.delete(name);
        },
        add(...names) { names.forEach(name => classes.add(name)); },
        remove(...names) { names.forEach(name => classes.delete(name)); },
        contains(name) { return classes.has(name); },
      },
      querySelectorAll() { return []; },
    }];
  }));
  const document = {
    querySelectorAll(selector) { return selector === "[id]" ? [...nodes.values()] : []; },
    addEventListener() {},
  };
  const context = vm.createContext({ document, console, window: {}, navigator: {},
    setTimeout: fn => setTimeout(fn, 0), clearTimeout });
  vm.runInContext(source + "\nglobalThis.audit = {state, el, renderReport, renderPracticeHistory," +
    "watchSessionGrading, pointAssessmentHtml, practiceQuestionGradeHtml," +
    "setApi(fn) {speechApi = fn;}, forget(fn) {forgetActiveSession = fn;}};", context);
  const api = context.audit;
  api.state.reportOrigin = origin;
  api.state.user = { role: origin === "teacher" ? "teacher" : "candidate" };
  api.renderReport(structuredClone(report));
  return { nodes, api };
}

test("partial grade is never presented as whole-session 100 percent", () => {
  const { nodes } = setup();
  assert.equal(nodes.get("reportPercentage").textContent, "—");
  assert.equal(nodes.get("reportScore").textContent, "—");
  assert.equal(nodes.get("reportVerdict").textContent, "Chưa đủ điểm toàn bài");
  assert.match(nodes.get("reportCoverage").textContent, /1\/2/);
  assert.match(nodes.get("reportSummaryText").textContent, /1 câu chưa có điểm đã xác minh/);
  assert.doesNotMatch(nodes.get("reportSummaryText").textContent, /100\/100/);
  assert.equal(nodes.get("reportContent").classList.contains("hidden"), false);
});

test("a failed batch keeps graded answers visible and the warning visible", () => {
  const { nodes } = setup(fixture.failed);
  assert.equal(nodes.get("reportContent").classList.contains("hidden"), false);
  assert.equal(nodes.get("reportGradingPanel").classList.contains("hidden"), false);
  assert.equal(nodes.get("retrySessionGradingButton").classList.contains("hidden"), true);
  assert.match(nodes.get("answerDetails").innerHTML, /10\/10/);
  assert.equal(nodes.get("reportPercentage").textContent, "—");
});

test("full score remains final and visible", () => {
  const { nodes } = setup(fixture.full);
  assert.equal(nodes.get("reportScore").textContent, "10");
  assert.equal(nodes.get("reportPercentage").textContent, "100%");
  assert.equal(nodes.get("reportTotalScore").textContent, "100/100");
});

test("practice uncertainty never directs students to a teacher review queue", () => {
  const { nodes } = setup(fixture.mixed);
  assert.match(nodes.get("answerDetails").innerHTML, /AI could not verify|AI chưa đủ cơ sở/);
  assert.doesNotMatch(nodes.get("answerDetails").innerHTML, /Cần giáo viên xem lại/);
  const report = structuredClone(fixture.mixed);
  report.session.interview_mode = "real";
  report.answers[1].evaluation.review_required = true;
  const teacher = setup(report, "teacher");
  assert.match(teacher.nodes.get("answerDetails").innerHTML, /Cần giáo viên xem lại/);
});

test("an empty report never invents zero or a final grade", () => {
  const empty = structuredClone(fixture.full);
  empty.answers = [];
  empty.session.answered_count = 0;
  const { nodes } = setup(empty);
  assert.equal(nodes.get("reportScore").textContent, "—");
  assert.equal(nodes.get("reportTotalScore").textContent, "—");
});

test("history shows coverage and withholds an incomplete whole-session grade", () => {
  const { nodes, api } = setup();
  api.state.practiceHistory = [fixture.history];
  api.renderPracticeHistory();
  assert.match(nodes.get("practiceHistoryRows").innerHTML, /Chưa có điểm cuối/);
  assert.match(nodes.get("practiceHistoryRows").innerHTML, /1\/2 câu/);
  assert.doesNotMatch(nodes.get("practiceHistoryRows").innerHTML, /100\/100/);
});

test("teacher final totals retain their manual score", () => {
  const report = structuredClone(fixture.full);
  report.session.interview_mode = "real";
  delete report.summary.practice_grading;
  report.summary.average_score = 73;
  report.answers[0].evaluation.final_score = 73;
  const { nodes } = setup(report, "teacher");
  assert.equal(nodes.get("reportScore").textContent, "73");
});

test("explicit backend retry eligibility is respected", () => {
  const report = structuredClone(fixture.failed);
  report.grading.can_retry = false;
  report.grading.attempts = 1;
  const { nodes } = setup(report);
  assert.equal(nodes.get("retrySessionGradingButton").classList.contains("hidden"), true);
});

test("watch fetches an available partial report before stopping on failure", async () => {
  const { nodes, api } = setup(fixture.mixed);
  const urls = [];
  api.setApi(async url => {
    urls.push(url);
    return structuredClone(url.endsWith("/grading") ? fixture.failed.grading : fixture.failed);
  });
  await api.watchSessionGrading("test-id", "practice");
  assert.equal(urls.length, 2);
  assert.ok(urls[1].endsWith("/report"));
  assert.equal(nodes.get("reportContent").classList.contains("hidden"), false);
  assert.match(nodes.get("reportGradingStatus").textContent, /gián đoạn/);
});

test("unchanged progress does not repeatedly download the same partial report", async () => {
  const { api } = setup();
  let polls = 0, reports = 0;
  api.setApi(async url => {
    if (url.endsWith("/grading")) {
      polls += 1;
      return polls < 3 ? {...fixture.failed.grading, state: "queued"} : fixture.failed.grading;
    }
    reports += 1;
    return fixture.failed;
  });
  await api.watchSessionGrading("test-id", "practice");
  assert.equal(polls, 3);
  assert.equal(reports, 2);
});

test("closing the dialog while a report loads prevents stale rendering", async () => {
  const { api, nodes } = setup();
  const stale = structuredClone(fixture.failed);
  stale.session.subject = "STALE REPORT MUST NOT RENDER";
  api.setApi(async url => {
    if (url.endsWith("/grading")) return fixture.failed.grading;
    nodes.get("reportDialog").open = false;
    return stale;
  });
  const before = nodes.get("reportTitle").textContent;
  await api.watchSessionGrading("test-id", "practice");
  assert.equal(nodes.get("reportTitle").textContent, before);
  assert.equal(nodes.get("reportPercentage").textContent, "—");
});

test("teacher watcher uses teacher endpoint and updates its review cache", async () => {
  const { api } = setup(fixture.mixed, "teacher");
  const urls = [];
  api.setApi(async url => {
    urls.push(url);
    return url.endsWith("/grading") ? fixture.failed.grading : fixture.failed;
  });
  await api.watchSessionGrading("teacher-id", "teacher");
  assert.equal(urls[1], "/api/teacher/results/teacher-id");
  assert.equal(api.state.reviewReportCache.has("teacher-id"), true);
});

test("practice exposes subject and competency coverage without turning partial means into final scores", () => {
  const { nodes } = setup();
  assert.equal(nodes.get("practiceGradingSection").classList.contains("hidden"), false);
  assert.equal(nodes.get("reportLegacyCompetencies").classList.contains("hidden"), true);
  assert.match(nodes.get("practiceSubjectRows").innerHTML, /DSA101/);
  assert.match(nodes.get("practiceSubjectRows").innerHTML, /1\/2 câu/);
  assert.match(nodes.get("practiceCompetencyRows").innerHTML, /Chưa đủ bằng chứng/);
  assert.doesNotMatch(nodes.get("practiceSubjectRows").innerHTML, /10\/10/);
  assert.match(nodes.get("practiceSessionGrade").textContent, /Chưa đủ bằng chứng/);
});

test("fully graded API reports expose per-course, per-competency and per-question scores on scale ten", () => {
  const { nodes } = setup(fixture.full);
  assert.match(nodes.get("practiceSessionGrade").textContent, /Đã chốt/);
  assert.match(nodes.get("practiceSubjectRows").innerHTML, /10\/10/);
  assert.match(nodes.get("practiceCompetencyRows").innerHTML, /10\/10/);
  assert.match(nodes.get("answerDetails").innerHTML, /Điểm câu: 10\/10/);
  for (const criterion of fixture.full.answers[0].evaluation.score_breakdown.criteria) {
    assert.ok(nodes.get("answerDetails").innerHTML.includes(`${criterion.earned_points} / ${criterion.max_points} điểm`));
  }
});

test("weighted criteria use backend points and never invent zero for unresolved evidence", () => {
  const { api } = setup();
  const evaluation = fixture.weighted;
  const html = api.pointAssessmentHtml(evaluation.point_assessments, evaluation.score_breakdown);
  assert.match(html, /4 \/ 4 điểm/);
  assert.match(html, /3 \/ 3 điểm/);
  assert.match(html, /Chưa xác minh \/ 3 điểm/);
  assert.doesNotMatch(html, /0 \/ 3 điểm/);
  const summary = api.practiceQuestionGradeHtml(evaluation.score_breakdown);
  assert.match(summary, /Điểm câu: Chưa chốt/);
  assert.match(summary, /7\/10/);
  assert.match(summary, /7–10\/10/);
});

test("verified zero remains zero and is not treated as missing", () => {
  const { api } = setup();
  const html = api.practiceQuestionGradeHtml({
    score: 0, status: "final", scale: 10, criteria: [], confirmed_points: 0,
  });
  assert.match(html, /Điểm câu: 0\/10/);
  assert.match(html, /Đã chốt/);
});

test("a null score with a final flag does not invent a final zero", () => {
  const { api } = setup();
  const html = api.practiceQuestionGradeHtml({score: null, status: "final", criteria: []});
  assert.match(html, /Chưa chốt/);
  assert.doesNotMatch(html, /0\/10|Đã chốt/);
});

test("invalid and mismatched rubric results have clear nonfinal labels", () => {
  const { api } = setup();
  for (const [status, label] of [["invalid_rubric", "Rubric cần kiểm tra"], ["score_mismatch", "Điểm cần đối chiếu"]]) {
    const html = api.practiceQuestionGradeHtml({status, score: null, criteria: []});
    assert.ok(html.includes(label));
    assert.match(html, /Chưa chốt/);
  }
});

test("opening a formal report after practice clears practice-only scores", () => {
  const { nodes, api } = setup(fixture.full);
  const formal = structuredClone(fixture.full);
  formal.session.interview_mode = "real";
  delete formal.summary.practice_grading;
  api.state.reportOrigin = "teacher";
  api.renderReport(formal);
  assert.equal(nodes.get("practiceGradingSection").classList.contains("hidden"), true);
  assert.equal(nodes.get("reportLegacyCompetencies").classList.contains("hidden"), false);
  assert.equal(nodes.get("practiceSubjectRows").innerHTML, "");
  assert.equal(nodes.get("practiceCompetencyRows").innerHTML, "");
  assert.equal(nodes.get("practiceSessionGrade").textContent, "");
});

test("course names and competency labels remain escaped", () => {
  const report = structuredClone(fixture.full);
  report.summary.practice_grading.subjects[0].subject = '<img src=x onerror="alert(1)">';
  report.summary.practice_grading.competencies[0].competency = "<script>bad()</script>";
  const { nodes } = setup(report);
  assert.doesNotMatch(nodes.get("practiceSubjectRows").innerHTML, /<img/);
  assert.doesNotMatch(nodes.get("practiceCompetencyRows").innerHTML, /<script/);
  assert.match(nodes.get("practiceCompetencyRows").innerHTML, /&lt;script&gt;/);
});

test("practice has one main scale-ten score and hides duplicated totals", () => {
  const {nodes} = setup(fixture.full);
  assert.equal(nodes.get("reportScoreScale").textContent, "/10");
  assert.equal(nodes.get("reportTotalCard").classList.contains("hidden"), true);
  assert.equal(nodes.get("reportPercentageCard").classList.contains("hidden"), true);
  assert.equal(nodes.get("reportStatGrid").classList.contains("practice-report-stats"), true);
  assert.doesNotMatch(nodes.get("answerDetails").innerHTML, /mức tin cậy|report-engine|Đã đối chiếu từng ý rubric/);
});

test("learning feedback and transcript evidence are visible and escaped", () => {
  const report = structuredClone(fixture.full);
  report.answers[0].evaluation.learning_feedback = {summary: 'You correctly stated: <img src=x onerror="bad()">',
    items: [{evidence_quotes: ['<script>bad()</script>']} ]};
  report.answers[0].answer = '<script>bad()</script>';
  report.answers[0].evaluation.graded_transcript = report.answers[0].answer;
  const {nodes} = setup(report);
  const html = nodes.get("answerDetails").innerHTML;
  assert.match(html, /You correctly stated: &lt;img/);
  assert.match(html, /&lt;script&gt;bad\(\)&lt;\/script&gt;/);
  assert.doesNotMatch(html, /<img|<script/);
});

test("teacher reports reset the practice layout and hide student retry actions", () => {
  const {nodes, api} = setup(fixture.full);
  const report = structuredClone(fixture.full);
  report.session.interview_mode = "real";
  delete report.summary.practice_grading;
  api.state.reportOrigin = "teacher";
  api.renderReport(report);
  assert.equal(nodes.get("reportTotalCard").classList.contains("hidden"), false);
  assert.equal(nodes.get("reportScoreScale").textContent, "/100");
  assert.equal(nodes.get("practiceNextStepsSection").classList.contains("hidden"), true);
  assert.equal(nodes.get("practiceNextSteps").innerHTML, "");
  assert.equal(api.state.practiceReportSessionId, null);
});

test("technical failures do not tell the student to record again", () => {
  const {nodes} = setup(fixture.failed);
  assert.match(nodes.get("practiceNextSteps").innerHTML, /Grading of your saved response is incomplete|Bộ chấm chưa hoàn tất/);
  assert.doesNotMatch(nodes.get("practiceNextSteps").innerHTML, /data-practice-again/);
});

test("practice suggestions after the first five are available in an expandable group", () => {
  const report = structuredClone(fixture.full);
  report.summary.learning_feedback.next_steps = Array.from({length: 6}, (_, i) => ({
    action: "practice_again", category: "knowledge", answer_id: i + 1,
    sequence_number: i + 1, message: "Review this criterion", focus_points: []}));
  const {nodes} = setup(report);
  const html = nodes.get("practiceNextSteps").innerHTML;
  assert.match(html, /<details class="practice-next-more"><summary>1 đề xuất khác/);
  assert.match(html, /data-practice-again="6"/);
  assert.equal([...html.matchAll(/data-practice-again=/g)].length, 6);
});

test("all report evidence paths reject quotes absent from the graded transcript", () => {
  const report = structuredClone(fixture.full);
  const quote = "FORGED EVIDENCE ABSENT FROM TRANSCRIPT";
  report.answers[0].evaluation.point_assessments[0].evidence_quote = quote;
  report.answers[0].evaluation.learning_feedback.items[0].evidence_quotes = [quote];
  const {nodes} = setup(report);
  assert.equal(nodes.get("answerDetails").innerHTML.includes(quote), false);
});

test("evidence follows the accepted strong transcript and never an unrelated original", () => {
  const report = structuredClone(fixture.full);
  const quote = "Strong verified transcript";
  report.answers[0].answer = "Original recording transcript";
  report.answers[0].evaluation.graded_transcript = quote;
  report.answers[0].evaluation.grading_source = "strong_ai";
  report.answers[0].evaluation.point_assessments[0].evidence_quote = quote;
  const {nodes} = setup(report);
  assert.ok(nodes.get("answerDetails").innerHTML.includes(`<q>${quote}</q>`));
});
