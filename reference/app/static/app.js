/* ConfPilot frontend — accessible, keyboard-friendly, progressive. */
(function () {
  "use strict";

  const store = {
    get(key, fallback) {
      try { return localStorage.getItem(key) ?? fallback; } catch { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem(key, value); } catch { /* ignore */ }
    },
  };

  const $ = (sel) => document.querySelector(sel);
  const announce = (message) => { $("#status").textContent = message; };

  /* ---------- Display preferences ---------- */
  function bindPreference(buttonId, className, storageKey) {
    const btn = $(buttonId);
    const stateSpan = btn.querySelector("[data-state]");
    const apply = (on) => {
      document.documentElement.classList.toggle(className, on);
      btn.setAttribute("aria-pressed", String(on));
      if (stateSpan) { stateSpan.textContent = on ? "on" : "off"; stateSpan.setAttribute("data-state", on ? "on" : "off"); }
    };
    apply(store.get(storageKey, "false") === "true");
    btn.addEventListener("click", () => {
      const next = btn.getAttribute("aria-pressed") !== "true";
      store.set(storageKey, String(next));
      apply(next);
      announce((next ? "enabled" : "disabled") + " " + btn.textContent.trim().split(":")[0].toLowerCase());
    });
  }

  bindPreference("#toggle-contrast", "high-contrast", "cf-high-contrast");
  bindPreference("#toggle-plain", "plain-language", "cf-plain-language");
  bindPreference("#toggle-bandwidth", "low-bandwidth", "cf-low-bandwidth");

  const lowBandwidth = () => document.documentElement.classList.contains("low-bandwidth");
  const plainLanguage = () => document.documentElement.classList.contains("plain-language");

  /* ---------- Tabs (ARIA tablist with arrow-key navigation) ---------- */
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  const panels = tabs.map((t) => document.getElementById(t.getAttribute("aria-controls")));

  function selectTab(index, focus) {
    tabs.forEach((t, i) => {
      const selected = i === index;
      t.setAttribute("aria-selected", String(selected));
      t.tabIndex = selected ? 0 : -1;
      panels[i].hidden = !selected;
    });
    if (focus) tabs[index].focus();
  }

  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => selectTab(i, false));
    tab.addEventListener("keydown", (e) => {
      let next = null;
      if (e.key === "ArrowRight") next = (i + 1) % tabs.length;
      else if (e.key === "ArrowLeft") next = (i - 1 + tabs.length) % tabs.length;
      else if (e.key === "Home") next = 0;
      else if (e.key === "End") next = tabs.length - 1;
      if (next !== null) { e.preventDefault(); selectTab(next, true); }
    });
  });

  /* ---------- HTTP helper ---------- */
  async function api(path, options) {
    const resp = await fetch(path, options);
    const text = await resp.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }
    if (!resp.ok) {
      const detail = (data && data.detail) ? data.detail : `HTTP ${resp.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  function setBusy(region, busy) {
    region.setAttribute("aria-busy", String(busy));
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function renderError(region, message) {
    region.innerHTML = `<p role="alert" class="status">Error: ${escapeHtml(message)}</p>`;
  }

  /* ---------- Search ---------- */
  $("#search-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const region = $("#search-results");
    const q = $("#search-q").value.trim();
    if (!q) return;
    setBusy(region, true);
    const k = lowBandwidth() ? 3 : 10;
    try {
      const data = await api(`/api/search?q=${encodeURIComponent(q)}&k=${k}`);
      if (!data.hits || data.hits.length === 0) {
        region.innerHTML = `<p class="status">No talks found${data.available === false ? " (search backend not configured)" : ""}.</p>`;
      } else {
        region.innerHTML = data.hits.map((h) => `
          <article class="card">
            <h3>${escapeHtml(h.title)}</h3>
            <p class="meta">${escapeHtml((h.speakers || []).join(", "))} · ${escapeHtml(h.track || "")} · ${escapeHtml(h.room || "")} · ${escapeHtml(h.day || "")}</p>
            ${lowBandwidth() ? "" : `<p class="abstract">${escapeHtml(h.abstract || "")}</p>`}
            <p class="meta">Match: ${escapeHtml((h.matched_by || []).join(" + "))} (score ${escapeHtml(h.score)})</p>
          </article>`).join("");
      }
      announce(`Found ${data.hits ? data.hits.length : 0} talks.`);
    } catch (err) {
      renderError(region, err.message);
    } finally {
      setBusy(region, false);
    }
  });

  /* ---------- Ask ---------- */
  $("#ask-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const region = $("#ask-results");
    const question = $("#ask-q").value.trim();
    if (!question) return;
    setBusy(region, true);
    region.innerHTML = `<p class="status">Thinking…</p>`;
    try {
      const data = await api("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          top_k: lowBandwidth() ? 3 : 5,
          plain_language: plainLanguage(),
        }),
      });
      const sources = (data.sources || []).map((s) =>
        `<li>${escapeHtml(s.title)}${s.speakers && s.speakers.length ? " — " + escapeHtml(s.speakers.join(", ")) : ""}</li>`
      ).join("");
      region.innerHTML = `
        <article class="card"><h3>Answer</h3><p>${escapeHtml(data.answer)}</p></article>
        ${sources ? `<article class="card"><h3>Sources</h3><ul>${sources}</ul></article>` : ""}`;
      announce("Answer ready.");
    } catch (err) {
      renderError(region, err.message);
    } finally {
      setBusy(region, false);
    }
  });

  /* ---------- Match ---------- */
  $("#match-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const region = $("#match-results");
    const raw = $("#match-interests").value.trim();
    if (!raw) return;
    setBusy(region, true);
    try {
      const interests = raw.split(",").map((s) => s.trim()).filter(Boolean);
      const data = await api("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ interests, limit: lowBandwidth() ? 5 : 10 }),
      });
      const matches = data.matches || [];
      region.innerHTML = matches.length
        ? matches.map((m) => `
            <article class="card">
              <h3>${escapeHtml(m.name)}</h3>
              <p class="meta">${escapeHtml(m.title || "")} @ ${escapeHtml(m.company || "")}</p>
              <p class="abstract">${escapeHtml((m.interests || []).join(", "))}</p>
              <p class="meta">Similarity ${escapeHtml(Math.round(m.similarity * 100))}%</p>
            </article>`).join("")
        : `<p class="status">No matches found.</p>`;
      announce(`Found ${matches.length} people.`);
    } catch (err) {
      renderError(region, err.message);
    } finally {
      setBusy(region, false);
    }
  });

  /* ---------- Rooms ---------- */
  async function loadRooms() {
    const list = $("#rooms-list");
    list.setAttribute("aria-busy", "true");
    try {
      const data = await api("/api/rooms");
      const rooms = data.rooms || [];
      list.innerHTML = rooms.map((r) => {
        const badge = `<span class="badge ${escapeHtml(r.crowd_level)}">${escapeHtml(r.crowd_level)}</span>`;
        return `<li><span><strong>${escapeHtml(r.name)}</strong>${r.quiet ? " · <em>quiet room</em>" : ""}<br /><span class="meta">${escapeHtml(r.current_count)} / ${escapeHtml(r.capacity)} people</span></span>${badge}</li>`;
      }).join("");
      announce(`Loaded ${rooms.length} rooms.`);
    } catch (err) {
      list.innerHTML = `<li class="status">Error: ${escapeHtml(err.message)}</li>`;
    } finally {
      list.setAttribute("aria-busy", "false");
    }
  }
  $("#rooms-refresh").addEventListener("click", loadRooms);
  if (!panels[3].hidden) loadRooms(); // preload if rooms tab active at start

  /* ---------- Chaos ---------- */
  async function refreshChaos() {
    const data = await api("/api/chaos");
    const btn = $("#chaos-enable");
    btn.setAttribute("aria-pressed", String(data.enabled));
    btn.textContent = data.enabled ? "Disable chaos" : "Enable chaos";
    $("#chaos-status").textContent =
      `Chaos is ${data.enabled ? "ON" : "OFF"} — latency ${data.latency_ms} ms, error rate ${data.error_rate}.`;
  }

  $("#chaos-enable").addEventListener("click", async () => {
    const enabled = $("#chaos-enable").getAttribute("aria-pressed") !== "true";
    const latency = parseInt($("#chaos-latency").value, 10) || 0;
    const errorRate = parseFloat($("#chaos-error").value) || 0;
    try {
      await api("/api/chaos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled, latency_ms: latency, error_rate: errorRate }),
      });
      await refreshChaos();
      announce(enabled ? "Chaos enabled." : "Chaos disabled.");
    } catch (err) {
      $("#chaos-status").textContent = "Error: " + err.message;
    }
  });

  refreshChaos().catch(() => {});
})();
