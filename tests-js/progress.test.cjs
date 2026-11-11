const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const source = ["progress-storage.js", "progress.js"]
  .map((name) =>
    fs.readFileSync(path.join(__dirname, "../static/js", name), "utf8"),
  )
  .join("\n");
const tick = () => new Promise(setImmediate);

function harness() {
  const storage = new Map(),
    completed = new Set(),
    published = new Set(),
    requests = [];
  const locks = new Map();
  let revision = 0;
  function tab({ user = "1", snapshot = null, unauthorized = false } = {}) {
    const listeners = {},
      status = {},
      location = {
        reloads: 0,
        reload() {
          this.reloads++;
        },
      };
    const window = {
      addEventListener: (name, callback) => {
        listeners[name] = callback;
      },
    };
    const document = {
      body: { dataset: { user, progressUrl: "/api/progress/" } },
      querySelector(selector) {
        if (selector === "#legacy-progress") return { textContent: "{}" };
        if (selector === "#progress-snapshot" && snapshot)
          return { textContent: JSON.stringify(snapshot) };
        if (selector === "[data-progress-csrf] input")
          return { value: "synthetic-test-value" };
        return null;
      },
      querySelectorAll: (selector) =>
        selector === "[data-sync-status]" ? [status] : [],
      dispatchEvent() {},
    };
    const response = (imported = [], applied = []) => ({
      ok: !unauthorized,
      status: unauthorized ? 401 : 200,
      json: async () => ({
        completed: [...completed],
        imported,
        applied,
        revision,
      }),
    });
    vm.runInNewContext(source, {
      window,
      document,
      location,
      CustomEvent: class {},
      AbortController,
      setTimeout,
      clearTimeout,
      navigator: {
        locks: {
          request(name, work) {
            const job = (locks.get(name) || Promise.resolve()).then(work);
            locks.set(
              name,
              job.catch(() => {}),
            );
            return job;
          },
        },
      },
      localStorage: {
        get length() {
          return storage.size;
        },
        key: (index) => [...storage.keys()][index],
        getItem: (key) => storage.get(key) ?? null,
        setItem: (key, value) => storage.set(key, value),
        removeItem: (key) => storage.delete(key),
      },
      fetch(_, options) {
        if (options.method === "GET") return Promise.resolve(response());
        const data = JSON.parse(options.body);
        return new Promise((resolve, reject) =>
          requests.push({
            data,
            abort() {
              reject(new Error("AbortError"));
            },
            finish() {
              if (data.revision !== revision) {
                resolve({
                  ok: false,
                  status: 409,
                  json: async () => ({ code: "progress_conflict" }),
                });
                return;
              }
              revision++;
              const imported = data.import
                .map(String)
                .filter((id) => published.has(id));
              const applied = [];
              for (const id of imported) completed.add(id);
              for (const [id, done] of Object.entries(data.changes)) {
                if (done && !published.has(id)) continue;
                if (done) completed.add(id);
                else completed.delete(id);
                applied.push(id);
              }
              resolve(response(imported, applied));
            },
          }),
        );
      },
    });
    return { progress: window.PoliSkilledProgress, listeners, status, location };
  }
  return { storage, completed, published, requests, tab };
}

test("two tabs serialize account sync and preserve the latest undo", async () => {
  const h = harness();
  h.published.add("1");
  const a = h.tab(),
    b = h.tab();
  await Promise.all([a.progress.ready, b.progress.ready]);
  a.progress.set("1", true);
  await tick();
  b.listeners.storage({ key: "ramo:user:1:pending:1" });
  b.progress.set("1", false);
  await tick();
  assert.equal(h.requests.length, 1);
  h.requests[0].finish();
  await tick();
  assert.deepEqual(h.requests[1].data.changes, { 1: false });
  h.requests[1].finish();
  await tick();
  await tick();
  assert.equal(h.requests.length, 2);
  assert.equal(h.completed.has("1"), false);
  assert.equal(h.storage.has("ramo:user:1:pending:1"), false);
});

test("anonymous activity writes from different tabs do not overwrite each other", async () => {
  const h = harness(),
    a = h.tab({ user: "" }),
    b = h.tab({ user: "" });
  a.progress.set("7", true);
  b.progress.set("8", true);
  a.listeners.storage({ key: "ramo:guest:v3:8" });
  assert.equal(a.progress.has("7") && a.progress.has("8"), true);
  assert.equal(b.progress.has("7") && b.progress.has("8"), true);
});

test("temporarily private completion stays pending until it is public again", async () => {
  const h = harness(),
    a = h.tab();
  await a.progress.ready;
  a.progress.set("1", true);
  await tick();
  h.requests[0].finish();
  await tick();
  assert.equal(h.storage.get("ramo:user:1:pending:1"), "1");
  assert.equal(a.progress.has("1"), true);
  assert.equal(h.requests.length, 1);
  h.published.add("1");
  a.listeners.focus();
  await tick();
  h.requests[1].finish();
  await tick();
  assert.equal(h.completed.has("1"), true);
  assert.equal(h.storage.has("ramo:user:1:pending:1"), false);
});

test("rejected imports do not starve later batches", async () => {
  const h = harness();
  h.storage.set(
    "ramo:guest-progress:v2",
    JSON.stringify(Array.from({ length: 201 }, (_, i) => i + 1)),
  );
  h.published.add("201");
  const a = h.tab();
  await tick();
  assert.equal(h.requests[0].data.import.length, 200);
  h.requests[0].finish();
  await tick();
  assert.deepEqual(h.requests[1].data.import, [201]);
  h.requests[1].finish();
  await a.progress.ready;
  assert.equal(h.completed.has("201"), true);
  assert.equal(h.storage.get("ramo:guest:v3:1"), "1");
  assert.equal(h.storage.get("ramo:guest:v3:201"), "0");
});

test("progress page refreshes after queued completion and undo, without looping", async () => {
  for (const done of [true, false]) {
    const h = harness();
    h.published.add("1");
    if (!done) h.completed.add("1");
    h.storage.set("ramo:user:1:pending:1", done ? "1" : "0");
    const a = h.tab({ snapshot: done ? [] : [1] });
    await tick();
    h.requests[0].finish();
    await a.progress.ready;
    assert.equal(a.location.reloads, 1);
    const b = h.tab({ snapshot: done ? [1] : [] });
    await b.progress.ready;
    assert.equal(b.location.reloads, 0);
  }
});

test("expired authentication reloads the page instead of retaining stale account controls", async () => {
  const h = harness(),
    a = h.tab({ unauthorized: true });
  await a.progress.ready;
  assert.equal(a.location.reloads, 1);
  assert.equal(h.requests.length, 0);
  a.progress.set("1", true);
  assert.equal(a.progress.has("1"), false);
  assert.equal(h.storage.has("ramo:user:1:pending:1"), false);
});

test("a timed-out POST that reaches the server late cannot resurrect an acknowledged undo", async () => {
  const h = harness();
  h.published.add("1");
  const a = h.tab(),
    b = h.tab();
  await Promise.all([a.progress.ready, b.progress.ready]);
  a.progress.set("1", true);
  await tick();
  h.requests[0].abort();
  await tick();
  b.progress.set("1", false);
  await tick();
  h.requests[1].finish();
  await tick();
  assert.equal(h.completed.has("1"), false);
  h.requests[0].finish();
  await tick();
  assert.equal(h.completed.has("1"), false);
  assert.equal(h.storage.has("ramo:user:1:pending:1"), false);
});
