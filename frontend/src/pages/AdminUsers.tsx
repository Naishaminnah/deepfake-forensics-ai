import React, { useEffect, useState } from "react";
import {
  Shield,
  ArrowLeft,
  UserCheck,
  UserX,
  Plus,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  getAdminUsers,
  toggleUserStatus,
  createUser,
  getCurrentUsername,
} from "../services/api";

interface User {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
}

const AdminUsers: React.FC = () => {
  const navigate = useNavigate();
  const currentUsername = getCurrentUsername();

  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");

  // Create user modal
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState("");

  const [newUser, setNewUser] = useState<{
    username: string;
    password: string;
    role: "FORENSIC_ANALYST" | "LEGAL_AUTHORITY";
  }>({
    username: "",
    password: "",
    role: "FORENSIC_ANALYST",
  });

  const fetchUsers = async () => {
    const data = await getAdminUsers();
    setUsers(data);
    setLoading(false);
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // 🔁 Reset modal state cleanly
  const openCreateModal = () => {
    setError("");
    setNewUser({
      username: "",
      password: "",
      role: "FORENSIC_ANALYST",
    });
    setShowCreate(true);
  };

  const closeCreateModal = () => {
    setError("");
    setShowCreate(false);
  };

  const handleCreateUser = async () => {
    try {
      await createUser(newUser);
      setError("");
      setShowCreate(false);
      setNewUser({
        username: "",
        password: "",
        role: "FORENSIC_ANALYST",
      });
      fetchUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create user");
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchSearch = u.username
      .toLowerCase()
      .includes(search.toLowerCase());

    const matchRole =
      roleFilter === "ALL" || u.role === roleFilter;

    const matchStatus =
      statusFilter === "ALL" ||
      (statusFilter === "ACTIVE" && u.is_active) ||
      (statusFilter === "DISABLED" && !u.is_active);

    return matchSearch && matchRole && matchStatus;
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-white">
        Loading users...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white p-6">

      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6 flex justify-between">
        <div className="flex items-center gap-3">
          <Shield className="text-blue-400" />
          <h1 className="text-2xl font-bold">User Management</h1>
        </div>

        <div className="flex gap-3">
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 rounded hover:bg-blue-700"
          >
            <Plus size={16} />
            Create User
          </button>

          <button
            onClick={() => navigate("/admin")}
            className="flex items-center gap-2 px-4 py-2 border border-slate-600 rounded hover:bg-slate-800"
          >
            <ArrowLeft size={16} />
            Back
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-7xl mx-auto mb-4 flex gap-4">
        <input
          placeholder="Search username..."
          className="bg-slate-800 border border-slate-600 rounded px-3 py-2 w-1/3"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <select
          className="bg-slate-800 border border-slate-600 rounded px-3 py-2"
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
        >
          <option value="ALL">All Roles</option>
          <option value="ADMIN">ADMIN</option>
          <option value="FORENSIC_ANALYST">FORENSIC_ANALYST</option>
          <option value="LEGAL_AUTHORITY">LEGAL_AUTHORITY</option>
        </select>

        <select
          className="bg-slate-800 border border-slate-600 rounded px-3 py-2"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="ALL">All Status</option>
          <option value="ACTIVE">Active</option>
          <option value="DISABLED">Disabled</option>
        </select>
      </div>

      {/* Users Table */}
      <div className="max-w-7xl mx-auto bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-700 text-sm text-slate-300">
            <tr>
              <th className="p-4 text-left">Username</th>
              <th className="p-4 text-left">Role</th>
              <th className="p-4 text-left">Status</th>
              <th className="p-4 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((u) => (
              <tr key={u.id} className="border-t border-slate-700">
                <td className="p-4">{u.username}</td>
                <td className="p-4">
                  <div className="inline-block bg-slate-900 border border-slate-600 rounded px-3 py-1 text-sm">
                    {u.role}
                  </div>
                </td>
                <td className="p-4">
                  {u.is_active ? (
                    <span className="text-green-400">Active</span>
                  ) : (
                    <span className="text-red-400">Disabled</span>
                  )}
                </td>
                <td className="p-4">
                  {u.username === currentUsername ? (
                    <span className="text-slate-400 text-sm italic">
                      Cannot disable self
                    </span>
                  ) : (
                    <button
                      onClick={() => toggleUserStatus(u.id).then(fetchUsers)}
                      className={`flex items-center gap-1 px-3 py-1 rounded text-sm ${
                        u.is_active
                          ? "bg-red-500/20 text-red-400"
                          : "bg-green-500/20 text-green-400"
                      }`}
                    >
                      {u.is_active ? <UserX size={14} /> : <UserCheck size={14} />}
                      {u.is_active ? "Disable" : "Enable"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create User Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center">
          <div className="bg-slate-800 p-6 rounded-xl w-96">
            <h2 className="text-xl font-bold mb-4">Create User</h2>

            {error && (
              <div className="mb-3 text-red-400 text-sm">
                {error}
              </div>
            )}

            <input
              placeholder="Username"
              className="w-full mb-3 p-2 bg-slate-900 border border-slate-600 rounded"
              value={newUser.username}
              onChange={(e) => {
                setError("");
                setNewUser({ ...newUser, username: e.target.value });
              }}
            />

            <input
              type="password"
              placeholder="Password"
              className="w-full mb-3 p-2 bg-slate-900 border border-slate-600 rounded"
              value={newUser.password}
              onChange={(e) => {
                setError("");
                setNewUser({ ...newUser, password: e.target.value });
              }}
            />

            <select
              className="w-full mb-4 p-2 bg-slate-900 border border-slate-600 rounded"
              value={newUser.role}
              onChange={(e) =>
                setNewUser({
                  ...newUser,
                  role: e.target.value as
                    | "FORENSIC_ANALYST"
                    | "LEGAL_AUTHORITY",
                })
              }
            >
              <option value="FORENSIC_ANALYST">FORENSIC_ANALYST</option>
              <option value="LEGAL_AUTHORITY">LEGAL_AUTHORITY</option>
            </select>

            <div className="flex justify-end gap-3">
              <button onClick={closeCreateModal}>Cancel</button>
              <button
                onClick={handleCreateUser}
                className="bg-blue-600 px-4 py-2 rounded"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminUsers;
