import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

export function ProtectedRoute({
  children,
  requiredRole,
}: {
  children: React.ReactNode;
  requiredRole: 'admin' | 'judge';
}) {
  const { isAuthenticated, role } = useAuth();

  if (!isAuthenticated || role !== requiredRole) {
    const redirect = requiredRole === 'admin' ? '/admin/login' : '/judge';
    return <Navigate to={redirect} replace />;
  }

  return <>{children}</>;
}
