/* Local splaTV inspection controls. No dependencies or network requests. */
(function (root) {
  "use strict";

  function createClock() {
    let time = 0;
    let playing = false;
    let seconds = 5;
    let previous = null;
    return {
      get time() { return time; },
      get playing() { return playing; },
      get seconds() { return seconds; },
      sample(now) {
        if (!Number.isFinite(now)) return time;
        if (playing && previous !== null) {
          time = (time + Math.max(0, now - previous) / (seconds * 1000)) % 1;
        }
        previous = now;
        return time;
      },
      toggle(now) {
        this.sample(now);
        playing = !playing;
      },
      seek(value, now) {
        if (!Number.isFinite(value)) return;
        time = Math.max(0, Math.min(1, value));
        playing = false;
        previous = now;
      },
      setDuration(value, now) {
        this.sample(now);
        if (Number.isFinite(value) && value >= 0.1 && value <= 3600) seconds = value;
      },
      pause(now) {
        this.sample(now);
        playing = false;
      },
    };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { createClock };
    return;
  }

  const clock = createClock();
  const panel = document.createElement("section");
  panel.id = "splatv-time-controls";
  panel.setAttribute("aria-label", "Scene time controls");
  panel.style.cssText = "position:fixed;bottom:12px;left:12px;z-index:1000;" +
    "max-width:calc(100vw - 48px);padding:10px;border-radius:8px;" +
    "background:rgba(0,0,0,.8);color:white;font:14px sans-serif;" +
    "display:flex;gap:8px;align-items:center;flex-wrap:wrap;";
  panel.innerHTML = `
    <button type="button" id="scene-play" aria-pressed="false">Play</button>
    <button type="button" id="scene-restart">Restart</button>
    <label for="scene-time">Time (0–1)</label>
    <input id="scene-time" type="range" min="0" max="1" step="0.001" value="0">
    <output id="scene-time-value" for="scene-time">0.000</output>
    <label for="scene-duration">Viewing cycle (seconds)</label>
    <input id="scene-duration" type="number" min="0.1" max="3600" step="0.1"
      value="5" style="width:5em" title="Playback setting, not necessarily capture duration">
  `;
  document.body.appendChild(panel);
  const play = document.getElementById("scene-play");
  const slider = document.getElementById("scene-time");
  const output = document.getElementById("scene-time-value");
  const duration = document.getElementById("scene-duration");

  function refresh() {
    play.textContent = clock.playing ? "Pause" : "Play";
    play.setAttribute("aria-pressed", String(clock.playing));
    slider.value = String(clock.time);
    output.value = clock.time.toFixed(3);
  }
  play.addEventListener("click", () => {
    clock.toggle(performance.now());
    refresh();
  });
  document.getElementById("scene-restart").addEventListener("click", () => {
    clock.seek(0, performance.now());
    refresh();
  });
  slider.addEventListener("input", () => {
    clock.seek(Number(slider.value), performance.now());
    refresh();
  });
  duration.addEventListener("change", () => {
    clock.setDuration(Number(duration.value), performance.now());
    duration.value = String(clock.seconds);
    refresh();
  });
  // Keep keyboard edits, pointer gestures, and scrolling out of camera handlers.
  // Do not prevent defaults: buttons and range/number keyboard controls still work.
  for (const type of ["keydown", "keyup", "pointerdown", "pointermove", "pointerup",
    "mousedown", "mousemove", "mouseup", "touchstart", "touchmove", "touchend",
    "wheel", "click", "dblclick"]) {
    panel.addEventListener(type, (event) => event.stopPropagation());
  }
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      clock.pause(performance.now());
      refresh();
    }
  });
  root.splatvTimeline = {
    sample(now = performance.now()) {
      const time = clock.sample(now);
      refresh();
      return time;
    },
  };
})(globalThis);
