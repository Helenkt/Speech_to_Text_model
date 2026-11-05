// Production authentication logic with controlled fetch responses; no live HTTP or microphone.
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const test = require("node:test");
const source = fs.readFileSync(process.argv[2], "utf8");
const fixture = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

function classes() {
  const values = new Set();
  return {add(...xs) {xs.forEach(x => values.add(x));}, remove(...xs) {xs.forEach(x => values.delete(x));},
    contains(x) {return values.has(x);}, toggle(x, force) {if (force ?? !values.has(x)) values.add(x); else values.delete(x);}};
}
function response(status, body) {
  return {status, ok: status >= 200 && status < 300, headers: {get() {return "application/json";}}, async json() {return body;}};
}
function setup() {
  const nodes = new Map(fixture.ids.map(id => [id, {id, textContent: "", innerHTML: "", value: "", open: false,
    classList: classes(), dataset: {}, style: {}, setAttribute() {}, removeAttribute() {}, pause() {}, focus() {},
    querySelectorAll() {return [];}, close() {this.open = false;}, showModal() {this.open = true;}}]));
  const context = vm.createContext({document: {body: {classList: classes()}, addEventListener() {},
    querySelectorAll(selector) {return selector === "[id]" ? [...nodes.values()] : [];}},
    navigator: {}, window: {scrollTo() {}}, console, setTimeout: fn => setTimeout(fn, 0), clearTimeout,
    localStorage: {getItem() {return null;}}, fetch: async () => response(200, {})});
  vm.runInContext(source + "\nglobalThis.audit = {state, api, initialize, login, logout, showLogin, enterApp," +
    "setFetch(fn) {globalThis.fetch = fn;}, prepare() {bindEvents = () => {}; applySummary = () => {};}};", context);
  const app = context.audit;
  app.prepare();
  return {app, nodes};
}
const user = id => ({user_id: id, role: "candidate", full_name: `Student ${id}`});
function recording(app) {
  const probe = {stopped: false};
  app.state.user = user(3);
  app.state.recorder = {state: "recording", onstop() {}, stop() {probe.stopped = true;}};
  return probe;
}
const event = () => ({preventDefault() {}});
const otherResponse = path => response(200, path === "/api/health" ? {question_generation: {}} : {languages: []});

test("stale API 401 cannot log the next student out or stop their recording", async () => {
  const {app} = setup();
  app.state.user = user(2);
  let release;
  app.setFetch(path => path === "/api/auth/logout" ? Promise.resolve(response(200, {}))
    : new Promise(resolve => {release = resolve;}));
  const pending = app.api("/api/interviews/old/report").catch(error => error);
  await app.logout();
  const probe = recording(app);
  release(response(401, {detail: "expired old session"}));
  assert.equal((await pending).status, 401);
  assert.equal(app.state.user.user_id, 3);
  assert.equal(probe.stopped, false);
});

for (const status of [200, 401]) {
  test(`stale initialization ${status} cannot replace a newer identity`, async () => {
    const {app} = setup();
    let release;
    app.setFetch(path => path === "/api/auth/me" ? new Promise(resolve => {release = resolve;}) : Promise.resolve(otherResponse(path)));
    const pending = app.initialize();
    const probe = recording(app);
    release(response(status, status === 200 ? {user: user(2)} : {}));
    await pending;
    assert.equal(app.state.user.user_id, 3);
    assert.equal(probe.stopped, false);
  });
}

test("initialization rechecks identity after waiting for its JSON body", async () => {
  const {app} = setup();
  let release;
  app.setFetch(async () => ({ok: true, json() {return new Promise(resolve => {release = resolve;});}}));
  const pending = app.initialize();
  await new Promise(resolve => setImmediate(resolve));
  recording(app);
  release({user: user(2)});
  await pending;
  assert.equal(app.state.user.user_id, 3);
});

test("a pending login invalidates startup auth even before its new user is known", async () => {
  const {app} = setup();
  let me, signedIn;
  app.setFetch(path => path === "/api/auth/me" ? new Promise(resolve => {me = resolve;})
    : path === "/api/auth/login" ? new Promise(resolve => {signedIn = resolve;}) : Promise.resolve(otherResponse(path)));
  const initial = app.initialize();
  const pending = app.login(event());
  me(response(200, {user: user(2)}));
  await initial;
  assert.equal(app.state.user, null);
  signedIn(response(200, {user: user(3)}));
  await pending;
  assert.equal(app.state.user.user_id, 3);
});

test("an earlier anonymous 401 cannot cancel a pending login", async () => {
  const {app, nodes} = setup();
  let old, signedIn;
  app.setFetch(path => path === "/api/old" ? new Promise(resolve => {old = resolve;})
    : path === "/api/auth/login" ? new Promise(resolve => {signedIn = resolve;}) : Promise.resolve(otherResponse(path)));
  const prior = app.api("/api/old").catch(error => error);
  const pending = app.login(event());
  old(response(401, {detail: "old anonymous check"}));
  await prior;
  assert.equal(nodes.get("loginButton").disabled, true);
  signedIn(response(200, {user: user(3)}));
  await pending;
  assert.equal(app.state.user.user_id, 3);
});

test("only the latest login response can choose the identity or reset the login form", async () => {
  const {app, nodes} = setup();
  const pendingResponses = [];
  app.setFetch(path => path === "/api/auth/login" ? new Promise(resolve => pendingResponses.push(resolve)) : Promise.resolve(otherResponse(path)));
  const older = app.login(event());
  const newer = app.login(event());
  pendingResponses[0](response(200, {user: user(2)}));
  await older;
  assert.equal(app.state.user, null);
  assert.equal(nodes.get("loginButton").disabled, true);
  pendingResponses[1](response(200, {user: user(3)}));
  await newer;
  assert.equal(app.state.user.user_id, 3);
  assert.equal(nodes.get("loginButton").disabled, false);
});

test("a stale logout callback cannot sign a newer identity out", async () => {
  const {app} = setup();
  app.state.user = user(2);
  let release;
  app.setFetch(path => path === "/api/auth/logout" ? new Promise(resolve => {release = resolve;})
    : Promise.resolve(path === "/api/auth/login" ? response(200, {user: user(3)}) : otherResponse(path)));
  const leaving = app.logout();
  await app.login(event());
  recording(app);
  release(response(200, {}));
  await leaving;
  assert.equal(app.state.user.user_id, 3);
});

test("a current 401 signs its owner out and leaves the login button usable", async () => {
  const {app, nodes} = setup();
  app.state.user = user(2);
  nodes.get("loginButton").disabled = true;
  app.setFetch(async () => response(401, {detail: "expired"}));
  await app.api("/api/health").catch(() => {});
  assert.equal(app.state.user, null);
  assert.equal(nodes.get("loginButton").disabled, false);
});

test("fresh initialization restores the authenticated user", async () => {
  const {app} = setup();
  app.setFetch(async path => path === "/api/auth/me" ? response(200, {user: user(2)}) : otherResponse(path));
  await app.initialize();
  assert.equal(app.state.user.user_id, 2);
});

test("an immediate session expiry after login leaves a usable login form", async () => {
  const {app, nodes} = setup();
  app.setFetch(async path => path === "/api/auth/login" ? response(200, {user: user(2)})
    : path === "/api/health" ? response(401, {detail: "session expired"}) : otherResponse(path));
  await app.login(event());
  assert.equal(app.state.user, null);
  assert.equal(nodes.get("loginButton").disabled, false);
  assert.equal(nodes.get("loginButton").textContent, "Đăng nhập");
});
