"use strict";

window.drawPoliSkilledConnections = function (map, hasCompleted) {
  const canvas = map.querySelector(".tree-canvas");
  const svg = map.querySelector(".tree-connections");
  const bounds = canvas.getBoundingClientRect();
  const half = (value) => Math.round(value * 2) / 2;
  // Measure first, then replace the SVG in one write.
  const nodes = [...canvas.querySelectorAll("[data-node]")].map((node) => {
    const emblem = node.querySelector(".node-emblem").getBoundingClientRect();
    const trigger = node
      .querySelector(".skill-trigger")
      .getBoundingClientRect();
    return {
      id: node.dataset.node,
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
    if (!edge.from || (hasCompleted(edge.from) && hasCompleted(edge.to)))
      path.classList.add("is-active");
    fragment.appendChild(path);
  }
  svg.setAttribute("viewBox", "0 0 " + bounds.width + " " + bounds.height);
  svg.replaceChildren(fragment);
};
