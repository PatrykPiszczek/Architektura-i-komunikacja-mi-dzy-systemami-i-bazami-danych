const Auth = (() => {
  async function login(email, password) {
    const data = await API.request("/auth/login", {
      method: "POST",
      form: { username: email, password },
      auth: false,
    });
    API.setToken(data.access_token);
  }

  async function register(email, password, displayName) {
    await API.request("/auth/register", {
      method: "POST",
      body: { email, password, display_name: displayName },
      auth: false,
    });
  }

  function logout() {
    API.clearToken();
  }

  const isLoggedIn = () => Boolean(API.getToken());

  return { login, register, logout, isLoggedIn };
})();
