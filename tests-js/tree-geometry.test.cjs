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

test("unconfirmed editions mark only their connected branches, including roots", () => {
  const a = { ...node("a", 1, 40, 300, 400), unconfirmed: true };
  const b = node("b", 1, 140, 300, 400);
  const c = node("c", 2, 40, 100, 180, ["a", "b"]);
  const edges = skillEdges([a, b, c], 300, { x: 100, y: 450 });
  assert.equal(edges.find((e) => e.from === "a").unconfirmed, true);
  assert.equal(edges.find((e) => e.from === "b").unconfirmed, false);
  assert.equal(edges.find((e) => !e.from && e.to === "a").unconfirmed, true);
  a.unconfirmed = false; // Completed locally, or a confirmed new edition.
  assert.ok(skillEdges([a, b, c], 300, null).every((e) => !e.unconfirmed));
});

test("different destinations get distinct lanes clear of the longest title", () => {
  const nodes = [
    node("a", 1, 40, 300, 400),
    node("b", 1, 140, 300, 400),
    node("c", 2, 40, 100, 180, ["a"]),
    node("d", 2, 140, 100, 220, ["b"]),
  ];
  const edges = skillEdges(nodes, 300, null);
  const lanes = edges.map((edge) => Number(edge.route.split(" V ")[1].split(" ")[0]));
  assert.notEqual(lanes[0], lanes[1]);
  assert.ok(lanes.every((y) => y > 220 && y < 300));
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
    "M 40 500 V 460 H 12 V 240 H 40 V 180",
  );
  assert.equal(edges.length, 3);
});
test("BCI-style skipped levels stay on the source side, also when mirrored", () => {
  for (const mirror of [false, true]) {
    const x = (value) => mirror ? 300 - value : value;
    const nodes = [
      node("aim", 1, x(80), 500, 570),
      node("bea", 1, x(220), 500, 570),
      node("course", 2, 150, 300, 380, ["bea"]),
      node("goal", 3, 150, 100, 180, ["course", "aim"]),
    ];
    const route = skillEdges(nodes, 300, null).find((e) => e.from === "aim").route;
    const gutter = mirror ? 288 : 12;
    assert.equal(route, `M ${x(80)} 500 V 460 H ${gutter} V 240 H 150 V 180`);
  }
});
test("empty trees and removed predecessors do not produce dangling branches", () => {
  assert.deepEqual(skillEdges([], 300, null), []);
  assert.deepEqual(
    skillEdges([node("a", 1, 40, 100, 180, ["hidden"])], 300, null),
    [],
  );
});

test("horizontal lanes leave the level headings clear", () => {
  const parent = { ...node("a", 1, 40, 500, 570), rowTop: 450 };
  const child = node("b", 2, 150, 300, 400, ["a"]);
  const edge = skillEdges([parent, child], 300, null)[0];
  assert.equal(edge.route, "M 40 500 V 425 H 150 V 400");
});
