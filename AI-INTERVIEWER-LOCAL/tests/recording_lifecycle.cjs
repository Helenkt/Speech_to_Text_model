// Real capture functions; permission, tracks and encoder are simulated, with no live mic.
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
function setup(failure = '') {
  const nodes = new Map(fixture.ids.map(id => [id, {id, textContent: '', innerHTML: '', value: '', open: false,
    disabled: false, classList: classes(), dataset: {}, style: {}, querySelectorAll() {return [];}, focus() {}, pause() {},
    setAttribute() {}, removeAttribute() {}, replaceChildren() {}, dispatchEvent() {}, close() {this.open = false;}}]));
  const permission = [], streams = [], recorders = [], transcriptions = [];
  const stream = deviceId => {
    const track = {stopped: false, getSettings() {return {deviceId};}, stop() {this.stopped = true;}};
    const value = {track, getTracks() {return [track];}, getAudioTracks() {return [track];}};
    streams.push(value); return value;
  };
  class Recorder {
    static isTypeSupported() {return true;}
    constructor(value) {
      if (failure === 'constructor') throw new Error('Encoder unavailable');
      this.stream = value; this.state = 'inactive'; recorders.push(this);
    }
    start() {if (failure === 'start') throw new Error('Encoder start failed'); this.state = 'recording';}
    stop() {this.state = 'inactive';} // Tests explicitly deliver the delayed stop event.
  }
  const context = vm.createContext({document: {body: {classList: classes()}, addEventListener() {},
    querySelectorAll(selector) {return selector === '[id]' ? [...nodes.values()] : [];}},
    window: {scrollTo() {}, confirm() {return true;}}, navigator: {mediaDevices: {getUserMedia(constraints) {
      return new Promise((resolve, reject) => permission.push({resolve, reject, constraints}));
    }}}, MediaRecorder: Recorder, Event, console, setTimeout, clearTimeout,
    localStorage: {getItem() {return null;}, setItem() {}, removeItem() {}}});
  vm.runInContext(source + '\nglobalThis.audit = {state, toggleRecording, showLogin, beginSession, finishPractice,' +
    'prepare(fn) {transcribeRecording = fn; renderQuestion = () => {};}};', context);
  const app = context.audit;
  app.prepare(async () => {transcriptions.push({userId: app.state.user.user_id,
    sessionId: app.state.session.session_id, chunks: [...app.state.audioChunks]});});
  function identity(id = 2) {
    app.state.user = {user_id: id, full_name: `Student ${id}`, role: 'candidate'};
    app.state.session = {session_id: `session-${id}`, interview_mode: 'practice', language: 'vi',
      requested_count: 2, answered_count: 0, grading_strategy: 'end_of_session', question: {id: `q-${id}`, language: 'vi'}};
    app.state.currentQuestion = app.state.session.question;
    app.state.sessionMicCheck = {ready: true, deviceId: 'mic-1', baselineDbfs: -45};
    app.state.selectedMicrophoneId = 'mic-1';
    app.state.health = {speech_to_text: {installed: true, ready: true}};
    app.state.completed = false; app.state.draftLoading = false;
  }
  identity();
  const grant = (index = 0, deviceId = 'mic-1') => permission[index].resolve(stream(deviceId));
  return {app, nodes, permission, streams, recorders, transcriptions, identity, grant};
}
test('late permission after completion closes its track without starting a recorder', async () => {
  const {app, grant, streams, recorders} = setup();
  const pending = app.toggleRecording();
  app.state.completed = true; app.state.currentQuestion = null;
  grant(); await pending;
  assert.equal(recorders.length, 0);
  assert.ok(streams[0].track.stopped);
  assert.equal(app.state.recordingRequest, null);
});
test('double record clicks open only one stream and logout closes it', async () => {
  const {app, permission, grant, streams, recorders} = setup();
  const first = app.toggleRecording(), second = app.toggleRecording();
  assert.equal(permission.length, 1);
  grant(); await Promise.all([first, second]);
  assert.equal(recorders.length, 1);
  app.showLogin();
  assert.ok(streams.every(value => value.track.stopped));
});
test('late A permission cannot start recording in B session', async () => {
  const {app, identity, grant, streams, recorders} = setup();
  const pending = app.toggleRecording();
  app.showLogin(); identity(3);
  grant(); await pending;
  assert.equal(recorders.length, 0);
  assert.ok(streams[0].track.stopped);
  assert.equal(app.state.user.user_id, 3);
  assert.equal(app.state.mediaStream, null);
});
test('old permission rejection cannot clear B recording or its controls', async () => {
  const {app, identity, grant, permission, streams, nodes} = setup();
  const old = app.toggleRecording();
  app.showLogin(); identity(3);
  const current = app.toggleRecording(); grant(1); await current;
  const currentRecorder = app.state.recorder;
  permission[0].reject(Object.assign(new Error('Old permission denied'), {name: 'NotAllowedError'})); await old;
  assert.equal(app.state.recorder, currentRecorder);
  assert.equal(currentRecorder.state, 'recording');
  assert.equal(streams[0].track.stopped, false);
  assert.equal(nodes.get('recordButton').textContent, '■ Dừng ghi');
  app.showLogin();
});
test('late old stream cannot replace a newer pending permission request', async () => {
  const {app, identity, grant, streams, nodes} = setup();
  const old = app.toggleRecording();
  app.showLogin(); identity(3);
  const current = app.toggleRecording(); const owner = app.state.recordingRequest;
  grant(0); await old;
  assert.ok(streams[0].track.stopped);
  assert.equal(app.state.recordingRequest, owner);
  assert.equal(nodes.get('recordButton').disabled, true);
  grant(1); await current;
  assert.equal(app.state.recorder.state, 'recording');
  app.showLogin();
});
for (const failure of ['permission', 'constructor', 'start']) {
  test(`${failure} failure preserves the existing preview and enables another try`, async () => {
    const {app, grant, permission, streams, nodes} = setup(failure);
    const saved = {key: 'old-preview'};
    app.state.savedRecording = saved; app.state.currentTranscriptionId = 'draft-1';
    app.state.currentPreviewSha256 = 'a'.repeat(64); nodes.get('answerText').value = 'Existing preview';
    const pending = app.toggleRecording();
    if (failure === 'permission') permission[0].reject(new Error('Denied'));
    else grant();
    await pending;
    assert.equal(app.state.savedRecording, saved);
    assert.equal(app.state.currentTranscriptionId, 'draft-1');
    assert.equal(nodes.get('answerText').value, 'Existing preview');
    assert.equal(app.state.recordingRequest, null);
    assert.equal(nodes.get('recordButton').disabled, false);
    assert.equal(nodes.get('submitAnswerButton').disabled, false);
    assert.ok(streams.every(value => value.track.stopped));
  });
}
test('a changed physical microphone closes the stream and requires a new check', async () => {
  const {app, grant, streams, recorders, nodes} = setup();
  const pending = app.toggleRecording(); grant(0, 'different-mic'); await pending;
  assert.equal(recorders.length, 0);
  assert.ok(streams[0].track.stopped);
  assert.equal(app.state.sessionMicCheck, null);
  assert.equal(nodes.get('recordButton').disabled, true);
});
for (const stoppedSession of ['completed', 'deadline']) {
  test(`the stop button still closes capture after ${stoppedSession}`, async () => {
    const {app, grant, streams, transcriptions} = setup();
    const pending = app.toggleRecording(); grant(); await pending;
    const recorder = app.state.recorder, onstop = recorder.onstop;
    if (stoppedSession === 'completed') app.state.completed = true;
    else app.state.session.recording_allowed = false;
    await app.toggleRecording(); onstop();
    assert.equal(recorder.state, 'inactive');
    assert.ok(streams[0].track.stopped);
    assert.equal(app.state.recorder, null);
    assert.equal(transcriptions.length, 0);
  });
}
test('normal capture keeps the last chunk and hands the right session to transcription once', async () => {
  const {app, grant, permission, transcriptions} = setup();
  const pending = app.toggleRecording(); grant(); await pending;
  assert.equal(permission[0].constraints.audio.deviceId.exact, 'mic-1');
  const recorder = app.state.recorder;
  recorder.ondataavailable({data: {size: 2, tag: 'first'}});
  await app.toggleRecording();
  recorder.ondataavailable({data: {size: 2, tag: 'last'}});
  recorder.onstop();
  assert.equal(transcriptions.length, 1);
  assert.equal(transcriptions[0].sessionId, 'session-2');
  assert.equal(transcriptions[0].chunks.length, 2);
  assert.equal(app.state.recordingRequest, null);
  app.showLogin();
});
test('a queued stop callback from A cannot transcribe under B', async () => {
  const {app, grant, identity, transcriptions, streams} = setup();
  const pending = app.toggleRecording(); grant(); await pending;
  const onstop = app.state.recorder.onstop;
  app.showLogin(); identity(3); onstop();
  assert.equal(transcriptions.length, 0);
  assert.ok(streams[0].track.stopped);
});
test('finishing is blocked while a permission request is still preparing', async () => {
  const {app, grant, nodes} = setup();
  const pending = app.toggleRecording();
  assert.equal(nodes.get('finishPracticeButton').disabled, true);
  await app.finishPractice();
  assert.equal(app.state.completed, false);
  assert.equal(app.state.sessionFinishing, false);
  grant(); await pending; app.showLogin();
});
test('beginning a new session invalidates an older pending microphone open', async () => {
  const {app, grant, streams, recorders} = setup();
  const pending = app.toggleRecording();
  app.beginSession({...app.state.session, session_id: 'new', question: {id: 'new-question', language: 'vi'}});
  grant(); await pending;
  assert.equal(recorders.length, 0);
  assert.ok(streams[0].track.stopped);
  assert.equal(app.state.session.session_id, 'new');
});
