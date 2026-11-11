const { test } = require("node:test");
const assert = require("node:assert/strict");
const { skillEdges } = require("../static/js/tree-geometry.js");
const node = (id, level, x, top, bottom, parents = []) => ({
  id,
  level,
  parents,
  top: { x, y: top },
  bottom: { x, y: bottom },
});

test("unequal titles share a clear level-wide connector lane", () => {
  const nodes = [
    node("a", 1, 40, 300, 400),
    node("b", 1, 140, 300, 400),
    node("c", 2, 40, 100, 180, ["a"]),
    node("d", 2, 140, 100, 220, ["b"]),
  ];
  const edges = skillEdges(nodes, 300, null);
  assert.equal(edges[0].route, "M 40 300 V 260 H 40 V 180");
  assert.equal(edges[1].route, "M 140 300 V 260 H 140 V 220");
});
test("a dependency skipping a level routes outside intermediate nodes", () => {
  const nodes = [
    node("a", 1, 40, 500, 570),
    node("b", 2, 100, 300, 380, ["a"]),
    node("c", 3, 40, 100, 180, ["a", "b"]),
  ];
  const edges = skillEdges(nodes, 300, null);
  assert.equal(
    edges.find((e) => e.from === "a" && e.to === "c").route,
    "M 40 500 V 440 H 288 V 240 H 40 V 180",
  );
  assert.equal(edges.length, 3);
});
test("empty trees and removed predecessors do not produce dangling branches", () => {
  assert.deepEqual(skillEdges([], 300, null), []);
  assert.deepEqual(
    skillEdges([node("a", 1, 40, 100, 180, ["hidden"])], 300, null),
    [],
  );
});
