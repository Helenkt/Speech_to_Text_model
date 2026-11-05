// Actual UI functions in a DOM double, not a screenshot or browser test.
const fs = require("node:fs");
const vm = require("node:vm");
const test = require("node:test");
const assert = require("node:assert/strict");
const source = fs.readFileSync(process.argv[2] || process.env.AUDIT_APP_SCRIPT, "utf8");
const fixture = JSON.parse(fs.readFileSync(process.argv[3] || process.env.AUDIT_REPORT_FIXTURE, "utf8"));

function classList() {
  const values = new Set();
  return {
    add(...names) { names.forEach(name => values.add(name)); },
    remove(...names) { names.forEach(name => values.delete(name)); },
    contains(name) { return values.has(name); },
    toggle(name, force) {
      const include = force === undefined ? !values.has(name) : force;
      if (include) values.add(name); else values.delete(name);
    },
  };
}

function setup() {
  const nodes = new Map(fixture.ids.map(id => [id, {
    id, classList: classList(), textContent: "", innerHTML: "", value: "", open: false,
    dataset: {}, style: {}, setAttribute() {}, removeAttribute() {}, focus() {}, pause() {},
    querySelectorAll() { return []; },
    showModal() { this.open = true; }, close() { this.open = false; },
  }]));
  const document = {
    body: {classList: classList()},
    querySelectorAll(selector) {
      return selector === "[id]" ? [...nodes.values()] : [];
    },
    addEventListener() {},
  };
  const context = vm.createContext({document, window: {scrollTo() {}}, navigator: {},
    console, setTimeout: fn => setTimeout(fn, 0), clearTimeout,
    localStorage: {getItem() {return null;}, setItem() {}, removeItem() {}}});
  vm.runInContext(source + "\nglobalThis.audit = {state, el, showPracticeHistoryReport, showTeacherResult," +
    "logout, showView, dismissReportDialog, practiceAgain, loadPracticeReport, renderReport, openReportDialog, enterApp," +
    "setApi(fn) {api = fn;}, setSpeech(fn) {speechApi = fn;}, setWatcher(fn) {watchSessionGrading = fn;}," +
    "setSummary(fn) {applySummary = fn;}, setStorage(value) {globalThis.localStorage = value;}," +
    "setBegin(fn) {beginSession = fn;}};", context);
  const api = context.audit;
  api.state.user = {user_id: 2, role: "candidate"};
  api.state.reportOrigin = "history";
  api.state.activeViewId = "practiceHistoryView";
  const pending = new Map(), rejected = new Map(), watched = [];
  api.setApi(path => {
    if (path === "/api/auth/logout") return Promise.resolve({logged_out: true});
    return new Promise((resolve, reject) => { pending.set(path, resolve); rejected.set(path, reject); });
  });
  api.setWatcher(async (...args) => watched.push(args));
  return {api, nodes, pending, rejected, watched};
}

function retryEvent() {
  const button = {dataset: {practiceAgain: "1"}, disabled: false};
  return {button, event: {target: {closest() {return button;}}}};
}

test("practice-again ignores duplicate clicks and opens a new session", async () => {
  const {api, nodes, pending} = setup();
  api.state.practiceReportSessionId = "OLD";
  nodes.get("reportDialog").open = true;
  let began = null;
  api.setBegin(value => {began = value;});
  const {event, button} = retryEvent();
  const loading = api.practiceAgain(event);
  assert.equal(button.disabled, true);
  await api.practiceAgain(event);
  assert.equal(pending.size, 1);
  pending.get("/api/interviews/OLD/practice-again")({session_id: "NEW"});
  await loading;
  assert.equal(began.session_id, "NEW");
  assert.equal(nodes.get("reportDialog").open, false);
  assert.equal(button.disabled, false);
});

test("practice-again response after closing or logout cannot navigate the student", async () => {
  for (const logout of [false, true]) {
    const {api, nodes, pending} = setup();
    api.state.practiceReportSessionId = "OLD";
    nodes.get("reportDialog").open = true;
    let began = false;
    api.setBegin(() => {began = true;});
    const loading = api.practiceAgain(retryEvent().event);
    if (logout) await api.logout(); else api.dismissReportDialog();
    pending.get("/api/interviews/OLD/practice-again")({session_id: "NEW"});
    await loading;
    assert.equal(began, false);
    assert.equal(nodes.get("reportDialog").open, false);
  }
});

