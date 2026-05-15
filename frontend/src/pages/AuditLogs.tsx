import { useEffect, useState } from "react";
import api from "../services/api";
import { useAuth } from "../auth/AuthContext";


export default function AuditLogs() {
  const { logout } = useAuth();
  const [logs, setLogs] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  useEffect(() => {
    api.get("/audit").then((res) => setLogs(res.data));
  }, []);

  // 🔍 Filter logic
  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      log.username?.toLowerCase().includes(search.toLowerCase()) ||
      log.action?.toLowerCase().includes(search.toLowerCase()) ||
      log.resource?.toLowerCase().includes(search.toLowerCase());

    const logTime = new Date(log.timestamp).getTime();

    const matchesFrom =
      !fromDate || logTime >= new Date(fromDate).getTime();

    const matchesTo =
      !toDate || logTime <= new Date(toDate + "T23:59:59").getTime();

    return matchesSearch && matchesFrom && matchesTo;
  });

  return (
    <div className="p-6 bg-slate-900 min-h-screen text-white">
      
      {/* Header row */}
<div className="flex justify-between items-center mb-6">
  <h1 className="text-4xl font-extrabold">Audit Logs</h1>

  <button
    onClick={logout}
    className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 
               text-white font-semibold text-sm shadow"
  >
    Logout
  </button>
</div>


      {/* Controls row */}
      <div className="flex justify-between items-end mb-6">
        {/* Search box on the left */}
        <div className="flex-1 max-w-sm">
          <label className="block text-sm text-slate-400 mb-1">Search</label>
          <input
            type="text"
            placeholder="Search user, action, resource..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-slate-800 border border-slate-600 rounded px-4 py-2 w-full text-sm focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Date filters on the right */}
        <div className="flex gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">From date</label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-1">To date</label>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Logs table */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-700 text-slate-300 text-sm">
            <tr>
              <th className="p-4 text-left">User</th>
              <th className="p-4 text-left">Action</th>
              <th className="p-4 text-left">Resource</th>
              <th className="p-4 text-left">Time</th>
            </tr>
          </thead>

          <tbody>
            {filteredLogs.map((l, i) => (
              <tr
                key={i}
                className="border-t border-slate-700 hover:bg-slate-700/40"
              >
                <td className="p-4">{l.username}</td>
                <td className="p-4">{l.action}</td>
                <td className="p-4">{l.resource || "-"}</td>
                <td className="p-4 text-sm text-slate-400">
                  {new Date(l.timestamp).toLocaleString()}
                </td>
              </tr>
            ))}

            {filteredLogs.length === 0 && (
              <tr>
                <td colSpan={4} className="p-6 text-center text-slate-400">
                  No audit logs found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
