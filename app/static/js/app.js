/* Batwara SPA — auth, groups, expenses, balances, settlement plan. */
"use strict";

const API = ""; // same-origin

const state = {
  token: localStorage.getItem("batwara_token") || null,
  user: JSON.parse(localStorage.getItem("batwara_user") || "null"),
  groups: [],
  currentGroup: null,
  tab: "expenses",
  plan: null,
  balances: null,
};

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, html) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (html !== undefined) node.innerHTML = html;
  return node;
};

const fmt = (n) =>
  "Rs " +
  Number(n).toLocaleString("en-PK", { minimumFractionDigits: 0, maximumFractionDigits: 2 });

function toast(msg, isError = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.toggle("error", isError);
  t.classList.remove("hidden");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add("hidden"), 2800);
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  const res = await fetch(API + path, { ...options, headers });
  if (res.status === 401 && state.token) {
    logout();
    throw new Error("Session expired — please log in again");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body.detail) detail = Array.isArray(body.detail) ? body.detail[0]?.msg || body.detail.join(", ") : body.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

function saveAuth(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem("batwara_token", token);
  localStorage.setItem("batwara_user", JSON.stringify(user));
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("batwara_token");
  localStorage.removeItem("batwara_user");
  render();
}

/* ── Auth view ── */
function authView() {
  const wrap = el("div", "auth-wrap");
  const card = el("div", "card auth-card");

  const logo = el("div", "logo-row");
  logo.appendChild(el("div", "logo-badge", "ب"));
  const brandWrap = el("div");
  brandWrap.appendChild(el("div", "brand", "Batwara"));
  brandWrap.appendChild(el("div", "tagline", "Split expenses with friends. Settle in one tap."));
  logo.appendChild(brandWrap);

  const tabs = el("div", "tab-row");
  const tabLogin = el("button", "tab active", "Login");
  const tabReg = el("button", "tab", "Register");
  tabs.append(tabLogin, tabReg);

  const form = el("form");
  form.addEventListener("submit", (e) => e.preventDefault());

  function showLogin() {
    tabLogin.classList.add("active");
    tabReg.classList.remove("active");
    form.innerHTML = `
      <label>Email</label>
      <input type="email" id="a-email" placeholder="you@example.com" required autocomplete="email" />
      <label>Password</label>
      <input type="password" id="a-pass" placeholder="••••••••" required autocomplete="current-password" />
      <div style="height:18px"></div>
      <button class="btn" type="submit">Login</button>
    `;
    form.onsubmit = async (e) => {
      e.preventDefault();
      try {
        const res = await api("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: $("#a-email").value, password: $("#a-pass").value }),
        });
        saveAuth(res.access_token, res.user);
        toast("Welcome back, " + res.user.name.split(" ")[0] + "!");
        render();
      } catch (err) { toast(err.message, true); }
    };
  }
  function showReg() {
    tabReg.classList.add("active");
    tabLogin.classList.remove("active");
    form.innerHTML = `
      <label>Full name</label>
      <input type="text" id="r-name" placeholder="Ali Ahmed" required autocomplete="name" />
      <label>Email</label>
      <input type="email" id="r-email" placeholder="you@example.com" required autocomplete="email" />
      <label>Password <span style="text-transform:none;font-weight:400">(min 8 chars, letters + digits)</span></label>
      <input type="password" id="r-pass" placeholder="••••••••" required autocomplete="new-password" />
      <div style="height:18px"></div>
      <button class="btn" type="submit">Create account</button>
      <p class="hint">Free forever. No credit card.</p>
    `;
    form.onsubmit = async (e) => {
      e.preventDefault();
      try {
        const res = await api("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({
            name: $("#r-name").value,
            email: $("#r-email").value,
            password: $("#r-pass").value,
          }),
        });
        saveAuth(res.access_token, res.user);
        toast("Account created. Khush amdeed!");
        render();
      } catch (err) { toast(err.message, true); }
    };
  }
  tabLogin.onclick = showLogin;
  tabReg.onclick = showReg;
  showLogin();

  card.append(logo, tabs, form);
  wrap.appendChild(card);
  return wrap;
}