function report(title) {
  const value = structuredClone(fixture.full);
  value.session.subject = title;
  return value;
}

test("latest student history selection must win when responses arrive out of order", async () => {
  const {api, nodes, pending, watched} = setup();
  const older = api.showPracticeHistoryReport("A");
  const newer = api.showPracticeHistoryReport("B");
  pending.get("/api/interviews/B/report")(report("REPORT B"));
  await newer;
  assert.equal(nodes.get("reportTitle").textContent, "REPORT B");
  pending.get("/api/interviews/A/report")(report("REPORT A"));
  await older;
  assert.equal(nodes.get("reportTitle").textContent, "REPORT B", JSON.stringify({
    visible: nodes.get("reportTitle").textContent, watched}));
});

test("student report response arriving after logout must not reopen private report dialog", async () => {
  const {api, nodes, pending} = setup();
  const loading = api.showPracticeHistoryReport("A");
  await api.logout();
  assert.equal(api.state.user, null);
  assert.equal(nodes.get("reportDialog").open, false);
  pending.get("/api/interviews/A/report")(report("PRIVATE STUDENT REPORT"));
  await loading;
  assert.equal(nodes.get("reportDialog").open, false, JSON.stringify({
    user: api.state.user, report: nodes.get("reportTitle").textContent,
    dialogOpen: nodes.get("reportDialog").open, loginVisible: !nodes.get("loginView").classList.contains("hidden")}));
});

test("leaving history view while report loads must not reopen it on a different view", async () => {
  const {api, nodes, pending} = setup();
  const loading = api.showPracticeHistoryReport("A");
  api.showView("practiceSetupView");
  pending.get("/api/interviews/A/report")(report("OLD HISTORY REPORT"));
  await loading;
  assert.equal(nodes.get("reportDialog").open, false, JSON.stringify({
    activeView: api.state.activeViewId, dialogOpen: nodes.get("reportDialog").open}));
});

test("control: teacher report load is already invalidated by logout", async () => {
  const {api, nodes, pending} = setup();
  api.state.user.role = "teacher";
  const loading = api.showTeacherResult("T");
  await api.logout();
  const value = report("TEACHER REPORT");
  value.session.interview_mode = "real";
  pending.get("/api/teacher/results/T")(value);
  await loading;
  assert.equal(nodes.get("reportDialog").open, false);
});

test("control: an ordinary current student request can display its report", async () => {
  const {api, nodes, pending} = setup();
  const loading = api.showPracticeHistoryReport("A");
  pending.get("/api/interviews/A/report")(report("CURRENT REPORT"));
  await loading;
  assert.equal(nodes.get("reportDialog").open, true);
  assert.equal(nodes.get("reportTitle").textContent, "CURRENT REPORT");
});

test("leaving and returning to history still invalidates the older request", async () => {
  const {api, nodes, pending} = setup();
  const loading = api.showPracticeHistoryReport("A");
  api.showView("practiceSetupView");
  api.showView("practiceHistoryView");
  pending.get("/api/interviews/A/report")(report("OLD REPORT"));
  await loading;
  assert.equal(nodes.get("reportDialog").open, false);
});

test("a response from an earlier user identity cannot show up for another student", async () => {
  const {api, nodes, pending} = setup();
  const loading = api.showPracticeHistoryReport("A");
  api.state.user = {user_id: 3, role: "candidate"};
  pending.get("/api/interviews/A/report")(report("PRIVATE EARLIER USER"));
  await loading;
  assert.equal(nodes.get("reportDialog").open, false);
});

test("a stale request error does not replace a current report with an error toast", async () => {
  const {api, nodes, pending, rejected} = setup();
  const older = api.showPracticeHistoryReport("A");
  const newer = api.showPracticeHistoryReport("B");
  pending.get("/api/interviews/B/report")(report("REPORT B"));
  await newer;
  rejected.get("/api/interviews/A/report")(new Error("OLD REQUEST ERROR"));
  await older;
  assert.equal(nodes.get("reportTitle").textContent, "REPORT B");
  assert.notEqual(nodes.get("toast").textContent, "OLD REQUEST ERROR");
});

