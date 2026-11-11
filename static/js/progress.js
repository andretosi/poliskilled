"use strict";

window.PoliSkilledProgress = (() => {
  const user = document.body.dataset.user;
  const store = window.createProgressStore(user);
  let completed = user ? store.cache() : store.guest();
  let syncing = false,
    invalidated = false;
  let message = user ? "Sincronizzazione…" : "Salvato su questo browser";
  const snapshot = document.querySelector("#progress-snapshot");
  const rendered = snapshot
    ? store.ids(JSON.parse(snapshot.textContent))
    : null;

  function applyPending() {
    for (const [id, done] of Object.entries(store.pending())) {
      if (done) completed.add(id);
      else completed.delete(id);
    }
  }
  function emit() {
    for (const label of document.querySelectorAll("[data-sync-status]"))
      label.textContent = store.healthy
        ? message
        : "Memoria browser non disponibile: le modifiche locali potrebbero andare perse.";
    for (const button of document.querySelectorAll("[data-progress-toggle]")) {
      if (invalidated) {
        button.hidden = true;
        button.disabled = true;
        continue;
      }
      button.hidden = false;
      const done = completed.has(button.dataset.progressToggle);
      button.textContent = done
        ? "Completata ✓ · Annulla"
        : "Segna completata +";
      button.setAttribute("aria-pressed", String(done));
    }
    document.dispatchEvent(new CustomEvent("poliskilled:progress"));
  }
  async function request(method, data) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(document.body.dataset.progressUrl, {
        method,
        credentials: "same-origin",
        cache: "no-store",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "X-PoliSkilled-User": user,
          "X-CSRFToken": document.querySelector("[data-progress-csrf] input")
            .value,
        },
        ...(data ? { body: JSON.stringify(data) } : {}),
      });
      if (!response.ok && response.status !== 409)
        throw new Error(String(response.status));
      const payload = await response.json();
      if (!response.ok)
        throw new Error(payload.code || String(response.status));
      return payload;
    } finally {
      clearTimeout(timeout);
    }
  }
  function acceptServer(values) {
    completed = store.ids(values);
    store.cacheServer(completed);
    applyPending();
  }
  function invalidateAccount() {
    invalidated = true;
    completed.clear();
    document.querySelector("main")?.replaceChildren();
    document.querySelector(".account-nav")?.replaceChildren();
    emit();
    location.reload();
  }
  async function drain() {
    const attempted = new Set(),
      blocked = {};
    let conflicts = 0;
    let result = await request("GET");
    acceptServer(result.completed);
    while (true) {
      const incoming = [...store.guest()]
        .filter((id) => !attempted.has(id))
        .slice(0, 200);
      const changes = Object.fromEntries(
        Object.entries(store.pending())
          .filter(([id, done]) => blocked[id] !== done)
          .slice(0, 200),
      );
      if (!incoming.length && !Object.keys(changes).length) break;
      try {
        result = await request("POST", {
          import: incoming.map(Number),
          changes,
          revision: result.revision,
        });
      } catch (error) {
        if (error.message !== "progress_conflict" || conflicts++ >= 3)
          throw error;
        result = await request("GET");
        acceptServer(result.completed);
        continue;
      }
      for (const id of incoming) attempted.add(id);
      for (const id of result.imported) store.setGuest(String(id), false);
      const applied = new Set(result.applied.map(String));
      for (const [id, done] of Object.entries(changes)) {
        if (applied.has(id)) store.acknowledge(id, done);
        else blocked[id] = done;
      }
      acceptServer(result.completed);
    }
    message =
      Object.keys(store.pending()).length || store.guest().size
        ? "Una tappa non è più pubblica: spunta conservata su questo browser."
        : "Sincronizzato con il tuo account";
    const server = store.ids(result.completed);
    if (
      rendered &&
      (server.size !== rendered.size ||
        [...server].some((id) => !rendered.has(id)))
    )
      location.reload();
  }
  async function sync() {
    if (invalidated) return;
    if (!user || syncing) {
      emit();
      return;
    }
    if (!navigator.locks) {
      message =
        "Spunte salvate qui. Per sincronizzarle usa un browser aggiornato e il link HTTPS.";
      emit();
      return;
    }
    syncing = true;
    try {
      // One account drain at a time across all tabs; commands are reread inside the lock.
      await navigator.locks.request("ramo:sync:" + user, drain);
    } catch (error) {
      if (["401", "409"].includes(error.message)) invalidateAccount();
      message = ["401", "409"].includes(error.message)
        ? "Account cambiato o sessione scaduta. Ricarica per accedere."
        : error.message === "403"
          ? "Sessione aggiornata: ricarica la pagina per sincronizzare."
          : "Sincronizzazione sospesa. Riproveremo alla prossima connessione.";
    } finally {
      syncing = false;
      emit();
    }
  }
  function set(id, done) {
    if (invalidated) return;
    id = String(id);
    if (user) {
      store.queue(id, done);
      completed = store.cache();
      applyPending();
    } else {
      store.setGuest(id, done);
      completed = store.guest();
    }
    message = user ? "Salvataggio…" : "Salvato su questo browser";
    emit();
    void sync();
  }
  for (const button of document.querySelectorAll("[data-progress-toggle]"))
    button.addEventListener("click", () =>
      set(
        button.dataset.progressToggle,
        !completed.has(button.dataset.progressToggle),
      ),
    );
  window.addEventListener("online", () => void sync());
  window.addEventListener("focus", () => void sync());
  window.addEventListener("storage", (event) => {
    if (invalidated || !event.key?.startsWith("ramo:")) return;
    completed = user ? store.cache() : store.guest();
    if (user) applyPending();
    emit();
    void sync();
  });
  if (user) applyPending();
  emit();
  const ready = sync();
  return { has: (id) => completed.has(String(id)), set, ready };
})();