/* ── Home (groups) view ── */
async function homeView() {
  const shell = el("div", "shell");

  const topbar = el("div", "topbar");
  topbar.appendChild(el("div", "brand", "Batwara"));
  const chip = el("div", "user-chip");
  chip.innerHTML = `👋 ${escapeHtml(state.user.name.split(" ")[0])}`;
  const logoutBtn = el("button", "logout", "Logout");
  logoutBtn.onclick = logout;
  chip.appendChild(logoutBtn);
  topbar.appendChild(chip);
  shell.appendChild(topbar);

  const title = el("div", "section-title", "Your groups");
  const newBtn = el("button", "btn sm", "+ New group");
  newBtn.onclick = () => openGroupModal();
  title.appendChild(newBtn);
  shell.appendChild(title);

  const list = el("div", "group-list");
  if (state.groups.length === 0) {
    list.appendChild(el("div", "empty", '<div class="big">🧾</div>Create your first group — flatmates, road trip, desi jamaat, anything.'));
  }
  state.groups.forEach((g) => {
    const item = el("div", "group-item");
    item.style.cursor = "pointer";
    const avatar = el("div", "group-avatar", g.name.trim().charAt(0).toUpperCase());
    const info = el("div", "group-info");
    info.appendChild(el("div", "group-name", escapeHtml(g.name)));
    info.appendChild(el("div", "group-meta", `${g.members.length} members · ${fmt(g.total_expenses)} total`));
    item.append(avatar, info);
    item.onclick = () => openGroup(g.id);
    list.appendChild(item);
  });
  shell.appendChild(list);

  const fab = el("button", "fab", "+");
  fab.onclick = () => openGroupModal();
  shell.appendChild(fab);

  return shell;
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

/* ── Group detail view ── */
async function groupView() {
  const g = state.currentGroup;
  const shell = el("div", "shell");

  const back = el("div", "back-row");
  const backBtn = el("button", "", "← Back");
  backBtn.onclick = async () => { state.currentGroup = null; await load(); };
  back.appendChild(backBtn);
  shell.appendChild(back);

  const title = el("div", "section-title", escapeHtml(g.name));
  shell.appendChild(title);

  // Stats
  const stats = el("div", "summary-grid");
  stats.appendChild(stat("Total expenses", fmt(g.total_expenses), ""));
  const myNet = g.my_net ?? 0;
  stats.appendChild(stat("Your balance", fmt(Math.abs(myNet)), myNet > 0 ? "green" : myNet < 0 ? "red" : ""));
  shell.appendChild(stats);

  // Tabs
  const seg = el("div", "seg");
  const tabs = [
    ["expenses", "Expenses"],
    ["balances", "Balances"],
    ["plan", "Settle plan"],
  ];
  tabs.forEach(([key, label]) => {
    const b = el("button", state.tab === key ? "active" : "", label);
    b.onclick = () => { state.tab = key; render(); };
    seg.appendChild(b);
  });
  shell.appendChild(seg);

  const content = el("div");
  if (state.tab === "expenses") {
    content.appendChild(await expensesView(g));
  } else if (state.tab === "balances") {
    content.appendChild(await balancesView(g));
  } else {
    content.appendChild(await planView(g));
  }
  shell.appendChild(content);

  const fab = el("button", "fab", "+");
  fab.onclick = () => openExpenseModal(g);
  shell.appendChild(fab);
  return shell;
}

function stat(k, v, color) {
  const s = el("div", "stat");
  s.appendChild(el("div", "k", k));
  s.appendChild(el("div", "v " + color, v));
  return s;
}

async function expensesView(g) {
  const wrap = el("div");
  try {
    const expenses = await api(`/api/groups/${g.id}/expenses`);
    if (expenses.length === 0) {
      wrap.appendChild(el("div", "empty", '<div class="big">💸</div>No expenses yet. Tap + to add the first one.'));
      return wrap;
    }
    expenses.forEach((e) => {
      const item = el("div", "expense-item");
      const info = el("div", "group-info");
      info.appendChild(el("div", "expense-desc", escapeHtml(e.description)));
      info.appendChild(el("div", "expense-meta", `${escapeHtml(e.payer.name)} paid · split ${e.split_type} · ${new Date(e.created_at).toLocaleDateString()}`));
      item.appendChild(info);
      const amt = el("div", "expense-amount", fmt(e.amount));
      item.appendChild(amt);
      if (e.payer.id === state.user.id) {
        const del = el("button", "expense-del", "🗑");
        del.onclick = async () => {
          if (!confirm("Delete this expense?")) return;
          try {
            await api(`/api/groups/${g.id}/expenses/${e.id}`, { method: "DELETE" });
            toast("Expense deleted");
            render();
          } catch (err) { toast(err.message, true); }
        };
        item.appendChild(del);
      }
      wrap.appendChild(item);
    });
  } catch (err) {
    wrap.appendChild(el("div", "empty", err.message));
  }
  return wrap;
}

async function balancesView(g) {
  const wrap = el("div");
  try {
    const balances = await api(`/api/groups/${g.id}/settle/balances`);
    state.balances = balances;
    balances.forEach((b) => {
      const row = el("div", "balance-row");
      const left = el("div");
      left.appendChild(el("div", "balance-name", escapeHtml(b.user.name)));
      left.appendChild(el("div", "balance-sub", `paid ${fmt(b.paid)} · owes ${fmt(b.owes)}`));
      const net = el("div", b.net > 0.005 ? "net-pos" : b.net < -0.005 ? "net-neg" : "net-zero",
        b.net > 0.005 ? `gets back ${fmt(b.net)}` : b.net < -0.005 ? `owes ${fmt(-b.net)}` : "settled up");
      row.append(left, net);
      wrap.appendChild(row);
    });
    if (balances.length === 0) wrap.appendChild(el("div", "empty", "No balances yet."));
  } catch (err) {
    wrap.appendChild(el("div", "empty", err.message));
  }
  return wrap;
}

async function planView(g) {
  const wrap = el("div");
  try {
    const plan = await api(`/api/groups/${g.id}/settle/plan`);
    state.plan = plan;
    const header = el("div", "section-title");
    const badge = el("span", "algo-badge", plan.algorithm + " · " + plan.transactions + " txn");
    header.appendChild(badge);
    wrap.appendChild(header);

    if (plan.plan.length === 0) {
      wrap.appendChild(el("div", "empty", '<div class="big">🎉</div>All settled up! No payments needed.'));
      return wrap;
    }
    plan.plan.forEach((p) => {
      const item = el("div", "plan-item");
      const arrow = el("div", "plan-arrow", "→");
      const names = el("div");
      names.appendChild(el("div", "plan-names", `${escapeHtml(p.from_user.name)} pays ${escapeHtml(p.to_user.name)}`));
      names.appendChild(el("div", "plan-note", "minimum-transaction plan"));
      item.append(arrow, names);
      item.appendChild(el("div", "plan-amount", fmt(p.amount)));
      wrap.appendChild(item);
    });
    const note = el("p", "hint", "This plan minimizes the number of payments. Settle privately (JazzCash, Easypaisa, cash) — Batwara just tracks who owes whom.");
    wrap.appendChild(note);
  } catch (err) {
    wrap.appendChild(el("div", "empty", err.message));
  }
  return wrap;
}

/* ── Modals ── */
function modal(title, sub, body, onMount) {
  const overlay = el("div", "modal-overlay");
  const m = el("div", "modal");
  m.appendChild(el("h3", "", title));
  if (sub) m.appendChild(el("div", "sub", sub));
  const close = el("button", "modal-close", "✕");
  close.style.position = "static";
  close.style.marginLeft = "auto";
  const headerRow = el("div", "back-row");
  headerRow.appendChild(el("h3", "", title));
  headerRow.appendChild(close);
  m.innerHTML = "";
  m.appendChild(headerRow);
  if (sub) m.appendChild(el("div", "sub", sub));
  m.appendChild(body);
  overlay.appendChild(m);
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
  close.onclick = () => overlay.remove();
  document.body.appendChild(overlay);
  if (onMount) onMount();
}

function openGroupModal() {
  const body = el("form");
  body.innerHTML = `
    <label>Group name</label>
    <input type="text" id="g-name" placeholder="Hostel 3, Road trip, Family" required maxlength="120" />
    <label>Description (optional)</label>
    <input type="text" id="g-desc" placeholder="Karachi trip — Aug 2026" maxlength="1000" />
    <label>Member emails <span style="text-transform:none;font-weight:400">(registered users, comma separated)</span></label>
    <input type="text" id="g-members" placeholder="bilal@example.com, sara@example.com" />
    <div style="height:18px"></div>
    <button class="btn" type="submit">Create group</button>
  `;
  modal("New group", "Split expenses with anyone who has a Batwara account.", body, () => {
    body.onsubmit = async (e) => {
      e.preventDefault();
      const emails = $("#g-members").value.split(",").map((s) => s.trim()).filter(Boolean);
      try {
        const res = await api("/api/groups", {
          method: "POST",
          body: JSON.stringify({ name: $("#g-name").value, description: $("#g-desc").value || null, member_emails: emails }),
        });
        document.querySelector(".modal-overlay")?.remove();
        toast("Group created!");
        await openGroup(res.id);
      } catch (err) { toast(err.message, true); }
    };
  });
}

function openExpenseModal(g) {
  const body = el("form");
  const members = g.members.map((m) => m.id);
  body.innerHTML = `
    <label>What was it for?</label>
    <input type="text" id="e-desc" placeholder="Dinner at Kolachi" required maxlength="200" />
    <label>Amount (PKR)</label>
    <input type="number" id="e-amount" placeholder="2500" required min="1" step="0.01" />
    <label>Split type</label>
    <select id="e-split">
      <option value="equal">Equally among all members</option>
      <option value="exact">Exact amounts per person</option>
    </select>
    <div id="e-shares"></div>
    <div style="height:18px"></div>
    <button class="btn" type="submit">Add expense</button>
  `;
  modal("Add expense", "Paid by you — split the cost with the group.", body, () => {
    const splitSel = $("#e-split");
    const sharesWrap = $("#e-shares");
    function renderShares() {
      if (splitSel.value !== "exact") { sharesWrap.innerHTML = ""; return; }
      sharesWrap.innerHTML = "<label>Shares (must total the amount)</label>" +
        g.members.map((m) => `
          <div class="member-check">
            <label>${escapeHtml(m.name)}</label>
            <input class="share-input" type="number" min="0" step="0.01" data-uid="${m.id}" placeholder="0" />
          </div>`).join("");
    }
    splitSel.onchange = renderShares;
    renderShares();

    body.onsubmit = async (e) => {
      e.preventDefault();
      const splitType = splitSel.value;
      const payload = {
        description: $("#e-desc").value,
        amount: parseFloat($("#e-amount").value),
        split_type: splitType,
      };
      if (splitType === "exact") {
        const details = {};
        sharesWrap.querySelectorAll(".share-input").forEach((inp) => {
          const v = parseFloat(inp.value);
          if (v > 0) details[inp.dataset.uid] = v;
        });
        payload.split_details = details;
      }
      try {
        await api(`/api/groups/${g.id}/expenses`, { method: "POST", body: JSON.stringify(payload) });
        document.querySelector(".modal-overlay")?.remove();
        toast("Expense added 💸");
        render();
      } catch (err) { toast(err.message, true); }
    };
  });
}

/* ── Router ── */
async function openGroup(id) {
  try {
    const g = await api(`/api/groups/${id}`);
    state.currentGroup = g;
    // compute my net from balances
    try {
      const balances = await api(`/api/groups/${id}/settle/balances`);
      const mine = balances.find((b) => b.user.id === state.user.id);
      g.my_net = mine ? mine.net : 0;
    } catch (_) { g.my_net = 0; }
    render();
  } catch (err) {
    toast(err.message, true);
  }
}

async function load() {
  try {
    state.groups = await api("/api/groups");
  } catch (_) {}
}

async function render() {
  const app = $("#app");
  app.innerHTML = "";
  if (!state.token || !state.user) {
    app.appendChild(authView());
    return;
  }
  if (state.currentGroup) {
    app.appendChild(await groupView());
  } else {
    await load();
    app.appendChild(await homeView());
  }
}

render();