test("closing the report invalidates an outstanding history load", async () => {
  const {api, nodes, pending} = setup();
  const loading = api.showPracticeHistoryReport("A");
  api.dismissReportDialog();
  pending.get("/api/interviews/A/report")(report("CLOSED REPORT"));
  await loading;
  assert.equal(nodes.get("reportDialog").open, false);
});

test("logout invalidates report loads before the logout HTTP response arrives", async () => {
  const {api, nodes} = setup();
  const pending = new Map();
  api.setApi(path => new Promise(resolve => pending.set(path, resolve)));
  const loading = api.showPracticeHistoryReport("A");
  const loggingOut = api.logout();
  pending.get("/api/interviews/A/report")(report("LOGOUT IN PROGRESS"));
  await loading;
  assert.equal(nodes.get("reportDialog").open, false);
  pending.get("/api/auth/logout")({logged_out: true});
  await loggingOut;
  assert.equal(api.state.user, null);
});

test("initial end-of-practice report cannot overwrite another students report", async () => {
  const {api, nodes, watched} = setup();
  api.state.session = {...fixture.full.session};
  let release;
  api.setSpeech(() => new Promise(resolve => {release = resolve;}));
  const loading = api.loadPracticeReport();
  await api.logout();
  api.state.user = {user_id: 3, role: "candidate"};
  api.state.reportOrigin = "history";
  const next = report("CURRENT STUDENT B");
  next.session.user_id = 3;
  next.session.session_id = "B";
  api.renderReport(next);
  api.openReportDialog();
  release(report("PRIVATE STUDENT A"));
  await loading;
  assert.equal(nodes.get("reportTitle").textContent, "CURRENT STUDENT B");
  assert.equal(nodes.get("reportDialog").open, true);
  assert.equal(watched.length, 0);
});

test("initial report response and error are ignored after dialog close or view change", async () => {
  for (const reject of [false, true]) {
    const {api, nodes, watched} = setup();
    api.state.session = {...fixture.full.session};
    let finish;
    api.setSpeech(() => new Promise((resolve, fail) => {finish = reject ? fail : resolve;}));
    const loading = api.loadPracticeReport();
    api.showView("practiceHistoryView");
    api.renderReport(report("SELECTED REPORT B"));
    api.openReportDialog();
    finish(reject ? new Error("STALE INITIAL ERROR") : report("STALE INITIAL REPORT"));
    await loading;
    assert.equal(nodes.get("reportTitle").textContent, "SELECTED REPORT B");
    assert.notEqual(nodes.get("toast").textContent, "STALE INITIAL ERROR");
    assert.equal(watched.length, 0);
  }
});

test("an active initial report is rendered and starts the grading watcher", async () => {
  const {api, nodes, watched} = setup();
  api.state.session = {...fixture.full.session};
  api.setSpeech(async () => report("CURRENT INITIAL REPORT"));
  await api.loadPracticeReport();
  assert.equal(nodes.get("reportTitle").textContent, "CURRENT INITIAL REPORT");
  assert.equal(watched.length, 1);
});

test("delayed app initialization cannot update the next signed-in identity", async () => {
  const {api, nodes, pending} = setup();
  const owner = {user_id: 2, role: "candidate", full_name: "A"};
  const loading = api.enterApp(owner);
  api.state.user = {user_id: 3, role: "candidate", full_name: "B"};
  pending.get("/api/health")({question_generation: {model: "OLD OWNER MODEL"}});
  pending.get("/api/questions/summary")({languages: []});
  await loading;
  assert.notEqual(nodes.get("questionModelName").textContent, "OLD OWNER MODEL");
});

test("a restored completed report is discarded if its owner logs out while loading", async () => {
  const {api, nodes, watched} = setup();
  api.state.session = null;
  api.setSummary(() => {});
  api.setStorage({getItem() {return "RESTORED";}});
  api.setApi(async path => {
    if (path.endsWith("/resume")) throw Object.assign(new Error("completed"), {status: 409});
    return path === "/api/health" ? {question_generation: {}} : {};
  });
  let release;
  api.setSpeech(path => path.endsWith("/grading") ? Promise.resolve({state: "completed"})
    : new Promise(resolve => {release = resolve;}));
  const loading = api.enterApp({user_id: 2, role: "candidate", full_name: "A"});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(typeof release, "function");
  await api.logout();
  release(report("PRIVATE RESTORED REPORT"));
  await loading;
  assert.equal(nodes.get("reportDialog").open, false);
  assert.equal(watched.length, 0);
});
