const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');
const assert = require('node:assert/strict');
const script = fs.readFileSync(process.argv[2], 'utf8');
const html = fs.readFileSync(process.argv[3], 'utf8');
const fixtures = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));

function setup(name = 'processing') {
  const classes = () => ({add() {}, remove() {}, contains() {return false;}, toggle() {}});
  const nodes = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(match => [match[1], {
    id: match[1], value: '', textContent: '', innerHTML: '', dataset: {}, style: {},
    classList: classes(), querySelectorAll() {return [];}, setAttribute() {}, removeAttribute() {},
    pause() {}, open: false,
  }]));
  const timers = new Map(), calls = [];
  let serial = 0;
  const document = {body: {classList: classes()}, hidden: false, addEventListener() {},
    querySelectorAll(selector) {return selector === '[id]' ? [...nodes.values()] : [];}};
  const context = vm.createContext({document, console, window: {scrollTo() {}},
    setTimeout(callback, delay) {const id = ++serial; timers.set(id, {callback, delay}); return id;},
    clearTimeout(id) {timers.delete(id);}});
  vm.runInContext(script + '\nglobalThis.ui = {state, renderResults, loadTeacherWorkspace, showView,' +
    'scheduleTeacherWorkspaceRefresh, stopTeacherWorkspaceRefresh, setApi(fn) {api = fn;},' +
    'simplifyDetail() {renderReviewQueue = () => {}; renderReviewDetail = () => {};}};', context);
  const ui = context.ui;
  ui.state.user = {user_id: 1, role: 'teacher'};
  ui.state.activeViewId = 'teacherResultsView';
  ui.state.results = [structuredClone(fixtures[name])];
  ui.simplifyDetail();
  ui.setApi(async path => {
    calls.push(path);
    return path === '/api/teacher/results' ? {results: [structuredClone(fixtures.complete)]} : {answers: [], score_threshold: 50};
  });
  function fire() {
    const [id, timer] = timers.entries().next().value;
    timers.delete(id); timer.callback();
  }
  return {ui, nodes, document, timers, calls, fire};
}

test('A partial reviewed mean is labeled as a subset and never as the final grade', () => {
  const {ui, nodes} = setup('partial'); ui.renderResults();
  const rows = nodes.get('teacherResultRows').innerHTML;
  assert.match(rows, /Chưa chốt/); assert.match(rows, /Đã duyệt 1\/2 câu/);
  assert.match(rows, /phần đã duyệt: 80\/100/); assert.doesNotMatch(rows, /<strong>80\/100<\/strong>/);
});

for (const [name, score] of [['complete', 70], ['zero', 0]]) {
  test(`Final ${name} grade is taken from final_score`, () => {
    const {ui, nodes} = setup(name); ui.renderResults();
    assert.ok(nodes.get('teacherResultRows').innerHTML.includes(`<strong>${score}/100</strong>`));
  });
}

test('An empty attempt remains ungraded', () => {
  const {ui, nodes} = setup('empty'); ui.renderResults();
  assert.match(nodes.get('teacherResultRows').innerHTML, /Chưa chốt/);
  assert.doesNotMatch(nodes.get('teacherResultRows').innerHTML, /<strong>0\/100/);
});

test('AI progress and interruption come from backend fields', () => {
  const {ui, nodes} = setup(); ui.renderResults();
  assert.match(nodes.get('teacherResultRows').innerHTML, /Chấm AI 1\/2 câu/);
  ui.state.results[0].grading_state = 'failed'; ui.renderResults();
  assert.match(nodes.get('teacherResultRows').innerHTML, /Chấm AI bị gián đoạn/);
});

test('Legacy partial means are never promoted when final fields are absent', () => {
  const {ui, nodes} = setup('partial');
  delete ui.state.results[0].final_score; delete ui.state.results[0].score_status;
  ui.renderResults(); assert.doesNotMatch(nodes.get('teacherResultRows').innerHTML, /<strong>80\/100/);
});

test('Refresh uses existing read APIs and stops when AI grading is complete', async () => {
  const {ui, timers, calls, fire, nodes} = setup();
  ui.scheduleTeacherWorkspaceRefresh(); ui.scheduleTeacherWorkspaceRefresh();
  assert.equal(timers.size, 1); assert.equal([...timers.values()][0].delay, 5000);
  fire(); await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(calls, ['/api/teacher/results', '/api/teacher/reviews']);
  assert.equal(timers.size, 0);
  assert.match(nodes.get('teacherResultRows').innerHTML, /<strong>70\/100/);
});

for (const reason of ['hidden', 'saving']) {
  test(`No background request while ${reason}`, () => {
    const {ui, document, timers, calls, fire} = setup();
    ui.scheduleTeacherWorkspaceRefresh();
    if (reason === 'hidden') document.hidden = true; else ui.state.reviewSaving = true;
    fire(); assert.equal(calls.length, 0); assert.equal(timers.size, 1);
  });
}

test('Leaving the teacher view cancels scheduled refresh', () => {
  const {ui, timers, calls} = setup(); ui.scheduleTeacherWorkspaceRefresh();
  ui.showView('teacherDashboardView'); assert.equal(timers.size, 0); assert.equal(calls.length, 0);
});

test('A stale timer cannot request results after an identity change', () => {
  const {ui, calls, fire} = setup(); ui.scheduleTeacherWorkspaceRefresh();
  ui.state.authGeneration++; ui.state.user = {user_id: 2, role: 'candidate'};
  fire(); assert.equal(calls.length, 0);
});

test('No timer is scheduled for failed or already graded work', () => {
  for (const name of ['complete', 'partial', 'empty']) {
    const {ui, timers} = setup(name); ui.scheduleTeacherWorkspaceRefresh(); assert.equal(timers.size, 0);
  }
  const {ui, timers} = setup(); ui.state.results[0].grading_state = 'failed';
  ui.scheduleTeacherWorkspaceRefresh(); assert.equal(timers.size, 0);
});
