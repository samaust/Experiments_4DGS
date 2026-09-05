const { test } = require("node:test");
const assert = require("node:assert/strict");
const { createClock } = require("../patches/splatv/time-controls.js");
const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} != ${expected}`);

test("starts paused; playback is linear across different frame intervals", () => {
  const clock = createClock();
  assert.equal(clock.playing, false);
  assert.equal(clock.sample(1000), 0);
  clock.toggle(1000);
  near(clock.sample(1250), 0.05);
  near(clock.sample(3500), 0.5);
  near(clock.sample(6000), 0);
});

test("pause and resume exclude paused wall time", () => {
  const clock = createClock();
  clock.toggle(0);
  clock.toggle(1000);
  near(clock.sample(10000), 0.2);
  clock.toggle(20000);
  near(clock.sample(20500), 0.3);
});

test("scrubbing pauses, endpoints remain exact, and restart resets", () => {
  const clock = createClock();
  clock.toggle(0);
  clock.seek(0.5, 1000);
  assert.equal(clock.playing, false);
  assert.equal(clock.sample(2000), 0.5);
  clock.seek(1, 3000);
  assert.equal(clock.sample(4000), 1);
  clock.toggle(4000);
  near(clock.sample(4500), 0.1);
  clock.seek(0, 4500);
  assert.equal(clock.sample(6000), 0);
});

test("duration edits preserve current time and reject invalid values", () => {
  const clock = createClock();
  clock.toggle(0);
  clock.setDuration(10, 1000);
  near(clock.sample(2000), 0.3);
  for (const value of [0, -1, NaN, Infinity, 3601]) {
    clock.setDuration(value, 2000);
    assert.equal(clock.seconds, 10);
  }
  clock.pause(3000);
  near(clock.sample(50000), 0.4);
});

test("browser controls wire play, seek, restart, tab pause, and event isolation", () => {
  const fs = require("node:fs");
  const vm = require("node:vm");
  const path = require("node:path");
  // A small DOM harness exercises browser event wiring without requiring WebGL.
  class Element {
    constructor(value = "") { this.value = value; this.listeners = {}; this.style = {}; }
    setAttribute(name, value) { this[name] = value; }
    addEventListener(name, handler) { this.listeners[name] = handler; }
  }
  const elements = Object.fromEntries(["scene-play", "scene-restart", "scene-time",
    "scene-time-value", "scene-duration"].map(id => [id, new Element()]));
  const panel = new Element();
  const listeners = {};
  const document = {
    hidden: false,
    createElement: () => panel,
    getElementById: id => elements[id],
    body: { appendChild: () => {} },
    addEventListener: (name, handler) => { listeners[name] = handler; },
  };
  let now = 0;
  const context = vm.createContext({ document, performance: { now: () => now } });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../patches/splatv/time-controls.js"), "utf8"), context);
  assert.equal(context.splatvTimeline.sample(0), 0);
  elements["scene-play"].listeners.click();
  now = 1000;
  near(context.splatvTimeline.sample(now), 0.2);
  elements["scene-time"].value = "0.75";
  elements["scene-time"].listeners.input();
  now = 3000;
  near(context.splatvTimeline.sample(now), 0.75);
  assert.equal(elements["scene-play"].textContent, "Play");
  elements["scene-restart"].listeners.click();
  assert.equal(context.splatvTimeline.sample(now), 0);
  elements["scene-play"].listeners.click();
  now = 4000;
  document.hidden = true;
  listeners.visibilitychange();
  near(context.splatvTimeline.sample(9000), 0.2);
  for (const type of ["keydown", "keyup", "wheel", "pointerdown", "touchstart"]) {
    let stopped = false;
    panel.listeners[type]({ stopPropagation: () => { stopped = true; } });
    assert.equal(stopped, true, type);
  }
});
