const SESSION_KEY = 'aivura_admin_session';

export function isAdminLoggedIn(): boolean {
  return sessionStorage.getItem(SESSION_KEY) === '1';
}

export function adminLogin(password: string): boolean {
  const expected = import.meta.env.VITE_ADMIN_PASSWORD || 'aivura2026';
  if (password === expected) {
    sessionStorage.setItem(SESSION_KEY, '1');
    return true;
  }
  return false;
}

export function adminLogout() {
  sessionStorage.removeItem(SESSION_KEY);
}
