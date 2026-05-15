import React, { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

type Props = {
  children: ReactNode;
  roles?: string[];
};

const ProtectedRoute: React.FC<Props> = ({ children, roles }) => {
  const { user, loading } = useAuth();

  // ⏳ Wait for auth state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400">
        Verifying access...
      </div>
    );
  }

  // 🔐 Not logged in → force login (replace removes history)
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // 🛑 Role-based access
  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
