(function() {
  // Hide everything until we confirm JWT
  document.documentElement.style.display = 'none';

  function parseJwt(token) {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));
      return JSON.parse(jsonPayload);
    } catch (e) { return null; }
  }

  function isExpired(token) {
    const payload = parseJwt(token);
    if (!payload || !payload.exp) return true;
    const now = Math.floor(Date.now() / 1000);
    return payload.exp <= (now + 10);
  }

  async function refreshAccessToken() {
    const refresh = localStorage.getItem('refresh');
    if (!refresh) return false;
    try {
      const res = await fetch('/api/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh })
      });
      if (!res.ok) return false;
      const data = await res.json();
      if (data.access) {
        localStorage.setItem('access', data.access);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  async function ensureAuthOrRedirect() {
    const access = localStorage.getItem('access');
    const refresh = localStorage.getItem('refresh');

    if (!access || !refresh) {
      window.location.replace('/api/auth/jwt-login/');
      return;
    }

    if (isExpired(access)) {
      const ok = await refreshAccessToken();
      if (!ok) {
        localStorage.removeItem('access');
        localStorage.removeItem('refresh');
        window.location.replace('/api/auth/jwt-login/');
        return;
      }
    }

    // ✅ Auth confirmed — show page
    document.documentElement.style.display = '';
  }

  ensureAuthOrRedirect();

  window.authFetch = async function(url, options = {}, allowRetry = true) {
    let access = localStorage.getItem('access');
    if (!access || isExpired(access)) {
      const ok = await refreshAccessToken();
      if (!ok) {
        window.location.replace('/api/auth/jwt-login/');
        throw new Error('Not authenticated');
      }
      access = localStorage.getItem('access');
    }

    const headers = options.headers ? {...options.headers} : {};
    headers['Authorization'] = `Bearer ${access}`;
    if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(url, { ...options, headers });

    if (res.status === 401 && allowRetry) {
      const ok = await refreshAccessToken();
      if (!ok) {
        localStorage.removeItem('access');
        localStorage.removeItem('refresh');
        window.location.replace('/api/auth/jwt-login/');
        throw new Error('Session expired');
      }
      return window.authFetch(url, options, false);
    }

    return res;
  };

  window.logout = function() {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    window.location.replace('/api/auth/jwt-login/');
  };
})();
