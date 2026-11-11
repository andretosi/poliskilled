"use strict";

function skillEdges(nodes, width, origin) {
  const levels = new Map();
  const byId = new Map(nodes.map((node) => [node.id, node]));
  for (const node of nodes) {
    const row = levels.get(node.level) || { top: Infinity, bottom: -Infinity };
    row.top = Math.min(row.top, node.top.y);
    row.bottom = Math.max(row.bottom, node.bottom.y);
    levels.set(node.level, row);
  }
  const lane = (lower, upper) =>
    (levels.get(lower).top + levels.get(upper).bottom) / 2;
  const edges = [];
  for (const child of nodes) {
    for (const parentId of child.parents) {
      const parent = byId.get(parentId);
      if (!parent) continue;
      const from = parent.top,
        to = child.bottom;
      let route;
      if (child.level === parent.level + 1) {
        const y = lane(parent.level, child.level);
        route = `M ${from.x} ${from.y} V ${y} H ${to.x} V ${to.y}`;
      } else {
        // Skipped levels use the outer gutter, never another node.
        const exit = lane(parent.level, parent.level + 1);
        const enter = lane(child.level - 1, child.level);
        route = `M ${from.x} ${from.y} V ${exit} H ${width - 12} V ${enter} H ${to.x} V ${to.y}`;
      }
      edges.push({ from: parent.id, to: child.id, route });
    }
  }
  const roots = nodes.filter((node) => !node.parents.length);
  if (roots.length && origin) {
    const y = (Math.max(...roots.map((node) => node.bottom.y)) + origin.y) / 2;
    edges.push({ route: `M ${origin.x} ${origin.y} V ${y}` });
    for (const root of roots) {
      edges.push({
        route: `M ${origin.x} ${y} H ${root.bottom.x} V ${root.bottom.y}`,
      });
    }
  }
  return edges;
}

if (typeof module !== "undefined") module.exports = { skillEdges };
else window.skillEdges = skillEdges;
