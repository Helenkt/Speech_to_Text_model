// Production async speech workflows with controlled DOM/cache/network and no live microphone.
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
const flush = () => new Promise(resolve => setImmediate(resolve));
function setup() {
  const nodes = new Map(fixture.ids.map(id => [id, {id, value: '', textContent: '', innerHTML: '', open: false,
    disabled: false, classList: classes(), dataset: {}, style: {}, querySelectorAll() {return [];}, focus() {}, pause() {},
    setAttribute() {}, removeAttribute() {}, replaceChildren() {}, dispatchEvent() {}, close() {this.open = false;}}]));
  const contexts = [], opens = [], cacheWrites = [], cacheDeletes = [], tracks = [], renderedMic = [];
  let now = 0, closed = 0;
  class AudioContext {
    constructor() {this.state = 'suspended'; contexts.push(this);}
    resume() {return new Promise(resolve => {this.release = () => {this.state = 'running'; resolve();};});}
    async close() {this.state = 'closed';}
  }
  class Recorder {
    static isTypeSupported() {return true;}
    constructor() {this.state = 'inactive'; this.mimeType = 'audio/webm';}
    start() {this.state = 'recording';}
    stop() {this.state = 'inactive'; queueMicrotask(() => this.onstop?.());}
  }
  const stream = () => {
    const track = {stopped: false, stop() {this.stopped = true;}, getSettings() {return {deviceId: 'mic-1'};}};
    tracks.push(track);
    return {getTracks() {return [track];}, getAudioTracks() {return [track];}};
  };
  const indexedDB = {open() {
    const request = {result: {close() {closed++;}, transaction() {
      const tx = {objectStore() {return {
        put(value) {cacheWrites.push(value); return {result: value.key};},
        delete(key) {cacheDeletes.push(key); return {result: undefined};},
        get() {return {result: null};},
      };}};
      queueMicrotask(() => tx.oncomplete?.()); return tx;
    }}};
    opens.push(request); return request;
  }};
  const context = vm.createContext({document: {body: {classList: classes()}, addEventListener() {},
    querySelectorAll(selector) {return selector === '[id]' ? [...nodes.values()] : [];}},
    window: {AudioContext, scrollTo() {}}, navigator: {mediaDevices: {async getUserMedia() {return stream();}}},
    MediaRecorder: Recorder, AbortController, DOMException, Blob, FormData, Event, indexedDB,
    crypto: {randomUUID() {return '11111111-1111-4111-8111-111111111111';}},
    performance: {now() {return now += 13000;}}, console, setTimeout, clearTimeout, setInterval, clearInterval});
  vm.runInContext(source + '\nglobalThis.audit = {state, checkMicrophone, restoreRecording, processSavedRecording, transcribeRecording,' +
    'recordingCache, showLogin, beginSession, setCache(fn) {recordingCache = fn;}, setSpeech(fn) {speechApi = fn;},' +
    'setProcessor(fn) {processSavedRecording = fn;}, setApi(fn) {api = fn;}, prepare(fn) {' +
    'renderQuestion = () => {}; pinTestMicrophone = async () => {}; startMicLevelMeter = () => () => {};' +
    'measureAmbientNoise = async () => ({dbfs: -50}); renderMicrophoneResult = fn;}};', context);
  const app = context.audit;
  app.prepare(value => renderedMic.push(value));
  app.setApi(async () => ({ready: true}));
  function identity(id = 2) {
    app.state.user = {user_id: id, full_name: `Student ${id}`, role: 'candidate'};
    app.state.session = {session_id: `session-${id}`, interview_mode: 'practice', language: 'vi',
      grading_strategy: 'end_of_session', requested_count: 2, answered_count: 0,
      question: {id: `q-${id}`, language: 'vi'}};
    app.state.currentQuestion = app.state.session.question;
    app.state.health = {speech_to_text: {installed: true, ready: true}};
    app.state.selectedMicrophoneId = 'mic-1'; app.state.completed = false; app.state.draftLoading = false;
    app.state.sessionMicCheck = {ready: true, baselineDbfs: -50, deviceId: 'mic-1'};
  }
  const saved = (id = 2) => ({key: `${id}:session-${id}`, sessionId: `session-${id}`, questionKey: `vi:q-${id}`,
    requestKey: '11111111-1111-4111-8111-111111111111', filename: 'answer.webm', blob: new Blob(['audio']), jobId: null});
  identity();
  return {app, nodes, contexts, opens, cacheWrites, cacheDeletes, tracks, renderedMic, identity, saved, closed: () => closed};
}
test('a cancelled old microphone check must not unlock controls of the new owner', async () => {
  const {app, nodes, contexts, identity} = setup(); app.state.sessionMicCheck = null;
  const pending = app.checkMicrophone();
  app.showLogin(); identity(3);
  for (const id of ['finishPracticeButton', 'checkMicrophoneButton', 'microphoneSelect']) nodes.get(id).disabled = true;
  contexts[0].release(); await pending;
  for (const id of ['finishPracticeButton', 'checkMicrophoneButton', 'microphoneSelect']) assert.equal(nodes.get(id).disabled, true);
});
test('B can start a mic check while a cancelled A audio context is still pending', async () => {
  const {app, contexts, identity} = setup(); app.state.sessionMicCheck = null;
  const old = app.checkMicrophone();
  app.showLogin(); identity(3); app.state.sessionMicCheck = null;
  const current = app.checkMicrophone();
  const count = contexts.length;
  app.state.micTestController?.abort();
  contexts.forEach(value => value.release());
  await Promise.all([old, current]);
  assert.equal(count, 2);
});
test('an older restore cannot clear the loading lock of a newer restore', async () => {
  const {app} = setup(); const cache = [];
  app.setCache(() => new Promise(resolve => cache.push(resolve)));
  app.setSpeech(async path => path.endsWith('/draft') ? {can_record: true, draft: null} : {job: null});
  const old = app.restoreRecording(), current = app.restoreRecording();
  cache[0](null); await old;
  const loading = app.state.draftLoading;
  cache[1](null); await current;
  assert.equal(loading, true);
  assert.equal(app.state.draftLoading, false);
});
test('a draft response returned in reverse order cannot replace a newer preview', async () => {
  const {app, nodes} = setup(); const responses = [];
  app.setCache(async () => null);
  app.setSpeech(() => new Promise(resolve => responses.push(resolve)));
  const old = app.restoreRecording(); await flush();
  const current = app.restoreRecording(); await flush();
  const result = label => ({can_record: true, can_confirm: true, draft: {transcription_id: label,
    preview_sha256: label, text: label, audio_saved: true, stage: 'draft'}});
  responses[1](result('new')); await current;
  responses[0](result('old')); await old;
  assert.equal(nodes.get('answerText').value, 'new');
  assert.equal(app.state.currentTranscriptionId, 'new');
});
test('a completed old upload must not recreate A local cache after logout', async () => {
  const {app, saved, identity} = setup(); const writes = []; let release;
  app.state.savedRecording = saved();
  app.setCache(async (action, value) => {if (action === 'put') writes.push(value);});
  app.setSpeech(() => new Promise(resolve => {release = resolve;}));
  const pending = app.processSavedRecording();
  app.showLogin(); identity(3);
  release({job_id: 'old-job', state: 'completed', audio_saved: true, result: {text: 'A'}}); await pending;
  assert.equal(writes.length, 0);
});
test('an IndexedDB put that opens late must not write an obsolete owner recording', async () => {
  const {app, saved, identity, opens, cacheWrites, closed} = setup();
  const pending = app.recordingCache('put', saved());
  app.showLogin(); identity(3);
  opens[0].onsuccess(); await pending;
  assert.equal(cacheWrites.length, 0);
  assert.equal(closed(), 1);
});
test('old post-recording cache completion cannot start processing B saved audio', async () => {
  const {app, identity, saved} = setup(); let release; const processed = [];
  app.state.recorder = {state: 'inactive', mimeType: 'audio/webm'};
  app.state.audioChunks = [new Blob(['audio'])];
  app.setCache(() => new Promise(resolve => {release = resolve;}));
  app.setProcessor(async () => processed.push(app.state.user.user_id));
  const pending = app.transcribeRecording();
  app.showLogin(); identity(3); app.state.savedRecording = saved(3);
  release(); await pending;
  assert.equal(processed.length, 0);
});
test('current mic check can still complete and release its controls', async () => {
  const {app, contexts, nodes, renderedMic} = setup(); app.state.sessionMicCheck = null;
  const pending = app.checkMicrophone(); contexts[0].release(); await pending;
  assert.equal(app.state.sessionMicCheck.ready, true);
  assert.equal(renderedMic.length, 1);
  assert.equal(nodes.get('checkMicrophoneButton').disabled, false);
  assert.equal(app.state.micTestController, null);
});
test('a current raw recording is cached then handed to processing once', async () => {
  const {app} = setup(); const writes = [], processed = [];
  app.state.recorder = {state: 'inactive', mimeType: 'audio/webm'};
  app.state.audioChunks = [new Blob(['audio'])];
  app.setCache(async (action, value) => writes.push({action, value}));
  app.setProcessor(async () => processed.push(app.state.savedRecording));
  await app.transcribeRecording();
  assert.equal(writes.length, 1); assert.equal(processed.length, 1);
  assert.equal(writes[0].value, processed[0]);
  assert.equal(app.state.recorder, null);
});
test('restore can hand off to processing and still release its own loading lock', async () => {
  const {app, saved, nodes} = setup(); const value = {...saved(), jobId: 'current-job'};
  app.setCache(async () => value);
  app.setSpeech(async path => path.endsWith('/draft') ? {can_record: true, recording_in_progress: true}
    : {job_id: 'current-job', state: 'completed', audio_saved: true,
      result: {text: 'Recovered', transcription_id: 'draft', preview_sha256: 'hash', answer_stage: 'draft'}});
  await app.restoreRecording();
  assert.equal(app.state.draftLoading, false);
  assert.equal(app.state.speechBusy, false);
  assert.equal(nodes.get('answerText').value, 'Recovered');
  assert.equal(nodes.get('recordButton').disabled, false);
});
test('a current native cache put works and explicit old-key cleanup remains possible', async () => {
  const {app, saved, opens, cacheWrites, cacheDeletes, identity} = setup(); const value = saved();
  const put = app.recordingCache('put', value); opens[0].onsuccess(); await put;
  assert.equal(cacheWrites.length, 1);
  assert.equal(cacheWrites[0], value);
  app.showLogin(); identity(3);
  const remove = app.recordingCache('delete', value); opens[1].onsuccess(); await remove;
  assert.equal(cacheDeletes[0], value.key);
});
test('an old failed job response cannot trigger a retry POST under the newer account', async () => {
  const {app, saved, identity} = setup(); let release; const requests = [];
  app.state.savedRecording = {...saved(), jobId: 'old-job'};
  app.setCache(async () => null);
  app.setSpeech(path => {requests.push(path); return new Promise(resolve => {release = resolve;});});
  const pending = app.processSavedRecording();
  app.showLogin(); identity(3);
  release({state: 'failed', retryable: true}); await pending;
  assert.equal(requests.length, 1);
});
test('restore does not compete with an opening microphone', async () => {
  const {app} = setup(); let reads = 0;
  app.state.recordingRequest = {opening: true};
  app.setCache(async () => {reads++; return null;});
  await app.restoreRecording();
  assert.equal(reads, 0);
  assert.equal(app.state.draftLoading, false);
});
test('cancelling the current mic check restores only its current controls', async () => {
  const {app, contexts, nodes} = setup(); app.state.sessionMicCheck = null;
  const pending = app.checkMicrophone();
  app.state.micTestController.abort(); contexts[0].release(); await pending;
  assert.equal(app.state.micTestController, null);
  assert.equal(nodes.get('checkMicrophoneButton').disabled, false);
  assert.equal(nodes.get('recordButton').disabled, true);
});
test('a late mic-analysis response cannot replace the newer baseline', async () => {
  const {app, contexts, identity, nodes} = setup(); let release;
  app.state.sessionMicCheck = null;
  app.setApi(() => new Promise(resolve => {release = resolve;}));
  const pending = app.checkMicrophone(); contexts[0].release();
  for (let i = 0; i < 10 && !release; i++) await flush();
  assert.ok(release);
  app.showLogin();
  assert.equal(nodes.get('finishMicTestButton').onclick, null);
  identity(3); const current = app.state.sessionMicCheck;
  const newHandler = () => {};
  nodes.get('finishMicTestButton').onclick = newHandler;
  release({ready: false}); await pending;
  assert.equal(app.state.sessionMicCheck, current);
  assert.equal(nodes.get('finishMicTestButton').onclick, newHandler);
});
test('a foreign local recording cannot be put using the current owner context', async () => {
  const {app, saved, opens, identity} = setup(); const old = saved(); identity(3);
  await app.recordingCache('put', old);
  assert.equal(opens.length, 0);
});
test('unavailable optional local cache does not block uploading the current voice', async () => {
  const {app} = setup(); let processed = 0;
  app.state.recorder = {state: 'inactive', mimeType: 'audio/webm'};
  app.state.audioChunks = [new Blob(['audio'])];
  app.setCache(async () => {throw new Error('Storage unavailable');});
  app.setProcessor(async () => {processed++;});
  await app.transcribeRecording();
  assert.equal(processed, 1);
  assert.equal(app.state.recorder, null);
});
