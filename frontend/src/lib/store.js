import { create } from 'zustand';

const normalizeUser = (user) => {
  if (!user) {
    return null;
  }

  return {
    ...user,
    has_viewed_tutorial: user.has_viewed_tutorial ?? false,
  };
};

export const useAuthStore = create((set) => ({
  user: normalizeUser(JSON.parse(localStorage.getItem('user') || 'null')),
  token: localStorage.getItem('token') || null,
  setAuth: (user, token) => {
    const normalizedUser = normalizeUser(user);
    localStorage.setItem('user', JSON.stringify(normalizedUser));
    localStorage.setItem('token', token);
    set({ user: normalizedUser, token });
  },
  logout: () => {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    set({ user: null, token: null });
  },
  updateUser: (user) => {
    const normalizedUser = normalizeUser(user);
    localStorage.setItem('user', JSON.stringify(normalizedUser));
    set({ user: normalizedUser });
  }
}));
