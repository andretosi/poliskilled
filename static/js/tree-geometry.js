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
  const targets = new Map();
  const skipped = [];
  for (const child of nodes) {
    for (const parentId of child.parents) {
      const parent = byId.get(parentId);
      if (!parent) continue;
      for (const lower of new Set([parent.level, child.level - 1])) {
        if (!targets.has(lower)) targets.set(lower, new Set());
        targets.get(lower).add(child.id);
      }
      if (child.level > parent.level + 1 && !skipped.includes(child.id))
        skipped.push(child.id);
    }
  }
  const lane = (lower, target) => {
    const ids = [...targets.get(lower)];
    const bottom = levels.get(lower + 1).bottom;
    const gap = levels.get(lower).top - bottom;
    return bottom + gap * (ids.indexOf(target) + 1) / (ids.length + 1);
  };
  const edges = [];
  for (const child of nodes) {
    for (const parentId of child.parents) {
      const parent = byId.get(parentId);
      if (!parent) continue;
      const from = parent.top,
        to = child.bottom;
      let route;
      if (child.level === parent.level + 1) {
        const y = lane(parent.level, child.id);
        route = `M ${from.x} ${from.y} V ${y} H ${to.x} V ${to.y}`;
      } else {
        // Skipped levels use the outer gutter, never another node.
        const exit = lane(parent.level, child.id);
        const enter = lane(child.level - 1, child.id);
        const gutter = width - 12 - 8 * skipped.indexOf(child.id);
        route = `M ${from.x} ${from.y} V ${exit} H ${gutter} V ${enter} H ${to.x} V ${to.y}`;
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
