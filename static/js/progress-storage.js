"use strict";
// Keep the original local-storage keys so existing progress survives the rebrand.

window.createProgressStore = (user) => {
  const guestPrefix = "ramo:guest:v3:";
  const accountKey = "ramo:user:" + user;
  const pendingPrefix = accountKey + ":pending:";
  const memory = new Map(),
    dirty = new Set();
  let healthy = true;
  const ids = (value) =>
    new Set(
      Array.isArray(value)
        ? value.map(String).filter((id) => /^[1-9]\d{0,15}$/.test(id))
        : [],
    );
  function read(key) {
    if (dirty.has(key)) return memory.get(key) ?? null;
    try {
      return localStorage.getItem(key);
    } catch {
      healthy = false;
      return memory.get(key) ?? null;
    }
  }
  function write(key, value) {
    memory.set(key, value);
    try {
      if (value === null) localStorage.removeItem(key);
      else localStorage.setItem(key, value);
      dirty.delete(key);
      return true;
    } catch {
      healthy = false;
      dirty.add(key);
      return false;
    }
  }
  function json(key, fallback) {
    try {
      return JSON.parse(read(key)) ?? fallback;
    } catch {
      return fallback;
    }
  }
  function entries(prefix) {
    const keys = new Set(memory.keys());
    try {
      for (let index = 0; index < localStorage.length; index++)
        keys.add(localStorage.key(index));
    } catch {
      healthy = false;
    }
    return [...keys]
      .filter((key) => key?.startsWith(prefix))
      .map((key) => [key.slice(prefix.length), read(key)])
      .filter(
        ([id, value]) =>
          /^[1-9]\d{0,15}$/.test(id) && ["0", "1"].includes(value),
      );
  }
  function importGuest(values) {
    let saved = true;
    for (const id of ids(values)) {
      // A tombstone keeps a previously undone activity undone during concurrent upgrades.
      if (read(guestPrefix + id) === null)
        saved = write(guestPrefix + id, "1") && saved;
    }
    return saved;
  }
  const v2 = "ramo:guest-progress:v2";
  if (importGuest(json(v2, []))) write(v2, null);
  const legacy = JSON.parse(
    document.querySelector("#legacy-progress").textContent,
  );
  for (const [slug, steps] of Object.entries(legacy)) {
    const key = "ramo:track:" + slug,
      old = ids(json(key, []));
    for (const entry of steps) {
      if (old.has(String(entry.step)) && importGuest([entry.activity]))
        old.delete(String(entry.step));
    }
    write(key, JSON.stringify([...old]));
  }
  // Upgrade the short-lived v2 per-account queue without overwriting newer commands.
  if (user) {
    const oldKey = accountKey + ":pending",
      old = json(oldKey, {});
    if (old && typeof old === "object" && !Array.isArray(old)) {
      let saved = true;
      for (const [id, done] of Object.entries(old)) {
        if (
          /^[1-9]\d{0,15}$/.test(id) &&
          typeof done === "boolean" &&
          read(pendingPrefix + id) === null
        )
          saved = write(pendingPrefix + id, done ? "1" : "0") && saved;
      }
      if (saved) write(oldKey, null);
    }
  }
  return {
    ids,
    get healthy() {
      return healthy;
    },
    guest: () =>
      new Set(
        entries(guestPrefix)
          .filter(([, value]) => value === "1")
          .map(([id]) => id),
      ),
    setGuest: (id, done) => write(guestPrefix + id, done ? "1" : "0"),
    pending: () =>
      Object.fromEntries(
        entries(pendingPrefix).map(([id, value]) => [id, value === "1"]),
      ),
    queue: (id, done) => write(pendingPrefix + id, done ? "1" : "0"),
    acknowledge(id, done) {
      if (read(pendingPrefix + id) === (done ? "1" : "0"))
        write(pendingPrefix + id, null);
    },
    cache: () => ids(json(accountKey, [])),
    cacheServer: (values) => write(accountKey, JSON.stringify([...values])),
  };
};
