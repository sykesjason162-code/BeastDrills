const SECTION_SEL = "section.panel[id]";

function slug(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function makeHeadingsLinkable() {
  const used = new Set([...document.querySelectorAll("[id]")].map((el) => el.id));
  document.querySelectorAll(`${SECTION_SEL} h3`).forEach((h) => {
    if (!h.id) {
      let id = slug(h.textContent);

      let n = 2;
      const base = id;
      while (!id || used.has(id)) id = `${base}-${n++}`;
      h.id = id;
    }
    used.add(h.id);

    h.classList.add("help-anchor");
    h.title = "Copy a link to this section";
    h.addEventListener("click", () => {
      const url = `${location.origin}${location.pathname}#${h.id}`;
      history.replaceState(null, "", `#${h.id}`);

      if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(
          () => flash(h, "Link copied"),
          () => flash(h, "Link in the address bar")
        );
      } else {
        flash(h, "Link in the address bar");
      }
    });
  });
}

function flash(el, message) {
  const tag = document.createElement("span");
  tag.className = "help-flash";
  tag.textContent = message;
  el.appendChild(tag);
  setTimeout(() => tag.remove(), 1400);
}

function buildContents() {
  const nav = document.querySelector(".help-toc");
  if (!nav) return [];
  const links = [];
  nav.classList.add("help-toc-tree");
  nav.innerHTML = `
    <div class="help-search">
      <input type="search" id="help-search" placeholder="Search help" autocomplete="off">
      <span class="dim" id="help-search-count"></span>
    </div>
    <div class="help-toc-list" id="help-toc-list"></div>`;

  const list = document.getElementById("help-toc-list");
  document.querySelectorAll(SECTION_SEL).forEach((section) => {
    const h2 = section.querySelector("h2");
    if (!h2) return;
    const group = document.createElement("div");
    group.className = "help-toc-group";
    const top = document.createElement("a");
    top.href = `#${section.id}`;
    top.className = "help-toc-top";
    top.textContent = h2.textContent.trim();
    group.appendChild(top);
    links.push({ a: top, id: section.id });

    const subs = section.querySelectorAll("h3");
    if (subs.length) {
      const ul = document.createElement("div");
      ul.className = "help-toc-subs";
      subs.forEach((h) => {
        const a = document.createElement("a");
        a.href = `#${h.id}`;
        a.textContent = h.textContent.trim();
        ul.appendChild(a);
        links.push({ a, id: h.id });
      });
      group.appendChild(ul);
    }
    list.appendChild(group);
  });
  return links;
}

function followScroll(links) {
  if (!links.length) return;
  const targets = links
    .map(({ a, id }) => ({ a, el: document.getElementById(id) }))
    .filter((t) => t.el);

  let current = null;
  const update = () => {
    const line = window.scrollY + 120;
    let found = targets[0];
    for (const t of targets) {
      if (t.el.getBoundingClientRect().top + window.scrollY <= line) found = t;
      else break;
    }
    if (found === current) return;
    if (current) current.a.classList.remove("is-current");
    found.a.classList.add("is-current");

    found.a.scrollIntoView({ block: "nearest", inline: "nearest" });
    current = found;
  };

  let queued = false;
  addEventListener("scroll", () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; update(); });
  }, { passive: true });
  update();
}

function wireSearch(links) {
  const input = document.getElementById("help-search");
  const count = document.getElementById("help-search-count");
  if (!input) return;

  const blocks = [...document.querySelectorAll(SECTION_SEL)].map((section) => ({
    section,

    text: section.innerText.toLowerCase(),
    subs: [...section.querySelectorAll("h3")].map((h) => ({
      h,

      text: sliceUntilNextH3(h).toLowerCase(),
    })),
  }));

  const apply = () => {
    const q = input.value.trim().toLowerCase();
    document.body.classList.toggle("help-searching", !!q);
    if (!q) {
      blocks.forEach((b) => {
        b.section.hidden = false;
        b.subs.forEach((s) => s.h.classList.remove("help-hit"));
      });
      links.forEach(({ a }) => (a.hidden = false));
      count.textContent = "";
      return;
    }
    let hits = 0;
    const shown = new Set();
    blocks.forEach((b) => {
      const match = b.text.includes(q);
      b.section.hidden = !match;
      if (match) {
        shown.add(b.section.id);
        hits++;
      }
      b.subs.forEach((s) => {
        const sub = match && s.text.includes(q);
        s.h.classList.toggle("help-hit", sub);
        if (sub) shown.add(s.h.id);
      });
    });
    links.forEach(({ a, id }) => (a.hidden = !shown.has(id)));
    count.textContent = hits ? `${hits} section${hits === 1 ? "" : "s"}` : "no matches";
  };

  input.addEventListener("input", apply);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { input.value = ""; apply(); }
  });
}

function sliceUntilNextH3(h) {
  let text = h.textContent + " ";
  for (let el = h.nextElementSibling; el && el.tagName !== "H3"; el = el.nextElementSibling) {
    text += el.innerText + " ";
  }
  return text;
}

makeHeadingsLinkable();
const links = buildContents();
followScroll(links);
wireSearch(links);

if (location.hash) {
  const target = document.getElementById(location.hash.slice(1));
  if (target) target.scrollIntoView();
}
