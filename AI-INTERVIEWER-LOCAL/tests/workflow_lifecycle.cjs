// Production workflow functions with controlled fetch/cache; no live HTTP or microphone.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const test = require('node:test');
const source = fs.readFileSync(process.argv[2], 'utf8');
const fixture = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
function classes() {
  const values = new Set();
  return {add(...xs) {xs.forEach(x => values.add(x));}, remove(...xs) {xs.forEach(x => values.delete(x));},
    contains(x) {return values.has(x);}, toggle(x, force) {if (force ?? !values.has(x)) values.add(x); else values.delete(x);}};
}
const user = id => ({user_id: id, full_name: `Student ${id}`, role: 'candidate'});
const session = id => ({session_id: id, interview_mode: 'practice', language: 'vi', answered_count: 0,
  requested_count: 2, grading_strategy: 'end_of_session', question: {id: `${id}-q`, language: 'vi', question: `${id} question`}});
const history = id => ({session_id: id, status: 'completed', answered_count: 1, requested_count: 1,
  language: 'vi', subject: 'DSA101', score_status: 'final', final_score: 80,
  scored_answer_count: 1, stored_answer_count: 1, can_view_report: true});
const response = (body, status = 200) => ({ok: status === 200, status,
  headers: {get() {return 'application/json';}}, async json() {return body;}});
