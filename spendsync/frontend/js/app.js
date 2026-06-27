const App = (() => {
  const state = {
    expenses: [],
    categories: [],
    budgets: [],
    filters: { q: "", category_id: "", from: "", to: "", min: "", max: "" },
    editingUuid: null,
  };

  const $ = (id) => document.getElementById(id);

  function toast(message, warn = false) {
    const el = $("toast");
    el.textContent = message;
    el.classList.toggle("warn", warn);
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), 2800);
  }

  function money(amount, currency = "PLN") {
    try {
      return new Intl.NumberFormat("pl-PL", { style: "currency", currency }).format(amount);
    } catch {
      return `${Number(amount).toFixed(2)} ${currency}`;
    }
  }

  function categoryById(id) {
    return state.categories.find((c) => c.id === id) || null;
  }

  function setSyncPill(stateName) {
    const labels = { online: "Online", offline: "Offline", syncing: "Synchronizuję…" };
    $("sync-pill").dataset.state = stateName;
    $("sync-label").textContent = labels[stateName];
  }

  async function loadLocal() {
    const all = await DB.getAll("expenses");
    state.expenses = all.filter((e) => !e.deleted);
    state.categories = await DB.getAll("categories");
    state.budgets = await DB.getAll("budgets");
  }

  function applyFilters(items) {
    const f = state.filters;
    return items.filter((e) => {
      if (f.q && !e.description.toLowerCase().includes(f.q.toLowerCase())) return false;
      if (f.category_id && e.category_id !== Number(f.category_id)) return false;
      if (f.from && e.spent_at < f.from) return false;
      if (f.to && e.spent_at > f.to) return false;
      if (f.min && e.amount < Number(f.min)) return false;
      if (f.max && e.amount > Number(f.max)) return false;
      return true;
    });
  }

  function renderSummary() {
    const month = new Date().toISOString().slice(0, 7);
    const total = state.expenses
      .filter((e) => e.spent_at.slice(0, 7) === month)
      .reduce((sum, e) => sum + (e.currency === "PLN" ? e.amount : 0), 0);
    $("month-total").textContent = money(total);
    $("month-period").textContent = new Date().toLocaleDateString("pl-PL", { month: "long", year: "numeric" });
  }

  function renderBudgets() {
    const container = $("budget-list");
    if (state.budgets.length === 0) {
      container.innerHTML = '<p class="muted">Brak budżetów na ten miesiąc.</p>';
      return;
    }
    container.innerHTML = state.budgets
      .map((b) => {
        const pct = Math.min(100, (b.spent / b.limit_amount) * 100);
        const over = b.spent > b.limit_amount;
        const name = b.category_name || "Wszystko";
        return `
          <div class="budget-row">
            <div class="budget-row-head">
              <span>${name}</span>
              <span class="budget-spent">${money(b.spent)} / ${money(b.limit_amount)}</span>
            </div>
            <div class="budget-bar"><div class="budget-fill ${over ? "over" : ""}" style="width:${pct}%"></div></div>
          </div>`;
      })
      .join("");
  }

  function renderCategoryFilter() {
    const select = $("filter-category");
    const current = select.value;
    select.innerHTML =
      '<option value="">Wszystkie kategorie</option>' +
      state.categories.map((c) => `<option value="${c.id}">${c.name}</option>`).join("");
    select.value = current;
  }

  function formatDayLabel(iso) {
    const today = new Date().toISOString().slice(0, 10);
    if (iso === today) return "Dzisiaj";
    return new Date(iso).toLocaleDateString("pl-PL", { weekday: "long", day: "numeric", month: "long" });
  }

  function renderList() {
    const items = applyFilters(state.expenses).sort((a, b) =>
      a.spent_at < b.spent_at ? 1 : a.spent_at > b.spent_at ? -1 : 0
    );
    $("empty-state").hidden = items.length > 0;

    const groups = {};
    for (const e of items) (groups[e.spent_at] ||= []).push(e);

    $("expense-list").innerHTML = Object.keys(groups)
      .sort((a, b) => (a < b ? 1 : -1))
      .map((day) => {
        const rows = groups[day]
          .map((e) => {
            const cat = categoryById(e.category_id);
            const dot = cat ? cat.color : "var(--muted)";
            const catName = cat ? cat.name : "Bez kategorii";
            const dirty = e.dirty ? '<span class="dirty-flag">• czeka na sync</span>' : "";
            return `
              <div class="expense-item">
                <span class="cat-dot" style="background:${dot}"></span>
                <div class="expense-main">
                  <div class="expense-desc">${e.description || "(bez opisu)"} ${dirty}</div>
                  <div class="expense-meta">${catName}</div>
                </div>
                <span class="expense-amount">${money(e.amount, e.currency)}</span>
                <div class="expense-actions">
                  <button data-edit="${e.client_uuid}">Edytuj</button>
                  <button data-delete="${e.client_uuid}">Usuń</button>
                </div>
              </div>`;
          })
          .join("");
        return `<div class="day-group"><div class="day-label">${formatDayLabel(day)}</div>${rows}</div>`;
      })
      .join("");
  }

  function monthKey(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  }

  function renderCategoryChart() {
    const container = $("chart-categories");
    const month = monthKey(new Date());
    const items = state.expenses.filter((e) => e.spent_at.slice(0, 7) === month && e.currency === "PLN");

    const totals = {};
    for (const e of items) {
      const key = e.category_id ?? "none";
      totals[key] = (totals[key] || 0) + e.amount;
    }
    const entries = Object.entries(totals).sort((a, b) => b[1] - a[1]);
    const sum = entries.reduce((s, [, v]) => s + v, 0);

    if (sum === 0) {
      container.innerHTML = '<p class="chart-empty">Brak wydatków w tym miesiącu</p>';
      return;
    }

    const r = 54;
    const circumference = 2 * Math.PI * r;
    let offset = 0;
    let segments = "";
    for (const [key, value] of entries) {
      const cat = key === "none" ? null : categoryById(Number(key));
      const color = cat ? cat.color : "#9ca3af";
      const len = (value / sum) * circumference;
      segments += `<circle cx="64" cy="64" r="${r}" fill="none" stroke="${color}" stroke-width="18" stroke-dasharray="${len.toFixed(2)} ${(circumference - len).toFixed(2)}" stroke-dashoffset="${(-offset).toFixed(2)}"></circle>`;
      offset += len;
    }

    const svg = `
      <svg viewBox="0 0 128 128" width="128" height="128">
        <g transform="rotate(-90 64 64)">${segments}</g>
        <text x="64" y="60" text-anchor="middle" font-size="10" fill="var(--muted)">Razem</text>
        <text x="64" y="78" text-anchor="middle" font-size="14" font-weight="600" fill="var(--ink)">${Math.round(sum)} zł</text>
      </svg>`;

    const legend = entries
      .map(([key, value]) => {
        const cat = key === "none" ? null : categoryById(Number(key));
        const color = cat ? cat.color : "#9ca3af";
        const name = cat ? cat.name : "Bez kategorii";
        const pct = Math.round((value / sum) * 100);
        return `<div class="legend-item"><span class="cat-dot" style="background:${color}"></span><span class="legend-name">${name}</span><span class="legend-val">${pct}%</span></div>`;
      })
      .join("");

    container.innerHTML = `<div class="donut-wrap"><div class="donut">${svg}</div><div class="donut-legend">${legend}</div></div>`;
  }

  function renderMonthChart() {
    const container = $("chart-months");
    const now = new Date();
    const months = [];
    for (let i = 5; i >= 0; i--) months.push(new Date(now.getFullYear(), now.getMonth() - i, 1));

    const sums = months.map((d) => {
      const key = monthKey(d);
      return state.expenses
        .filter((e) => e.currency === "PLN" && e.spent_at.slice(0, 7) === key)
        .reduce((s, e) => s + e.amount, 0);
    });

    if (sums.every((v) => v === 0)) {
      container.innerHTML = '<p class="chart-empty">Brak danych do wykresu</p>';
      return;
    }

    const max = Math.max(...sums);
    const bars = months
      .map((d, i) => {
        const height = Math.round((sums[i] / max) * 100);
        const label = d.toLocaleDateString("pl-PL", { month: "short" });
        return `<div class="bar-col"><div class="bar" style="height:${height}%" title="${money(sums[i])}"></div><span class="bar-label">${label}</span></div>`;
      })
      .join("");

    container.innerHTML = `<div class="bars">${bars}</div>`;
  }

  function renderAll() {
    renderSummary();
    renderStats();
    renderBudgets();
    renderCategoryFilter();
    renderList();
  }

  function renderStats() {
    renderCategoryChart();
    renderMonthChart();
  }

  function openModal(html) {
    $("modal-content").innerHTML = html;
    $("modal-backdrop").hidden = false;
  }
  function closeModal() {
    $("modal-backdrop").hidden = true;
    state.editingUuid = null;
  }

  function expenseModal(expense) {
    const today = new Date().toISOString().slice(0, 10);
    const options = state.categories
      .map((c) => `<option value="${c.id}" ${expense && expense.category_id === c.id ? "selected" : ""}>${c.name}</option>`)
      .join("");
    const currencies = ["PLN", "EUR", "USD", "GBP"]
      .map((cur) => `<option value="${cur}" ${expense && expense.currency === cur ? "selected" : ""}>${cur}</option>`)
      .join("");
    openModal(`
      <h3>${expense ? "Edytuj wydatek" : "Nowy wydatek"}</h3>
      <div class="modal-row">
        <label><span>Kwota</span><input id="m-amount" type="number" min="0.01" step="0.01" value="${expense ? expense.amount : ""}"></label>
        <label><span>Waluta</span><select id="m-currency">${currencies}</select></label>
      </div>
      <p id="m-rate" class="rate-hint"></p>
      <label><span>Opis</span><input id="m-desc" type="text" maxlength="255" value="${expense ? expense.description.replace(/"/g, "&quot;") : ""}"></label>
      <div class="modal-row">
        <label><span>Data</span><input id="m-date" type="date" value="${expense ? expense.spent_at : today}"></label>
        <label><span>Kategoria</span><select id="m-category"><option value="">—</option>${options}</select></label>
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="m-cancel">Anuluj</button>
        <button class="btn btn-primary" id="m-save">Zapisz</button>
      </div>
    `);

    const updateRate = async () => {
      const cur = $("m-currency").value;
      const amount = Number($("m-amount").value);
      const hint = $("m-rate");
      if (cur === "PLN" || !amount) { hint.textContent = ""; return; }
      if (!navigator.onLine) { hint.textContent = "Kurs niedostępny offline"; return; }
      try {
        const data = await API.request(`/rates?code=${cur}`);
        hint.textContent = `≈ ${money(amount * data.rate)} (kurs NBP ${data.rate})`;
      } catch {
        hint.textContent = "";
      }
    };
    $("m-currency").addEventListener("change", updateRate);
    $("m-amount").addEventListener("input", updateRate);
    $("m-cancel").addEventListener("click", closeModal);
    $("m-save").addEventListener("click", saveExpense);
    updateRate();
  }

  async function saveExpense() {
    const amount = Number($("m-amount").value);
    if (!amount || amount <= 0) { toast("Podaj kwotę większą od zera", true); return; }
    const data = {
      amount,
      currency: $("m-currency").value,
      description: $("m-desc").value.trim(),
      spent_at: $("m-date").value,
      category_id: $("m-category").value ? Number($("m-category").value) : null,
    };
    const now = new Date().toISOString();

    if (state.editingUuid) {
      const rec = await DB.get("expenses", state.editingUuid);
      Object.assign(rec, data, { dirty: true, updated_at: now });
      await DB.put("expenses", rec);
    } else {
      await DB.put("expenses", {
        client_uuid: crypto.randomUUID(),
        server_id: null,
        version: 0,
        deleted: false,
        dirty: true,
        updated_at: now,
        ...data,
      });
    }
    closeModal();
    await loadLocal();
    renderAll();
    trySync();
  }

  async function deleteExpense(uuid) {
    const rec = await DB.get("expenses", uuid);
    if (!rec) return;
    rec.deleted = true;
    rec.dirty = true;
    rec.updated_at = new Date().toISOString();
    await DB.put("expenses", rec);
    await loadLocal();
    renderAll();
    toast("Usunięto");
    trySync();
  }

  function categoriesModal() {
    const list = state.categories
      .map(
        (c) => `
        <div class="cat-manage-item">
          <span class="cat-dot" style="background:${c.color}"></span>
          <span>${c.name}</span>
          <button class="btn-link small" data-delcat="${c.id}">Usuń</button>
        </div>`
      )
      .join("");
    openModal(`
      <h3>Kategorie</h3>
      <div>${list || '<p class="muted">Brak kategorii.</p>'}</div>
      <div class="modal-row" style="margin-top:14px">
        <label><span>Nowa kategoria</span><input id="c-name" type="text" maxlength="80" placeholder="np. Zakupy"></label>
        <label><span>Kolor</span><input id="c-color" type="color" value="#0e8c6b"></label>
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="c-close">Zamknij</button>
        <button class="btn btn-primary" id="c-add">Dodaj</button>
      </div>
    `);
    $("c-close").addEventListener("click", closeModal);
    $("c-add").addEventListener("click", addCategory);
    document.querySelectorAll("[data-delcat]").forEach((btn) =>
      btn.addEventListener("click", () => deleteCategory(Number(btn.dataset.delcat)))
    );
  }

  async function addCategory() {
    const name = $("c-name").value.trim();
    if (!name) { toast("Podaj nazwę", true); return; }
    if (!navigator.onLine) { toast("Kategorie wymagają połączenia", true); return; }
    try {
      await API.request("/categories", { method: "POST", body: { name, color: $("c-color").value } });
      await Sync.run();
      await loadLocal();
      renderAll();
      categoriesModal();
    } catch (err) {
      toast(err.detail || "Nie udało się dodać", true);
    }
  }

  async function deleteCategory(id) {
    if (!navigator.onLine) { toast("Kategorie wymagają połączenia", true); return; }
    try {
      await API.request(`/categories/${id}`, { method: "DELETE" });
      await Sync.run();
      await loadLocal();
      renderAll();
      categoriesModal();
    } catch (err) {
      toast(err.detail || "Nie udało się usunąć", true);
    }
  }

  function budgetModal() {
    const period = new Date().toISOString().slice(0, 7);
    const options = state.categories.map((c) => `<option value="${c.id}">${c.name}</option>`).join("");
    openModal(`
      <h3>Nowy budżet</h3>
      <label><span>Miesiąc (RRRR-MM)</span><input id="b-period" type="text" value="${period}" pattern="\\d{4}-\\d{2}"></label>
      <label><span>Limit (zł)</span><input id="b-limit" type="number" min="1" step="0.01" placeholder="np. 600"></label>
      <label><span>Kategoria (opcjonalnie)</span><select id="b-category"><option value="">Cały budżet</option>${options}</select></label>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="b-cancel">Anuluj</button>
        <button class="btn btn-primary" id="b-save">Zapisz</button>
      </div>
    `);
    $("b-cancel").addEventListener("click", closeModal);
    $("b-save").addEventListener("click", saveBudget);
  }

  async function saveBudget() {
    if (!navigator.onLine) { toast("Budżety wymagają połączenia", true); return; }
    const limit = Number($("b-limit").value);
    if (!limit || limit <= 0) { toast("Podaj limit", true); return; }
    try {
      await API.request("/budgets", {
        method: "POST",
        body: {
          period: $("b-period").value,
          limit_amount: limit,
          category_id: $("b-category").value ? Number($("b-category").value) : null,
        },
      });
      await Sync.run();
      await loadLocal();
      renderAll();
      closeModal();
      toast("Dodano budżet");
    } catch (err) {
      toast(err.detail || "Nie udało się dodać", true);
    }
  }

  async function trySync() {
    if (!navigator.onLine) return;
    setSyncPill("syncing");
    try {
      const result = await Sync.run();
      await loadLocal();
      renderAll();
      setSyncPill(navigator.onLine ? "online" : "offline");
      if (result.conflicts > 0) {
        toast(`Rozwiązano konflikty: ${result.conflicts} (zachowano nowszą wersję)`, true);
      }
    } catch (err) {
      setSyncPill(navigator.onLine ? "online" : "offline");
      if (!(err instanceof API.OfflineError)) toast(err.detail || "Błąd synchronizacji", true);
    }
  }

  function bindAppEvents() {
    $("add-expense-btn").addEventListener("click", () => { state.editingUuid = null; expenseModal(null); });
    $("add-budget-btn").addEventListener("click", budgetModal);
    $("manage-categories-btn").addEventListener("click", categoriesModal);
    $("logout-btn").addEventListener("click", () => { Auth.logout(); location.reload(); });

    $("expense-list").addEventListener("click", (e) => {
      const editId = e.target.dataset.edit;
      const delId = e.target.dataset.delete;
      if (editId) {
        DB.get("expenses", editId).then((rec) => { state.editingUuid = editId; expenseModal(rec); });
      } else if (delId) {
        deleteExpense(delId);
      }
    });

    $("modal-backdrop").addEventListener("click", (e) => {
      if (e.target.id === "modal-backdrop") closeModal();
    });

    const filterInputs = {
      q: "filter-q", category_id: "filter-category", from: "filter-from",
      to: "filter-to", min: "filter-min", max: "filter-max",
    };
    for (const [key, id] of Object.entries(filterInputs)) {
      $(id).addEventListener("input", () => { state.filters[key] = $(id).value; renderList(); });
    }
    $("filter-clear").addEventListener("click", () => {
      Object.keys(state.filters).forEach((k) => (state.filters[k] = ""));
      Object.values(filterInputs).forEach((id) => ($(id).value = ""));
      renderList();
    });

    window.addEventListener("online", () => { setSyncPill("online"); trySync(); });
    window.addEventListener("offline", () => setSyncPill("offline"));
    window.addEventListener("auth:expired", () => { toast("Sesja wygasła", true); setTimeout(() => location.reload(), 1200); });
  }

  async function startApp() {
    $("login-view").hidden = true;
    $("app-view").hidden = false;
    setSyncPill(navigator.onLine ? "online" : "offline");
    bindAppEvents();
    await loadLocal();
    renderAll();
    await trySync();
  }

  function bindLogin() {
    let registerMode = false;
    const submit = $("login-submit");
    const toggle = $("toggle-mode");
    const errorBox = $("login-error");

    toggle.addEventListener("click", () => {
      registerMode = !registerMode;
      $("register-fields").hidden = !registerMode;
      submit.textContent = registerMode ? "Zarejestruj się" : "Zaloguj się";
      toggle.textContent = registerMode ? "Masz już konto? Zaloguj się" : "Nie masz konta? Zarejestruj się";
      errorBox.hidden = true;
    });

    submit.addEventListener("click", async () => {
      const email = $("login-email").value.trim();
      const password = $("login-password").value;
      errorBox.hidden = true;
      if (!email || !password) { errorBox.textContent = "Podaj email i hasło"; errorBox.hidden = false; return; }
      try {
        if (registerMode) {
          await Auth.register(email, password, $("register-name").value.trim() || email);
        }
        await Auth.login(email, password);
        await startApp();
      } catch (err) {
        errorBox.textContent = err.detail || "Nie udało się zalogować";
        errorBox.hidden = false;
      }
    });

    $("login-password").addEventListener("keydown", (e) => { if (e.key === "Enter") submit.click(); });
  }

  async function init() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("./sw.js").catch(() => {});
    }
    if (Auth.isLoggedIn()) {
      await startApp();
    } else {
      bindLogin();
    }
  }

  return { init };
})();

window.addEventListener("DOMContentLoaded", App.init);
