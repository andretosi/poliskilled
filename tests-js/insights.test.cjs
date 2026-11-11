const test = require("node:test");
const assert = require("node:assert/strict");
const { create } = require("../insights/static/insights/intent-storage.js");
const fs = require("node:fs");
const vm = require("node:vm");

function fakeStorage() {
  const values = new Map();
  return {
    get length() { return values.size; },
    key(index) { return [...values.keys()][index]; },
    getItem(key) { return values.get(key) ?? null; },
    setItem(key, value) { values.set(key, value); },
    removeItem(key) { values.delete(key); },
  };
}

test("anonymous intents are separate keys and undo does not erase another preference", () => {
  const store = create(fakeStorage());
  store.set("interests", 1, true);
  store.set("interests", 2, true);
  store.set("follows", 1, true);
  store.set("interests", 1, false);
  assert.deepEqual(store.pending(), { interests: [2], follows: [1] });
});

test("import acknowledgement is idempotent and only clears the submitted snapshot", () => {
  const store = create(fakeStorage());
  store.set("interests", 1, true);
  const snapshot = store.pending();
  store.set("interests", 2, true);
  store.clearImported(snapshot, snapshot);
  store.clearImported(snapshot, snapshot);
  assert.deepEqual(store.pending(), { interests: [2], follows: [] });
});

test("storage denial and malformed identities cannot masquerade as a successful save", () => {
  const denied = create(null);
  assert.equal(denied.set("interests", 1, true), false);
  assert.equal(denied.has("interests", 1), false);
  assert.deepEqual(denied.pending(), { interests: [], follows: [] });
  const store = create(fakeStorage());
  assert.equal(store.set("other", 1, true), false);
  assert.equal(store.set("interests", "1:bad", true), false);
  assert.equal(store.set("interests", "9007199254740993", true), false);
});

test("temporarily private interests remain local without triggering a reload loop", () => {
  const store = create(fakeStorage());
  store.set("interests", 1, true);
  store.set("interests", 2, true);
  const accepted = { interests: [2], follows: [] };
  assert.equal(store.clearImported(store.pending(), accepted), 1);
  assert.deepEqual(store.pending(), { interests: [1], follows: [] });
  assert.equal(store.clearImported(store.pending(), accepted), 0);
  assert.equal(store.clearImported(store.pending(), { interests: [1, 2], follows: [] }), 1);
  assert.deepEqual(store.pending(), { interests: [], follows: [] });
});

test("an old acknowledgement cannot erase the same choice saved again in another tab", () => {
  const storage = fakeStorage();
  const importing = create(storage), guest = create(storage);
  importing.set("interests", 1, true);
  const snapshot = importing.pending();
  guest.set("interests", 1, false);
  guest.set("interests", 1, true);
  assert.equal(importing.clearImported(snapshot, snapshot), 0);
  assert.equal(guest.has("interests", 1), true);
});

test("legacy plain markers can still be imported", () => {
  const storage = fakeStorage();
  storage.setItem("poliskilled:intent:v1:interests:7", "1");
  const store = create(storage);
  const snapshot = store.pending();
  assert.deepEqual(snapshot.interests, [7]);
  assert.equal(store.clearImported(snapshot, snapshot), 1);
});

test("a failed removal retains the choice without requesting a reload", () => {
  const storage = fakeStorage(), store = create(storage);
  store.set("interests", 1, true);
  const snapshot = store.pending();
  storage.removeItem = () => { throw new Error("denied"); };
  assert.equal(store.clearImported(snapshot, snapshot), 0);
  assert.equal(store.has("interests", 1), true);
});

test("a choice added between acknowledgement read and removal keeps its distinct key", () => {
  const storage = fakeStorage(), importing = create(storage), guest = create(storage);
  importing.set("interests", 1, true);
  const snapshot = importing.pending(), remove = storage.removeItem;
  let interleaved = false;
  storage.removeItem = (key) => {
    if (!interleaved) {
      interleaved = true;
      guest.set("interests", 1, true);
    }
    remove(key);
  };
  importing.clearImported(snapshot, snapshot);
  assert.equal(guest.has("interests", 1), true);
});

test("anonymous imports are bounded and do not read unrelated storage", () => {
  const storage = fakeStorage();
  storage.setItem("unrelated", "personal data");
  storage.setItem("poliskilled:intent:v1:follows:5:invalid", "1");
  const store = create(storage);
  for (let id = 1; id <= 220; id += 1) store.set("interests", id, true);
  assert.equal(store.pending().interests.length, 200);
  assert.deepEqual(store.pending().follows, []);
  assert.equal(storage.getItem("unrelated"), "personal data");
});

test("reopening a dialog during a pending save cannot toggle the preference back", async () => {
  const listeners = [], nodes = [], calls = [];
  let finishSave;
  const button = () => ({
    dataset: { intentKind: "interests", intentId: "1", intentUrl: "/interest/1/",
      intentLabel: "Mi interessa", intentSelectedLabel: "Ti interessa" },
    setAttribute(key, value) { this[key] = value; },
    closest(selector) { return selector === "[data-intent-kind]" ? this :
      selector === ".intent-control" ? { querySelector: () => ({}) } : null; },
  });
  const original = button(); nodes.push(original);
  const config = { dataset: { user: "1", stateUrl: "/state/", viewUrl: "/view/0/" },
    querySelector: () => ({ value: "fixture-csrf" }) };
  vm.runInNewContext(fs.readFileSync(require.resolve("../insights/static/insights/insights.js"), "utf8"), {
    document: { querySelector: (s) => s === "[data-insights-config]" ? config : null,
      querySelectorAll: () => nodes, addEventListener: (_, listener) => listeners.push(listener) },
    window: { PoliSkilledIntents: { create }, addEventListener() {} },
    localStorage: fakeStorage(), URLSearchParams,
    fetch: async (url, options) => {
      calls.push([url, options]);
      if (url === "/interest/1/") await new Promise((resolve) => { finishSave = resolve; });
      return { ok: true, json: async () => ({ interests: [], follows: [] }) };
    },
  });
  const settle = () => new Promise((resolve) => setImmediate(resolve));
  const click = (target) => listeners.forEach((listener) => listener({ target, button: 0 }));
  await settle();
  click(original); await settle();
  const clone = button(); nodes.push(clone);
  const node = { dataset: { node: "1" } };
  const trigger = { closest: (selector) => selector === "[data-track]" ? {} : node };
  click({ closest: (selector) => selector === "[data-node] > a" ? trigger : null });
  assert.equal(clone.disabled, true);
  click(clone);
  finishSave(); await settle();
  assert.equal(calls.filter(([url]) => url === "/interest/1/").length, 1);
  assert.equal(clone["aria-pressed"], "true");
  assert.equal(clone.disabled, false);
});
