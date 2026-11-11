"use strict";

(function () {
  const config = document.querySelector("[data-insights-config]");
  if (!config) return;
  const user = config.dataset.user;
  const csrf = config.querySelector("[name=csrfmiddlewaretoken]").value;
  let storage;
  try { storage = localStorage; } catch (_) { storage = null; }
  const local = window.PoliSkilledIntents.create(storage);
  const current = { interests: new Set(), follows: new Set() };
  const pendingWrites = new Set();
  let ready = !user;

  function buttons() { return [...document.querySelectorAll("[data-intent-kind]")]; }
  function render() {
    for (const button of buttons()) {
      const { intentKind: kind, intentId: id } = button.dataset;
      const active = user ? current[kind].has(Number(id)) : local.has(kind, id);
      button.setAttribute("aria-pressed", String(active));
      button.textContent = active ? button.dataset.intentSelectedLabel : button.dataset.intentLabel;
      button.disabled = !ready || pendingWrites.has(kind + ":" + id);
    }
  }
  function announce(button, message) {
    const status = button.closest(".intent-control").querySelector("[data-intent-status]");
    if (status) status.textContent = message;
  }
  async function request(url, body) {
    const response = await fetch(url, {
      method: body === undefined ? "GET" : "POST", credentials: "same-origin",
      headers: { "X-CSRFToken": csrf, "X-Poliskilled-User": user,
        ...(typeof body === "string" ? { "Content-Type": "application/json" } : {}) },
      ...(body === undefined ? {} : { body }),
    });
    if (!response.ok) throw new Error("request failed");
    return response.json();
  }
  function accept(data) {
    for (const kind of ["interests", "follows"]) current[kind] = new Set(data[kind]);
  }
  let writes = Promise.resolve();
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-intent-kind]");
    if (!button || !ready) return;
    const { intentKind: kind, intentId: id } = button.dataset;
    const key = kind + ":" + id;
    if (pendingWrites.has(key)) return;
    if (!user) {
      const next = !local.has(kind, id);
      const saved = local.set(kind, id, next);
      announce(button, saved ? (next ? "Salvato in questo browser. Accedi per sincronizzare." : "Preferenza rimossa da questo browser.") : "Il browser non permette il salvataggio. Accedi per salvare nell’account.");
      render();
      return;
    }
    pendingWrites.add(key);
    render();
    const next = !current[kind].has(Number(id));
    writes = writes.then(async () => {
      try {
        await request(button.dataset.intentUrl, new URLSearchParams({ active: String(next) }));
        if (next) current[kind].add(Number(id)); else current[kind].delete(Number(id));
        announce(button, next ? "Salvato nel tuo account." : "Preferenza rimossa.");
      } catch (_) { announce(button, "Salvataggio non riuscito. Ricarica la pagina e riprova."); }
      pendingWrites.delete(key);
      render();
    });
  });
  document.addEventListener("click", (event) => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    const trigger = event.target.closest("[data-node] > a");
    if (!trigger || !trigger.closest("[data-track]")) return;
    const id = trigger.closest("[data-node]").dataset.node;
    if (!/^[1-9]\d*$/.test(id)) return;
    fetch(config.dataset.viewUrl.replace("/0/", "/" + id + "/"), {
      method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": csrf },
    }).catch(() => {});
    render();
  });
  window.addEventListener("storage", () => { if (!user) render(); });
  render();
  if (user) {
    const pending = local.pending();
    const importing = pending.interests.length + pending.follows.length > 0;
    request(importing ? config.dataset.importUrl : config.dataset.stateUrl,
      importing ? JSON.stringify(local.payload(pending)) : undefined).then((data) => {
      accept(data);
      if (importing) {
        const imported = local.clearImported(pending, data.acknowledged);
        if (imported && document.querySelector("[data-saved-intents]")) location.reload();
      }
      ready = true;
      render();
    }).catch(() => {
      for (const button of buttons()) announce(button, "Sincronizzazione non disponibile. Ricarica la pagina.");
    });
  }
})();
