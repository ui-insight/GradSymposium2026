import { useState, useEffect, type ReactNode } from 'react';
import { apiFetch } from '../../api/client';
import { storage } from '../../utils/storage';
import { AuthContext } from './auth-context';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    !!storage.getItem('access_token')
  );
  const [role, setRole] = useState<'admin' | 'judge' | null>(
    storage.getItem('user_role') as 'admin' | 'judge' | null
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
    storage.setItem('access_token', token);
    storage.setItem('user_role', r);
    setIsAuthenticated(true);
    setRole(r);
  };

  const logout = () => {
    storage.removeItem('access_token');
    storage.removeItem('user_role');
    setIsAuthenticated(false);
    setRole(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, role, user, login, logout, updateUser: setUser }}>
      {children}
    </AuthContext.Provider>
  );
}
