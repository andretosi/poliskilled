"use strict";

window.drawPoliSkilledConnections = function (map, hasCompleted) {
  const canvas = map.querySelector(".tree-canvas");
  const svg = map.querySelector(".tree-connections");
  const elements = [...canvas.querySelectorAll("[data-node]")];
  const levels = new Map(elements.map((node) => [
    node.dataset.node, Number(node.closest("[data-stage]").dataset.stage),
  ]));
  const longTargets = elements.filter((node) => node.dataset.parents
    .split(",").some((id) => levels.get(node.dataset.node) > levels.get(id) + 1));
  canvas.style.setProperty(
    "--route-gutter", `${Math.max(28, 16 + longTargets.length * 8)}px`,
  );
  const bounds = canvas.getBoundingClientRect();
  const half = (value) => Math.round(value * 2) / 2;
  // Measure first, then replace the SVG in one write.
  const nodes = elements.map((node) => {
    const emblem = node.querySelector(".node-emblem").getBoundingClientRect();
    const trigger = node
      .querySelector(".skill-trigger")
      .getBoundingClientRect();
    return {
      id: node.dataset.node,
      rowTop: half(node.closest("[data-stage]").getBoundingClientRect().top - bounds.top),
      unconfirmed: node.dataset.reopening === "true" && !hasCompleted(node.dataset.node),
      level: Number(node.closest("[data-stage]").dataset.stage),
      parents: node.dataset.parents.split(",").filter(Boolean),
      top: {
        x: half(emblem.left + emblem.width / 2 - bounds.left),
        y: half(emblem.top - bounds.top),
      },
      bottom: {
        x: half(trigger.left + trigger.width / 2 - bounds.left),
        y: half(trigger.bottom - bounds.top),
      },
    };
  });
  const start = map.querySelector(".tree-origin span").getBoundingClientRect();
  const origin = {
    x: half(start.left + start.width / 2 - bounds.left),
    y: half(start.top - bounds.top),
  };
  const fragment = document.createDocumentFragment();
  for (const edge of window.skillEdges(nodes, bounds.width, origin)) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", edge.route);
    if (edge.from) path.dataset.from = edge.from;
    if (edge.to) path.dataset.to = edge.to;
    if (edge.unconfirmed) path.classList.add("is-unconfirmed");
    if (!edge.from || (hasCompleted(edge.from) && hasCompleted(edge.to)))
      path.classList.add("is-active");
    fragment.appendChild(path);
  }
  svg.setAttribute("viewBox", "0 0 " + bounds.width + " " + bounds.height);
  svg.replaceChildren(fragment);
};
