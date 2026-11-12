"use strict";

const interestFilter = document.querySelector("[data-auto-filter]");
if (interestFilter) {
  interestFilter.addEventListener("change", () => {
    const form = interestFilter.form;
    form.requestSubmit(form.querySelector("[data-search-submit]"));
  });
}

const map = document.querySelector("[data-track]");
if (map) {
  const progress = window.PoliSkilledProgress;
  const nodes = [...map.querySelectorAll("[data-node]")];
  const known = new Set(nodes.map((node) => node.dataset.node));
  const announce = document.querySelector("[data-progress-message]");
  const dialog = document.querySelector(".skill-dialog");
  const complete = dialog.querySelector(".complete-node");
  let selected = null;

  function renderProgress() {
    // Preserve hidden steps while moderation temporarily removes them from the map.
    const count = [...known].filter((id) => progress.has(id)).length;
    for (const node of nodes) {
      const done = progress.has(node.dataset.node);
      node.classList.toggle("is-complete", done);
      node.querySelector(".node-rank").textContent = done ? "1 / 1" : "0 / 1";
      node
        .querySelector("a")
        .setAttribute(
          "aria-label",
          node.dataset.title + (done ? ", completata" : ", da esplorare") +
            (!done && node.dataset.reopening === "true" ? ", riapertura da verificare" : ""),
        );
    }
    map.querySelector("[data-progress-number]").firstChild.textContent =
      String(count).padStart(2, "0") + " ";
    map.querySelector("[data-progress-number] span").textContent =
      "/ " + String(nodes.length).padStart(2, "0");
    map.querySelector("[data-progress-count]").textContent =
      count + " di " + nodes.length + " tappe completate";
    map.querySelector("progress").value = nodes.length
      ? (count / nodes.length) * 100
      : 0;
    if (selected) {
      const done = progress.has(selected.dataset.node);
      complete.textContent = done
        ? "Completata ✓ · Annulla"
        : "Segna completata +";
      complete.setAttribute("aria-pressed", String(done));
    }
    drawConnections();
  }
  for (const node of nodes) {
    node.querySelector("a").addEventListener("click", (event) => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
        return;
      event.preventDefault();
      selected = node;
      for (const other of nodes)
        other.classList.toggle("is-selected", other === node);
      dialog
        .querySelector("[data-node-detail]")
        .replaceChildren(
          node.querySelector("template").content.cloneNode(true),
        );
      renderProgress();
      dialog.showModal();
    });
  }
  complete.addEventListener("click", () => {
    if (!selected) return;
    const id = selected.dataset.node;
    progress.set(id, !progress.has(id));
    renderProgress();
    announce.textContent = progress.has(id)
      ? "Tappa completata: " + selected.dataset.title
      : "Tappa da esplorare: " + selected.dataset.title;
    dialog.close();
  });
  map.querySelector(".reset-progress").addEventListener("click", () => {
    for (const id of known) progress.set(id, false);
    renderProgress();
    announce.textContent = "Progressi del percorso azzerati.";
  });

  const canvas = map.querySelector(".tree-canvas");
  let frame = null;
  function drawConnections() {
    if (frame !== null) return;
    frame = requestAnimationFrame(() => {
      frame = null;
      window.drawPoliSkilledConnections(map, progress.has);
    });
  }
  document.addEventListener("poliskilled:progress", renderProgress);
  progress.ready.then(renderProgress);
  renderProgress();
  new ResizeObserver(drawConnections).observe(canvas);
}

const predecessorSearch = document.querySelector("[data-predecessor-search]");
if (predecessorSearch) {
  predecessorSearch.addEventListener("keydown", (event) => {
    if (event.key === "Enter") event.preventDefault();
  });
  predecessorSearch.addEventListener("input", () => {
    const term = predecessorSearch.value.trim().toLocaleLowerCase("it");
    for (const label of document.querySelectorAll(
      ".predecessor-options label",
    )) {
      label.parentElement.hidden =
        !label.textContent.toLocaleLowerCase("it").includes(term) &&
        !label.querySelector("input").checked;
    }
  });
}
