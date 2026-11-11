"use strict";

(function (root) {
  const prefix = "poliskilled:intent:v1:";
  const kinds = ["interests", "follows"];
  function create(storage) {
    const snapshots = new WeakMap();
    const valid = (kind, id) => kinds.includes(kind) && /^[1-9]\d*$/.test(String(id))
      && Number.isSafeInteger(Number(id));
    const base = (kind, id) => prefix + kind + ":" + id;
    function entries() {
      const found = [];
      for (let index = 0; index < storage.length; index += 1) {
        const key = storage.key(index);
        if (!key || !key.startsWith(prefix)) continue;
        const [kind, id, version, ...extra] = key.slice(prefix.length).split(":");
        if (!valid(kind, id) || extra.length || (version && !/^\d+-[0-9a-f]+$/.test(version))) continue;
        const value = storage.getItem(key);
        if (value !== "1" && !(typeof value === "string" && value.startsWith("1:"))) continue;
        found.push({ key, kind, id: Number(id), marker: version ? "v2:" + version : value });
      }
      return found;
    }
    return {
      has(kind, id) {
        try { return valid(kind, id) && entries().some((item) => item.kind === kind && item.id === Number(id)); }
        catch (_) { return false; }
      },
      set(kind, id, active) {
        if (!valid(kind, id)) return false;
        try {
          const previous = entries().filter((item) => item.kind === kind && item.id === Number(id));
          if (active) storage.setItem(base(kind, id) + ":" + Date.now() + "-" + Math.random().toString(16).slice(2), "1");
          for (const item of previous) storage.removeItem(item.key);
          return true;
        } catch (_) { return false; }
      },
      pending() {
        const result = { interests: [], follows: [] }, captured = new Map();
        snapshots.set(result, captured);
        try {
          for (const item of entries()) {
            const key = base(item.kind, item.id);
            if (!captured.has(key)) {
              if (result[item.kind].length >= 200) continue;
              captured.set(key, []);
              result[item.kind].push(item.id);
            }
            captured.get(key).push(item);
          }
        } catch (_) { /* The UI explains denied storage when a save is attempted. */ }
        return result;
      },
      payload(snapshot) {
        const markers = { interests: {}, follows: {} }, captured = snapshots.get(snapshot);
        for (const kind of kinds)
          for (const id of snapshot[kind]) markers[kind][id] = captured.get(base(kind, id)).map((item) => item.marker).sort().at(-1);
        return { ...snapshot, markers };
      },
      clearImported(snapshot, accepted) {
        let removed = 0;
        const captured = snapshots.get(snapshot);
        if (!captured) return removed;
        try {
          for (const kind of kinds)
            for (const id of snapshot[kind])
              if (accepted[kind].includes(id))
                for (const item of captured.get(base(kind, id))) {
                  const existed = storage.getItem(item.key) !== null;
                  // A new choice has its own key, even if another tab writes here.
                  storage.removeItem(item.key);
                  if (existed) removed += 1;
                }
        } catch (_) { /* Retry retained keys when storage becomes available. */ }
        return removed;
      },
    };
  }
  if (typeof module !== "undefined" && module.exports) module.exports = { create };
  else root.PoliSkilledIntents = { create };
})(typeof window !== "undefined" ? window : globalThis);
