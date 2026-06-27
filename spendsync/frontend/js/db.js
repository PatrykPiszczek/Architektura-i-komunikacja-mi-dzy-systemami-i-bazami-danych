const DB = (() => {
  const NAME = "spendsync";
  const VERSION = 1;
  let dbPromise = null;

  function open() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(NAME, VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains("expenses")) {
          db.createObjectStore("expenses", { keyPath: "client_uuid" });
        }
        if (!db.objectStoreNames.contains("categories")) {
          db.createObjectStore("categories", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("budgets")) {
          db.createObjectStore("budgets", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("meta")) {
          db.createObjectStore("meta", { keyPath: "key" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    return dbPromise;
  }

  function tx(store, mode, action) {
    return open().then(
      (db) =>
        new Promise((resolve, reject) => {
          const transaction = db.transaction(store, mode);
          const result = action(transaction.objectStore(store));
          transaction.oncomplete = () => resolve(result.value);
          transaction.onerror = () => reject(transaction.error);
        })
    );
  }

  const wrap = (req) => {
    const box = {};
    req.onsuccess = () => (box.value = req.result);
    return box;
  };

  return {
    getAll: (store) => tx(store, "readonly", (s) => wrap(s.getAll())),
    get: (store, key) => tx(store, "readonly", (s) => wrap(s.get(key))),
    put: (store, value) => tx(store, "readwrite", (s) => wrap(s.put(value))),
    delete: (store, key) => tx(store, "readwrite", (s) => wrap(s.delete(key))),
    clear: (store) => tx(store, "readwrite", (s) => wrap(s.clear())),
    async replaceAll(store, items) {
      const db = await open();
      return new Promise((resolve, reject) => {
        const transaction = db.transaction(store, "readwrite");
        const os = transaction.objectStore(store);
        os.clear();
        items.forEach((item) => os.put(item));
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(transaction.error);
      });
    },
    async getMeta(key, fallback = null) {
      const row = await tx("meta", "readonly", (s) => wrap(s.get(key)));
      return row ? row.value : fallback;
    },
    setMeta: (key, value) => tx("meta", "readwrite", (s) => wrap(s.put({ key, value }))),
  };
})();
