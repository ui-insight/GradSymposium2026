import { createContext } from 'react';

export interface AuthState {
  isAuthenticated: boolean;
  role: 'admin' | 'judge' | null;
  user: { name: string; id: string } | null;
  login: (token: string, role: 'admin' | 'judge') => void;
  logout: () => void;
  updateUser: (user: { name: string; id: string }) => void;
}

export const AuthContext = createContext<AuthState>({
  isAuthenticated: false,
  role: null,
  user: null,
  login: () => {},
  logout: () => {},
  updateUser: () => {},
});
