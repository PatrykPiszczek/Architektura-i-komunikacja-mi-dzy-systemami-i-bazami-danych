const Sync = (() => {
  let running = false;

  async function pushDirty() {
    const local = await DB.getAll("expenses");
    const dirty = local.filter((e) => e.dirty);
    if (dirty.length === 0) return { conflicts: 0 };

    const changes = dirty.map((e) => ({
      client_uuid: e.client_uuid,
      amount: e.amount,
      currency: e.currency,
      description: e.description,
      spent_at: e.spent_at,
      category_id: e.category_id,
      deleted: e.deleted,
      base_version: e.version,
      updated_at: e.updated_at,
    }));

    const response = await API.request("/sync/push", { method: "POST", body: { changes } });

    let conflicts = 0;
    for (const result of response.results) {
      const server = result.expense;
      if (result.status.startsWith("conflict")) conflicts += 1;
      await DB.put("expenses", {
        client_uuid: server.client_uuid,
        server_id: server.id,
        amount: server.amount,
        currency: server.currency,
        description: server.description,
        spent_at: server.spent_at,
        category_id: server.category_id,
        version: server.version,
        deleted: server.deleted,
        updated_at: server.updated_at,
        dirty: false,
      });
    }
    return { conflicts };
  }

  async function pull() {
    const since = await DB.getMeta("lastSync");
    const query = since ? `?since=${encodeURIComponent(since)}` : "";
    const data = await API.request(`/sync/changes${query}`);

    const local = await DB.getAll("expenses");
    const byUuid = Object.fromEntries(local.map((e) => [e.client_uuid, e]));

    for (const server of data.expenses) {
      const existing = byUuid[server.client_uuid];
      if (existing && existing.dirty) continue;
      await DB.put("expenses", {
        client_uuid: server.client_uuid,
        server_id: server.id,
        amount: server.amount,
        currency: server.currency,
        description: server.description,
        spent_at: server.spent_at,
        category_id: server.category_id,
        version: server.version,
        deleted: server.deleted,
        updated_at: server.updated_at,
        dirty: false,
      });
    }

    await DB.setMeta("lastSync", data.server_time);
  }

  async function refreshReferenceData() {
    const categories = await API.request("/categories");
    await DB.replaceAll("categories", categories);
    const period = new Date().toISOString().slice(0, 7);
    const budgets = await API.request(`/budgets/summary?period=${period}`);
    await DB.replaceAll("budgets", budgets);
  }

  async function run() {
    if (running || !navigator.onLine) return { ok: false, offline: !navigator.onLine };
    running = true;
    try {
      const pushResult = await pushDirty();
      await pull();
      await refreshReferenceData();
      return { ok: true, conflicts: pushResult.conflicts };
    } catch (err) {
      if (err instanceof API.OfflineError) return { ok: false, offline: true };
      throw err;
    } finally {
      running = false;
    }
  }

  return { run };
})();
