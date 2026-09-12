/**
 * Authentication Module
 * Manages JWT tokens, user state, login, registration, and logout.
 */

const Auth = {
  getToken() {
    return localStorage.getItem('billsplitter_token');
  },

  getUser() {
    const userStr = localStorage.getItem('billsplitter_user');
    try {
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  },

  isAuthenticated() {
    return !!this.getToken();
  },

  async login(email, password) {
    const res = await API.post('/auth/login', { email, password });
    if (res.success && res.data) {
      localStorage.setItem('billsplitter_token', res.data.token);
      localStorage.setItem(
        'billsplitter_user',
        JSON.stringify({
          _id: res.data._id,
          name: res.data.name,
          email: res.data.email,
        })
      );
      return res.data;
    }
    throw new Error(res.message || 'Login failed');
  },

  async register(name, email, password, confirmPassword) {
    const res = await API.post('/auth/register', {
      name,
      email,
      password,
      confirmPassword,
    });
    if (res.success && res.data) {
      localStorage.setItem('billsplitter_token', res.data.token);
      localStorage.setItem(
        'billsplitter_user',
        JSON.stringify({
          _id: res.data._id,
          name: res.data.name,
          email: res.data.email,
        })
      );
      return res.data;
    }
    throw new Error(res.message || 'Registration failed');
  },

  logout() {
    localStorage.removeItem('billsplitter_token');
    localStorage.removeItem('billsplitter_user');
    window.location.href = 'login.html';
  },

  requireAuth() {
    if (!this.isAuthenticated()) {
      window.location.href = 'login.html';
      return false;
    }
    return true;
  },

  initUserHeader() {
    const user = this.getUser();
    if (user) {
      const nameEl = document.getElementById('userName');
      const avatarEl = document.getElementById('userAvatar');
      if (nameEl) nameEl.textContent = user.name;
      if (avatarEl) avatarEl.textContent = user.name.charAt(0).toUpperCase();
    }

    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => {
        Auth.logout();
      });
    }
  },
};
