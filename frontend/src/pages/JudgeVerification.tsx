import { useState } from "react";
import {
  Gavel,
  UploadCloud,
  ShieldCheck,
  AlertTriangle,
  FileSearch,
  LogOut,
} from "lucide-react";

import api from "../services/api";
import { useAuth } from "../auth/AuthContext";

type VerificationResult = {
  verdict: "MATCH" | "MISMATCH";
  uploaded_hash: string;
  blockchain_hash: string;
  ipfs_hash: string;
  ipfs_cid: string;
  registered_by: string;
  timestamp: number;
  tx_hash: string;
};

export default function JudgeVerification() {
  const { logout } = useAuth();

  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [ledgerRecord, setLedgerRecord] = useState<any | null>(null);
  const [ledgerLoading, setLedgerLoading] = useState(false);

  // ⭐ NEW: Case filter
  const [caseFilter, setCaseFilter] = useState("");

  const fetchLocalLedger = async () => {
    if (!result) return;

    setLedgerLoading(true);
    try {
      const res = await api.get(
        `/evidence/anchor/by-hash/${result.uploaded_hash}`
      );
      setLedgerRecord(res.data);
    } catch {
      setLedgerRecord(null);
    } finally {
      setLedgerLoading(false);
    }
  };

  const handleVerify = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);

    setLedgerRecord(null);
    setLedgerLoading(false);
    setCaseFilter("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await api.post<VerificationResult>(
        "/forensics/verify",
        formData
      );

      setResult(res.data);
    } catch (err: any) {
      const message =
        err.response?.data?.detail ||
        err.message ||
        "Verification failed";

      setError(message);
    } finally {
      setLoading(false);
    }
  };

  // ⭐ Filtered case records
  const filteredCases =
    ledgerRecord?.cases?.filter((c: any) =>
      caseFilter
        ? String(c.case_id).includes(caseFilter.trim())
        : true
    ) || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-8">
      {/* HEADER */}
      <div className="max-w-7xl mx-auto mb-10 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Gavel className="w-12 h-12 text-red-400" />
          <div>
            <h1 className="text-4xl font-bold">
              Court Evidence Verification
            </h1>
            <p className="text-slate-400">
              Judicial-grade integrity validation · Blockchain + IPFS
            </p>
          </div>
        </div>

        <button
          onClick={logout}
          className="flex items-center gap-2 px-4 py-2 rounded-lg
                     bg-slate-700 hover:bg-slate-600 transition"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* LEFT PANEL */}
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-8 shadow-xl">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <UploadCloud className="text-blue-400" />
            Upload Evidence
          </h2>

          <p className="text-sm text-slate-400 mb-6">
            Accepted formats: image, video, audio
            <br />
            This operation is <b>read-only</b>.
          </p>

          <input
            type="file"
            accept="image/*,video/*,audio/*"
            onChange={(e) => {
              if (!e.target.files) return;

              setFile(e.target.files[0]);
              setResult(null);
              setLedgerRecord(null);
              setLedgerLoading(false);
              setError(null);
              setCaseFilter("");
            }}
            className="w-full text-sm text-slate-300
                       file:mr-4 file:py-2 file:px-4
                       file:rounded-lg file:border-0
                       file:bg-slate-700 file:text-white
                       hover:file:bg-slate-600 mb-6"
          />

          <button
            onClick={handleVerify}
            disabled={!file || loading}
            className="w-full py-3 rounded-lg font-semibold
                       bg-red-600 hover:bg-red-700
                       disabled:opacity-50 transition"
          >
            {loading ? "Verifying Evidence…" : "Verify Evidence"}
          </button>

          {error && (
            <div className="mt-6 p-4 bg-red-900/40 border border-red-700 rounded-lg flex gap-3">
              <AlertTriangle className="text-red-400" />
              <div>
                <p className="font-semibold text-red-300">
                  Verification Error
                </p>
                <p className="text-sm">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT PANEL */}
        <div className="bg-slate-800 border border-slate-700 rounded-2xl p-8 shadow-xl">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <ShieldCheck className="text-green-400" />
            Verification Result
          </h2>

          {!result && (
            <div className="text-slate-400 text-sm flex items-center gap-2">
              <FileSearch />
              Awaiting evidence verification…
            </div>
          )}

          {result && (
            <>
              <div
                className={`mb-6 p-4 rounded-lg border text-lg font-bold ${
                  result.verdict === "MATCH"
                    ? "bg-green-900/40 border-green-600 text-green-300"
                    : "bg-yellow-900/40 border-yellow-600 text-yellow-300"
                }`}
              >
                Verdict: {result.verdict}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <Info label="Uploaded File Hash" value={result.uploaded_hash} />
                <Info label="Blockchain Hash" value={result.blockchain_hash} />
                <Info label="IPFS Retrieved Hash" value={result.ipfs_hash} />
                <Info label="IPFS CID" value={result.ipfs_cid} />
              </div>
            </>
          )}
        </div>
      </div>

      {/* ⭐ CASE EVIDENCE RECORD SECTION */}
      {result && (
        <div className="mt-8 border-t border-slate-700 pt-6">
          <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <FileSearch className="text-blue-400" />
            Case Evidence Record (Local Ledger)
          </h3>

          <button
            onClick={fetchLocalLedger}
            disabled={ledgerLoading}
            className="mb-6 px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 transition"
          >
            {ledgerLoading ? "Checking Ledger…" : "Verify Against Local Ledger"}
          </button>

          {ledgerRecord?.status === "FOUND" && (
            <>
              {/* ⭐ CASE FILTER SEARCH */}
              <div className="mb-6 max-w-xs">
                <label className="block text-sm text-slate-400 mb-1">
                  Filter by Case ID
                </label>
                <input
                  type="text"
                  placeholder="Enter case ID..."
                  value={caseFilter}
                  onChange={(e) => setCaseFilter(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm"
                />
              </div>

              {/* ⭐ CASE CARDS */}
              {filteredCases.length === 0 && (
                <div className="text-yellow-300 text-sm">
                  No matching case record found.
                </div>
              )}

              <div className="space-y-6">
                {filteredCases.map((c: any, index: number) => (
                  <div
                    key={index}
                    className="bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-lg"
                  >
                    <div className="mb-4 text-lg font-semibold text-blue-300">
                      Case #{c.case_id}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                      <Info label="Evidence Hash" value={c.evidence_hash} />
                      <Info label="IPFS CID" value={c.ipfs_cid} />
                      <Info
                        label="Blockchain Tx Hash"
                        value={c.blockchain_tx_hash}
                      />
                      <Info label="File Name" value={c.file_name} />
                      <Info label="MIME Type" value={c.mime_type} />
                      <Info label="Registered By" value={c.registered_by} />
                      <Info
                        label="Anchored At"
                        value={new Date(c.created_at).toLocaleString()}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {ledgerRecord && ledgerRecord.status === "NOT_FOUND" && (
            <div className="text-yellow-300">
              No local evidence record found for this hash.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* UI HELPER */

const Info = ({ label, value }: { label: string; value: string }) => (
  <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
    <p className="text-xs text-slate-400 mb-1">{label}</p>
    <p className="break-all">{value}</p>
  </div>
);
