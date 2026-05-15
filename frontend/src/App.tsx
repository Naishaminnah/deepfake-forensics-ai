import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Unauthorized from "./pages/Unauthorized";
import AuditLogs from "./pages/AuditLogs";
import AdminDashboard from "./pages/AdminDashboard";
import AdminUsers from "./pages/AdminUsers";
import JudgeVerification from "./pages/JudgeVerification";
import EvidenceLedgerAdmin from "./pages/EvidenceLedgerAdmin";
import EvidenceAnchorLedgerAdmin from "./pages/EvidenceAnchorLedgerAdmin";

const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>

          {/* PUBLIC */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* ROOT → USER DASHBOARD */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Navigate to="/dashboard" replace />
              </ProtectedRoute>
            }
          />

          {/* USER DASHBOARD */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Home />
              </ProtectedRoute>
            }
          />

          {/* ADMIN */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute roles={["ADMIN"]}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/audit"
            element={
              <ProtectedRoute roles={["ADMIN"]}>
                <AuditLogs />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/users"
            element={
              <ProtectedRoute roles={["ADMIN"]}>
                <AdminUsers />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/evidence-ledger"
            element={
              <ProtectedRoute roles={["ADMIN"]}>
                <EvidenceLedgerAdmin />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin/evidence-anchor-ledger"
            element={
              <ProtectedRoute roles={["ADMIN"]}>
                <EvidenceAnchorLedgerAdmin />
              </ProtectedRoute>
            }
          />

          {/* LEGAL AUTHORITY */}
          <Route
            path="/verify"
            element={
              <ProtectedRoute roles={["LEGAL_AUTHORITY"]}>
                <JudgeVerification />
              </ProtectedRoute>
            }
          />

          <Route path="/unauthorized" element={<Unauthorized />} />

          {/* FALLBACK */}
          <Route path="*" element={<Navigate to="/login" replace />} />

        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
