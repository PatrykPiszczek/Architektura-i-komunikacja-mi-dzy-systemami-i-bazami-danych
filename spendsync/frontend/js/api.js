const API = (() => {
  const BASE = window.SPENDSYNC_API || "/api";
  const TOKEN_KEY = "spendsync_token";

  const getToken = () => localStorage.getItem(TOKEN_KEY);
  const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
  const clearToken = () => localStorage.removeItem(TOKEN_KEY);

  class OfflineError extends Error {}
  class HttpError extends Error {
    constructor(status, detail) {
      super(detail);
      this.status = status;
      this.detail = detail;
    }
  }

  async function request(path, { method = "GET", body, form, auth = true } = {}) {
    const headers = {};
    if (auth && getToken()) headers["Authorization"] = `Bearer ${getToken()}`;

    let payload;
    if (form) {
      headers["Content-Type"] = "application/x-www-form-urlencoded";
      payload = new URLSearchParams(form).toString();
    } else if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetch(`${BASE}${path}`, { method, headers, body: payload });
    } catch (err) {
      throw new OfflineError("Brak połączenia z serwerem");
    }

    if (response.status === 401 && auth) {
      clearToken();
      window.dispatchEvent(new Event("auth:expired"));
      throw new HttpError(401, "Sesja wygasła");
    }

    if (response.status === 204) return null;

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new HttpError(response.status, data.detail || "Wystąpił błąd");
    }
    return data;
  }

  return { request, getToken, setToken, clearToken, OfflineError, HttpError };
})();
