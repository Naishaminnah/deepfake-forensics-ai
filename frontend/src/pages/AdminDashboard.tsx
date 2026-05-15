import React, { useEffect, useState } from "react";
import {
  Shield,
  Users,
  FileSearch,
  Activity,
  Database,
  LogOut,
  AlertTriangle,

} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { useNavigate } from "react-router-dom";
import { getAdminSummary } from "../services/api";

interface AdminSummary {
  users: {
    total: number;
    by_role: Record<string, number>;
  };
  audit: {
    total_events: number;
    actions: Record<string, number>;
    last_24h: number;
  };
  system: {
    status: string;
  };
}

const AdminDashboard: React.FC = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAdminSummary()
      .then(setSummary)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-white">
        Loading admin metrics...
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="min-h-screen flex items-center justify-center text-red-400">
        Failed to load admin data
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-10 h-10 text-blue-400" />
          <div>
            <h1 className="text-3xl font-bold">Admin Control Panel</h1>
            <p className="text-sm text-slate-400">
              Real-time system governance & forensic oversight
            </p>
          </div>
        </div>

        <button
          onClick={logout}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-500 hover:bg-slate-700 transition"
        >
          <LogOut size={16} />
          Logout
        </button>
      </div>

      {/* Stats */}
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
        <StatCard
          icon={<Activity className="text-green-400" />}
          title="System Status"
          value={summary.system.status}
          sub="Backend services"
        />

        <StatCard
          icon={<Users className="text-yellow-400" />}
          title="Total Users"
          value={String(summary.users.total)}
          sub="Registered accounts"
        />

        <StatCard
          icon={<Database className="text-purple-400" />}
          title="Audit Events"
          value={String(summary.audit.total_events)}
          sub="Logged system actions"
        />

        <StatCard
          icon={<FileSearch className="text-blue-400" />}
          title="Events (24h)"
          value={String(summary.audit.last_24h)}
          sub="Recent activity"
        />

        <StatCard
          icon={<AlertTriangle className="text-red-400" />}
          title="Failed Logins"
          value={String(summary.audit.actions["FAILED_LOGIN"] ?? 0)}
          sub="Suspicious activity"
        />

        <StatCard
          icon={<Shield className="text-cyan-400" />}
          title="Admins"
          value={String(summary.users.by_role["ADMIN"] ?? 0)}
          sub="Privileged users"
        />
      </div>

      {/* Actions */}
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
        <AdminAction
          title="Audit Logs"
          description="View authentication, evidence access & admin actions"
          onClick={() => navigate("/audit")}
        />

        <AdminAction
         title="User Management"
         description="Role assignment and account control"
         onClick={() => navigate("/admin/users")}
        />


        <AdminAction
         title="Detection Analytics"
         description="Deepfake trends & detector performance"
         onClick={() => navigate("/admin/evidence-ledger")}
        />

       <AdminAction
        title="Blockchain Verification"
        description="Evidence integrity & chain-of-custody"
        onClick={() => navigate("/admin/evidence-anchor-ledger")}
      />

      </div>
    </div>
  );
};

export default AdminDashboard;

/* =======================
   UI COMPONENTS
======================= */

const StatCard = ({
  icon,
  title,
  value,
  sub,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  sub: string;
}) => (
  <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-lg">
    <div className="flex items-center gap-3 mb-3">
      {icon}
      <h3 className="font-semibold text-lg">{title}</h3>
    </div>
    <p className="text-3xl font-bold">{value}</p>
    <p className="text-sm text-slate-400 mt-1">{sub}</p>
  </div>
);

const AdminAction = ({
  title,
  description,
  onClick,
  disabled,
}: {
  title: string;
  description: string;
  onClick?: () => void;
  disabled?: boolean;
}) => (
  <div
    onClick={!disabled ? onClick : undefined}
    className={`bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-lg transition
      ${disabled ? "opacity-50 cursor-not-allowed" : "hover:bg-slate-700 cursor-pointer"}`}
  >
    <h3 className="text-xl font-semibold mb-2">{title}</h3>
    <p className="text-slate-400 text-sm">{description}</p>
    {disabled && (
      <p className="mt-2 text-xs text-yellow-400">Coming soon</p>
    )}
  </div>
);

