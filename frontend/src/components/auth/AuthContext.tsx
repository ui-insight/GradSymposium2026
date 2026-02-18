import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { apiFetch } from '../../api/client';

interface AuthState {
  isAuthenticated: boolean;
  role: 'admin' | 'judge' | null;
  user: { name: string; id: string } | null;
  login: (token: string, role: 'admin' | 'judge') => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  isAuthenticated: false,
  role: null,
  user: null,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('access_token'));
  const [role, setRole] = useState<'admin' | 'judge' | null>(
    localStorage.getItem('user_role') as 'admin' | 'judge' | null
  );
  const [user, setUser] = useState<{ name: string; id: string } | null>(null);

  useEffect(() => {
    if (isAuthenticated && role === 'admin') {
      apiFetch<{ User_ID: string; Username: string }>('/auth/me')
        .then(data => setUser({ name: data.Username, id: data.User_ID }))
        .catch(() => { setIsAuthenticated(false); setRole(null); });
    } else if (isAuthenticated && role === 'judge') {
      apiFetch<{ Judge_ID: string; First_Name: string; Last_Name: string }>('/judge/me')
        .then(data => setUser({ name: `${data.First_Name} ${data.Last_Name}`, id: data.Judge_ID }))
        .catch(() => { setIsAuthenticated(false); setRole(null); });
    }
  }, [isAuthenticated, role]);

  const login = (token: string, r: 'admin' | 'judge') => {
    localStorage.setItem('access_token', token);
    localStorage.setItem('user_role', r);
    setIsAuthenticated(true);
    setRole(r);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    setIsAuthenticated(false);
    setRole(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, role, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