function setup() {
  const nodes = new Map(fixture.ids.map(id => [id, {id, value: '', textContent: '', innerHTML: '', open: false,
    classList: classes(), dataset: {}, style: {}, attributes: {}, querySelectorAll() {return [];}, focus() {}, pause() {},
    setAttribute(key, value) {this.attributes[key] = value;}, removeAttribute(key) {delete this.attributes[key];},
    replaceChildren() {}, dispatchEvent() {}, close() {this.open = false;}}]));
  const stored = new Map();
  const context = vm.createContext({document: {body: {classList: classes()}, addEventListener() {},
    querySelectorAll(selector) {return selector === '[id]' ? [...nodes.values()] : [];},
    querySelector() {return {value: 'Easy'};}}, window: {scrollTo() {}, confirm() {return true;}}, navigator: {}, console,
    performance, Event, AbortController, setTimeout, clearTimeout, setInterval, clearInterval,
    localStorage: {getItem(key) {return stored.get(key);}, setItem(key, value) {stored.set(key, value);}, removeItem(key) {stored.delete(key);}}});
  vm.runInContext(source + '\nglobalThis.audit = {state, loadPracticeHistory, refreshPracticeHistory, startPractice, startReal, beginSession, submitCurrentAnswer, finishPractice, showLogin,' +
    'setFetch(fn) {globalThis.fetch = fn;}, setCache(fn) {recordingCache = fn;}, setReport(fn) {loadPracticeReport = fn;}, prepare() {renderQuestion = () => {};}};', context);
  const app = context.audit;
  app.prepare();
  app.state.user = user(2);
  app.state.activeViewId = 'practiceHistoryView';
  nodes.get('practiceLanguage').value = 'vi';
  nodes.get('practiceSubject').value = 'DSA101';
  nodes.get('practiceQuestionCount').value = '2';
  return {app, nodes, stored};
}
const event = () => ({preventDefault() {}});
function preview(app, nodes, id) {
  app.state.session = session(id);
  app.state.currentQuestion = app.state.session.question;
  app.state.currentTranscriptionId = `${id}-voice`;
  app.state.currentPreviewSha256 = 'a'.repeat(64);
  app.state.draftLoading = false;
  nodes.get('answerText').value = `${id} spoken answer`;
}
test('old successful history cannot publish A history under B', async () => {
  const {app, nodes} = setup();
  let release;
  app.setFetch(() => new Promise(resolve => {release = resolve;}));
  const pending = app.loadPracticeHistory();
  app.showLogin();
  app.state.user = user(3);
  app.state.practiceHistory = [history('B-private')];
  release(response({sessions: [history('A-private')]}));
  await pending;
  assert.equal(app.state.practiceHistory[0].session_id, 'B-private');
  assert.ok(!nodes.get('practiceHistoryRows').innerHTML.includes('A-private'));
});
test('latest history wins and old response cannot remove a newer loading state', async () => {
  const {app, nodes} = setup();
  const releases = [];
  app.setFetch(() => new Promise(resolve => releases.push(resolve)));
  const old = app.loadPracticeHistory(), fresh = app.loadPracticeHistory();
  releases[0](response({sessions: [history('stale')]}));
  await old;
  assert.equal(nodes.get('practiceHistoryRows').attributes['aria-busy'], 'true');
  releases[1](response({sessions: [history('fresh')]}));
  await fresh;
  assert.equal(app.state.practiceHistory[0].session_id, 'fresh');
  assert.equal(nodes.get('practiceHistoryRows').attributes['aria-busy'], undefined);
});
test('history responses in reverse order keep the newest result', async () => {
  const {app} = setup();
  const releases = [];
  app.setFetch(() => new Promise(resolve => releases.push(resolve)));
  const old = app.loadPracticeHistory(), fresh = app.loadPracticeHistory();
  releases[1](response({sessions: [history('fresh')]})); await fresh;
  releases[0](response({sessions: [history('stale')]})); await old;
  assert.equal(app.state.practiceHistory[0].session_id, 'fresh');
});
test('history is invalidated even when the same account logs in again', async () => {
  const {app} = setup();
  let release;
  app.setFetch(() => new Promise(resolve => {release = resolve;}));
  const pending = app.loadPracticeHistory();
  const original = app.state.user;
  app.showLogin(); app.state.user = original;
  release(response({sessions: [history('old-epoch')]})); await pending;
  assert.equal(app.state.practiceHistory.length, 0);
});
test('a newer direct history load releases a superseded refresh button', async () => {
  const {app, nodes} = setup();
  const releases = [];
  app.setFetch(() => new Promise(resolve => releases.push(resolve)));
  const old = app.refreshPracticeHistory(), fresh = app.loadPracticeHistory();
  releases[1](response({sessions: []})); await fresh;
  releases[0](response({sessions: []})); await old;
  assert.equal(nodes.get('refreshPracticeHistoryButton').disabled, false);
  assert.equal(nodes.get('refreshPracticeHistoryButton').textContent, 'Làm mới');
});
for (const action of ['startPractice', 'startReal']) {
  test(`old ${action} cannot replace B session or persist it under B`, async () => {
    const {app, stored} = setup();
    app.state.candidateExam = {exam_code: 'EXAM'};
    let release;
    app.setFetch(() => new Promise(resolve => {release = resolve;}));
    const pending = app[action](event());
    app.showLogin(); app.state.user = user(3); app.state.session = session('B-session');
    release(response(session('A-session'))); await pending;
    assert.equal(app.state.session.session_id, 'B-session');
    assert.notEqual(stored.get('ai-interview-active:3'), 'A-session');
  });
}
test('only the latest start can choose the session and release its start button', async () => {
  const {app, nodes} = setup();
  const releases = [];
  app.setFetch(() => new Promise(resolve => releases.push(resolve)));
  const old = app.startPractice(event()), fresh = app.startPractice(event());
  releases[0](response(session('old'))); await old;
  assert.equal(nodes.get('startPracticeButton').disabled, true);
  assert.equal(app.state.session, null);
  releases[1](response(session('fresh'))); await fresh;
  assert.equal(app.state.session.session_id, 'fresh');
  assert.equal(nodes.get('startPracticeButton').disabled, false);
});
test('cross-mode starts cannot leave the superseded mode button locked after failure', async () => {
  const {app, nodes} = setup();
  const releases = [];
  app.state.candidateExam = {exam_code: 'EXAM'};
  app.setFetch(() => new Promise(resolve => releases.push(resolve)));
  const practice = app.startPractice(event()), exam = app.startReal();
  releases[0](response(session('practice'))); await practice;
  assert.equal(app.state.session, null);
  assert.equal(nodes.get('startPracticeButton').disabled, false);
  releases[1](response({detail: 'Exam closed'}, 409)); await exam;
  assert.equal(nodes.get('startRealButton').disabled, false);
});
test('confirmation rechecks identity after waiting for cache deletion', async () => {
  const {app, nodes} = setup();
  preview(app, nodes, 'A-session'); app.state.savedRecording = {key: 'A-cache'};
  let releaseDelete;
  app.setCache(() => new Promise(resolve => {releaseDelete = resolve;}));
  app.setFetch(async () => response({answered_count: 1, requested_count: 2, completed: false,
    next_question: {id: 'A-next', language: 'vi'}}));
  const pending = app.submitCurrentAnswer();
  while (!releaseDelete) await new Promise(resolve => setImmediate(resolve));
  app.showLogin(); app.state.user = user(3); preview(app, nodes, 'B-session');
  app.state.savedRecording = {key: 'B-cache'};
  releaseDelete(); await pending;
  assert.equal(app.state.currentQuestion.id, 'B-session-q');
  assert.equal(app.state.session.answered_count, 0);
  assert.equal(app.state.savedRecording.key, 'B-cache');
});
test('a late old confirmation cannot clear a new active submission lock', async () => {
  const {app, nodes} = setup(); preview(app, nodes, 'A-session');
  let release;
  app.setFetch(() => new Promise(resolve => {release = resolve;}));
  const pending = app.submitCurrentAnswer();
  app.showLogin(); app.state.user = user(3); preview(app, nodes, 'B-session');
  app.state.answerSubmitting = true;
  release(response({answered_count: 1, requested_count: 2, completed: false})); await pending;
  assert.equal(app.state.answerSubmitting, true);
});
test('a current confirmation saves the captured preview and advances exactly once', async () => {
  const {app, nodes} = setup(); preview(app, nodes, 'current');
  const saved = {key: 'current-cache'}; app.state.savedRecording = saved;
  let deleted, body;
  app.setCache(async (action, value) => {assert.equal(action, 'delete'); deleted = value;});
  app.setFetch(async (path, options) => {
    body = JSON.parse(options.body);
    return response({answered_count: 1, requested_count: 2, completed: false, next_question: {id: 'next'}});
  });
  await app.submitCurrentAnswer();
  assert.equal(body.preview_sha256, 'a'.repeat(64));
  assert.equal(deleted, saved);
  assert.equal(app.state.savedRecording, null);
  assert.equal(app.state.currentQuestion.id, 'next');
  assert.equal(app.state.session.answered_count, 1);
  assert.equal(app.state.answerSubmitting, false);
});
test('a failed current confirmation keeps its recording and allows retry', async () => {
  const {app, nodes} = setup(); preview(app, nodes, 'current');
  const saved = {key: 'current-cache'}; app.state.savedRecording = saved;
  app.setFetch(async () => response({detail: 'Temporary error'}, 503));
  await app.submitCurrentAnswer();
  assert.equal(app.state.savedRecording, saved);
  assert.equal(app.state.session.answered_count, 0);
  assert.equal(app.state.answerSubmitting, false);
  assert.equal(nodes.get('submitAnswerButton').disabled, false);
});
test('current history and start responses remain usable', async () => {
  const {app, nodes, stored} = setup();
  app.setFetch(async () => response({sessions: [history('current')]}));
  await app.loadPracticeHistory();
  assert.ok(nodes.get('practiceHistoryRows').innerHTML.includes('current'));
  app.setFetch(async () => response(session('current')));
  await app.startPractice(event());
  assert.equal(app.state.session.session_id, 'current');
  assert.equal(stored.get('ai-interview-active:2'), 'current');
});
test('a late finish response cannot open B report or clear B finish lock', async () => {
  const {app, nodes} = setup(); preview(app, nodes, 'A-session');
  let release, reports = 0;
  app.setFetch(() => new Promise(resolve => {release = resolve;}));
  app.setReport(async () => {reports++;});
  const pending = app.finishPractice();
  app.showLogin(); app.state.user = user(3); preview(app, nodes, 'B-session');
  app.state.sessionFinishing = true;
  release(response({})); await pending;
  assert.equal(reports, 0);
  assert.equal(app.state.completed, false);
  assert.equal(app.state.sessionFinishing, true);
});
test('a current finish response still opens its report and releases its lock', async () => {
  const {app, nodes} = setup(); preview(app, nodes, 'current');
  let reports = 0;
  app.setFetch(async () => response({}));
  app.setReport(async () => {reports++;});
  await app.finishPractice();
  assert.equal(reports, 1);
  assert.equal(app.state.sessionFinishing, false);
});
test('a new session resets controls owned by superseded submission or finish requests', () => {
  const {app, nodes} = setup();
  app.state.answerSubmitting = app.state.sessionFinishing = true;
  for (const id of ['finishPracticeButton', 'microphoneSelect', 'checkMicrophoneButton']) nodes.get(id).disabled = true;
  app.beginSession(session('new'));
  assert.equal(app.state.answerSubmitting, false);
  assert.equal(app.state.sessionFinishing, false);
  for (const id of ['finishPracticeButton', 'microphoneSelect', 'checkMicrophoneButton']) assert.equal(nodes.get(id).disabled, false);
  assert.equal(nodes.get('recordButton').disabled, true);
});
