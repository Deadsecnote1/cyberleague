export type UserRecord = {
  id: string;
  name: string;
  telegramChatId: string;
  studentId?: string;
  department?: string;
  active: boolean;
  addedAt: string;
  lastSeen?: string;
  messageCount: number;
};

export type ActivityLog = {
  id: string;
  time: string;
  user: string;
  intent: string;
  status: 'success' | 'partial' | 'error' | 'denied';
  preview: string;
};

export type PortalSettings = {
  notionUsersDbId: string;
  telegramBotName: string;
};

const KEYS = { users: 'aivura_students', activity: 'aivura_activity', settings: 'aivura_settings' };

const defaultUsers: UserRecord[] = [];

const defaultActivity: ActivityLog[] = [];

function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function save<T>(key: string, data: T) {
  localStorage.setItem(key, JSON.stringify(data));
}

export function getUsers() {
  return load(KEYS.users, defaultUsers);
}

export function saveUsers(users: UserRecord[]) {
  save(KEYS.users, users);
}

export function addUser(user: Omit<UserRecord, 'id' | 'addedAt' | 'messageCount'>) {
  const entry: UserRecord = { ...user, id: crypto.randomUUID(), addedAt: new Date().toISOString().split('T')[0], messageCount: 0 };
  const users = [...getUsers(), entry];
  saveUsers(users);
  return entry;
}

export function updateUser(id: string, patch: Partial<UserRecord>) {
  const users = getUsers().map((u) => (u.id === id ? { ...u, ...patch } : u));
  saveUsers(users);
  return users;
}

export function deleteUser(id: string) {
  const users = getUsers().filter((u) => u.id !== id);
  saveUsers(users);
  return users;
}

export function getActivity() {
  return load(KEYS.activity, defaultActivity);
}

export function getSettings() {
  return load(KEYS.settings, { notionUsersDbId: '', telegramBotName: '@Aivura_bot' });
}

export function saveSettings(s: PortalSettings) {
  save(KEYS.settings, s);
}

export function exportUsersForNotion() {
  return getUsers().map((u) => ({
    Name: u.name,
    'Telegram Chat ID': u.telegramChatId,
    Role: 'student',
    Active: u.active,
    Department: u.department || '',
    'Student ID': u.studentId || '',
  }));
}
