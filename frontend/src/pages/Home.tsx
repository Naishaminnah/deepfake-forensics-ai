import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

import DeepfakeForensicsDashboard from "../components/DeepfakeForensicsDashboard";
import UserDeepfakeDashboard from "../components/UserDeepfakeDashboard";

const Home: React.FC = () => {
  const { user } = useAuth();

  // 🚨 Not logged in → go to login
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // 👩‍⚖️ Judge / Legal Authority
  if (user.role === "LEGAL_AUTHORITY") {
    return <Navigate to="/verify" replace />;
  }

  // 🧑 Normal user (no cases, no blockchain)
  if (user.role === "USER") {
    return <UserDeepfakeDashboard />;
  }

  // 🧪 Forensic Analyst (full system)
  if (user.role === "FORENSIC_ANALYST") {
    return <DeepfakeForensicsDashboard />;
  }
   // 🧪 Forensic Analyst (full system)
  if (user.role === "ADMIN") {
    return <Navigate to="/admin" replace/>;
  }

  // ❌ Fallback safety
  return <Navigate to="/unauthorized" replace />;
};

export default Home;
