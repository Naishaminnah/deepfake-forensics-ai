import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { Shield, User, Lock, AlertCircle } from "lucide-react";

export default function Signup() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  

 const submit = async () => {
  setError("");

  if (username.trim().length==0) {
    setError("Username cannot be empty");
    return;
  }

  if (username.trim().length < 3) {
    setError("Username must be at least 3 characters");
    return;
  }

  if (password.length==0) {
    setError("Password cannot be empty");
    return;
  }
  if (password.length < 8) {
    setError("Password must be at least 8 characters");
    return;
  }

  const usernameRegex = /^[A-Za-z0-9_]+$/;

  if (!usernameRegex.test(username.trim())) {
  setError("Username may contain only letters, numbers, and underscores");
  return;
}
  

  try {
    setLoading(true);

    // ✅ FIX: send form data, NOT JSON
    const params = new URLSearchParams();
    params.append("username", username.trim());
    params.append("password", password);
    
    await api.post("/auth/signup", params, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    setSuccess("Account created successfully. Redirecting to login…");

setTimeout(() => {
  navigate("/login");
}, 1500);


  } catch (err: any) {
    const msg = err?.response?.data?.detail;

    if (msg?.includes("exists")) {
      setError("Username already exists. Try logging in");
    } else {
      setError("Signup failed. Please try again");
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
            <h1 className="text-2xl font-bold">User Registration</h1>
            <p className="text-sm text-blue-300">
              Public Evidence Submission
            </p>
          </div>
        </div>
        {success && (
          <div className="mb-4 bg-green-900/40 border border-green-700 text-green-300 p-3 rounded-lg text-sm">
            {success}
          </div>
        )}

        {error && (
          <div className="mb-4 flex items-center gap-2 bg-red-900/40 border border-red-700 text-red-300 p-3 rounded-lg text-sm">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {/* Username */}
        <div className="mb-4">
          <label className="text-sm text-slate-300 mb-1 block">Username</label>
          <div className="flex items-center bg-slate-700 rounded-lg px-3">
            <User className="w-4 h-4 text-slate-400 mr-2" />
            <input
              disabled={loading}
              className="w-full bg-transparent p-2 outline-none text-white"
              value={username}
              onChange={(e) => {
    const value = e.target.value;
    if (/^[A-Za-z0-9_]*$/.test(value)) {
      setUsername(value);
    }
  }}
            />
          </div>
        </div>

        {/* Password */}
        <div className="mb-6">
          <label className="text-sm text-slate-300 mb-1 block">Password</label>
          <div className="flex items-center bg-slate-700 rounded-lg px-3">
            <Lock className="w-4 h-4 text-slate-400 mr-2" />
            <input
              disabled={loading}
              type="password"
              className="w-full bg-transparent p-2 outline-none text-white"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
        </div>

        <button
          onClick={submit}
          disabled={loading}
          className="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-700 font-semibold"
        >
          {loading ? "Creating Account..." : "Sign Up"}
        </button>

        <p className="mt-6 text-sm text-center text-slate-400">
          Already have an account?{" "}
          <span
            className="text-blue-400 cursor-pointer hover:underline"
            onClick={() => navigate("/login")}
          >
            Login
          </span>
        </p>
      </div>
    </div>
  );
}
