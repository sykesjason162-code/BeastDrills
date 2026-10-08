(function () {
"use strict";

  const STORE_KEY = "bd.lang";
  let table = null;
  let current = "en";

  function fill(text, vars) {
    if (!vars) return text;
    return text.replace(/\{(\w+)\}/g, (whole, key) =>
      Object.prototype.hasOwnProperty.call(vars, key) ? String(vars[key]) : whole);
  }

  function T(english, vars) {

    const found = table && table[english];
    return fill(found || english, vars);
  }

  function pool(name, english) {
    const localised = table && table["@pool:" + name];
    return Array.isArray(localised) && localised.length ? localised : english;
  }

  async function load(code) {
    current = code;
    table = null;

    document.documentElement.lang = code;
    if (code === "en") return;
    try {
      const r = await fetch(`/static/locales/${encodeURIComponent(code)}.json`);
      if (r.ok) table = await r.json();
    } catch {

      table = null;
    }
  }

  function name(id) {
    const names = table && table["@names"];
    return (names && names[id]) || null;
  }

  const ENDONYM = {
    en: "English",
    ja: "日本語",
    zh: "简体中文",
    ko: "한국어",
  };

  function applyDom(root) {
    (root || document).querySelectorAll("[data-t]").forEach((el) => {

      if (el.firstElementChild) return;
      const key = el.getAttribute("data-t") || el.textContent.trim();
      if (!key) return;

      if (!el.dataset.tKey) el.dataset.tKey = key;
      const out = T(el.dataset.tKey);
      if (out !== el.textContent) el.textContent = out;
    });

    (root || document).querySelectorAll("[data-t-placeholder]").forEach((el) => {
      const key = el.dataset.tPlaceholder || el.placeholder;
      if (key) el.placeholder = T(key);
    });
    (root || document).querySelectorAll("[data-t-title]").forEach((el) => {
      const key = el.dataset.tTitle || el.title;
      if (key) el.title = T(key);
    });
  }

  function applyLinks() {
    const links = table && table["@links"];
    if (!links) return;
    for (const [id, spec] of Object.entries(links)) {
      const el = document.getElementById("bd-link-" + id);
      if (!el || !spec) continue;
      if (spec.href) el.href = spec.href;
      if (spec.label) el.textContent = spec.label;
    }
  }

  async function mountPicker() {
    const sel = document.getElementById("bd-lang");
    if (!sel) return;
    const codes = await window.i18n.available();

    if (!codes || codes.length < 2) return;
    sel.innerHTML = codes
      .map((c) => `<option value="${c}">${ENDONYM[c] || c.toUpperCase()}</option>`)
      .join("");
    sel.value = window.i18n.current;
    sel.hidden = false;
    sel.addEventListener("change", () => window.i18n.use(sel.value));
  }

  window.i18n = {
    T,
    pool,
    fill,
    name,

    applyDom,
    get current() { return current; },

    ready: (async () => {
      await load(localStorage.getItem(STORE_KEY) || "en");

      const onReady = () => { mountPicker(); applyLinks(); applyDom(); };
      if (document.readyState === "loading")
        document.addEventListener("DOMContentLoaded", onReady);
      else onReady();
    })(),
    async use(code) {
      localStorage.setItem(STORE_KEY, code);
      await load(code);

      location.reload();
    },
    async available() {
      try {
        const r = await fetch("/api/locales");
        return r.ok ? await r.json() : ["en"];
      } catch { return ["en"]; }
    },
  };
})();
