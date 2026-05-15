import { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { useNavigate } from "react-router-dom";
import { Shield, Lock, User, AlertCircle } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError("");

    if (!username.trim()) {
      setError("Username is required");
      return;
    }

    if (!password) {
      setError("Password is required");
      return;
    }

    try {
      setLoading(true);

      await login(username.trim(), password);

      // ✅ ROLE-BASED REDIRECT (CRITICAL FIX)
      const role = localStorage.getItem("role");

      if (role === "ADMIN") {
        navigate("/admin", { replace: true });
      } else {
        navigate("/dashboard", { replace: true });
      }

    } catch (err: any) {
      const msg = err?.response?.data?.detail;

      if (msg?.includes("disabled")) {
  setError("Your account has been disabled. Contact administrator.");
} else {
  setError("Invalid username or password");
}

    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 text-white">
      <div className="w-full max-w-md bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl p-8">

        {/* Header */}
        <div className="flex items-center gap-3 mb-6 justify-center">
          <Shield className="w-10 h-10 text-blue-400" />
          <div>
            <h1 className="text-2xl font-bold">AI Digital Forensics</h1>
            <p className="text-sm text-blue-300">
              Secure Evidence Analysis Portal
            </p>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 flex items-center gap-2 bg-red-900/40 border border-red-700 text-red-300 p-3 rounded-lg text-sm">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {/* Username */}
        <div className="mb-4">
          <label className="text-sm text-slate-300 mb-1 block">
            Investigator ID
          </label>
          <div className="flex items-center bg-slate-700 rounded-lg px-3">
            <User className="w-4 h-4 text-slate-400 mr-2" />
            <input
              className="w-full bg-transparent p-2 outline-none text-white"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
            />
          </div>
        </div>

        {/* Password */}
        <div className="mb-6">
          <label className="text-sm text-slate-300 mb-1 block">
            Access Key
          </label>
          <div className="flex items-center bg-slate-700 rounded-lg px-3">
            <Lock className="w-4 h-4 text-slate-400 mr-2" />
            <input
              type="password"
              className="w-full bg-transparent p-2 outline-none text-white"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
            />
          </div>
        </div>

        <button
          onClick={submit}
          disabled={loading}
          className={`w-full py-3 rounded-lg font-semibold ${
            loading
              ? "bg-slate-600"
              : "bg-blue-600 hover:bg-blue-700"
          }`}
        >
          {loading ? "Authenticating..." : "Login"}
        </button>

        <p className="mt-6 text-sm text-center text-slate-400">
          Don’t have an account?{" "}
          <span
            className="text-blue-400 cursor-pointer hover:underline"
            onClick={() => navigate("/signup")}
          >
            Sign up
          </span>
        </p>
      </div>
    </div>
  );
}
