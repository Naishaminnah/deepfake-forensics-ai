// src/pages/EvidenceAnchorLedgerAdmin.tsx
import React, { useEffect, useState } from "react";
import { Search, Database, XCircle } from "lucide-react";
import { getEvidenceAnchorLedger } from "../services/api"; // GET /admin/evidence-anchor-ledger
import { useAuth } from "../auth/AuthContext";

interface EvidenceAnchorRecord {
  id: number;
  case_id: number;
  evidence_hash: string;
  ipfs_cid: string;
  metadata_hash: string;
  evidence_type: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  blockchain_tx_hash: string;
  registered_by: number;
  created_at: string;
}

const EvidenceAnchorLedgerAdmin: React.FC = () => {
  const { logout } = useAuth();
  const [records, setRecords] = useState<EvidenceAnchorRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    getEvidenceAnchorLedger().then((data) => {
      setRecords(data);
      setLoading(false);
    });
  }, []);

  const filtered = records.filter((r) =>
    Object.values(r)
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  if (loading)
    return (
      <div className="min-h-screen flex items-center justify-center text-white">
        Loading Evidence Anchor Ledger...
      </div>
    );

  return (
    <div className="min-h-screen p-6 bg-slate-900 text-white">
      <h1 className="text-3xl font-bold mb-4 flex items-center gap-2">
        <Database className="text-cyan-400" /> Evidence Anchor Ledger (Blockchain)
      </h1>

      <div className="mb-4 flex justify-between items-center">
        <input
          type="text"
          placeholder="Search any field..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 w-full max-w-sm placeholder:text-slate-400"
        />
        <button
          onClick={logout}
          className="ml-4 px-4 py-2 bg-red-600 rounded-lg hover:bg-red-700 transition"
        >
          Logout
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-700">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-800">
            <tr>
              {[
                "ID",
                "Case ID",
                "File Name",
                "Type",
                "Hash",
                "IPFS CID",
                "Metadata Hash",
                "Blockchain TX",
                "Registered By",
                "Size (B)",
                "MIME",
                "Created At",
              ].map((col) => (
                <th
                  key={col}
                  className="px-4 py-2 text-left text-slate-400 border-b border-slate-700"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={12} className="text-center p-4 text-slate-400">
                  <XCircle className="inline mr-2" /> No records found
                </td>
              </tr>
            )}
            {filtered.map((r) => (
              <tr
                key={r.id}
                className="hover:bg-slate-800 transition border-b border-slate-700"
              >
                <td className="px-4 py-2">{r.id}</td>
                <td className="px-4 py-2">{r.case_id}</td>
                <td className="px-4 py-2">{r.file_name}</td>
                <td className="px-4 py-2">{r.evidence_type}</td>
                <td className="px-4 py-2">{r.evidence_hash}</td>
                <td className="px-4 py-2">{r.ipfs_cid}</td>
                <td className="px-4 py-2">{r.metadata_hash}</td>
                <td className="px-4 py-2">{r.blockchain_tx_hash}</td>
                <td className="px-4 py-2">{r.registered_by}</td>
                <td className="px-4 py-2">{r.file_size}</td>
                <td className="px-4 py-2">{r.mime_type}</td>
                <td className="px-4 py-2">
                  {new Date(r.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default EvidenceAnchorLedgerAdmin;
