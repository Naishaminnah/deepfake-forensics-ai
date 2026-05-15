import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import api from "../services/api";

/* ====================================================== */
export type User = {
  username: string;
  role: string;
};

type AuthContextType = {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/* ====================================================== */
export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  /* ----------------------------------------------
     Verify token on app startup
  ---------------------------------------------- */
  useEffect(() => {
    const verifySession = async () => {
      const token = sessionStorage.getItem("token");

      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const res = await api.get("/auth/me");

        setUser({
          username: res.data.username,
          role: res.data.role,
        });
      } catch {
        sessionStorage.clear();
        setUser(null);
      }

      setLoading(false);
    };

    verifySession();
  }, []);

  useEffect(() => {
  const handleForbidden = () => {
    alert("You do not have permission to access this page");
    window.location.href = "/";
  };

  window.addEventListener("auth-forbidden", handleForbidden);

  return () =>
    window.removeEventListener("auth-forbidden", handleForbidden);
}, []);


  /* ----------------------------------------------
     Listen for global logout events (401 interceptor)
  ---------------------------------------------- */
  useEffect(() => {
    const handleLogout = () => logout();

    window.addEventListener("auth-logout", handleLogout);
    return () => window.removeEventListener("auth-logout", handleLogout);
  }, []);

  /* ---------------------------------------------- */
  const login = async (username: string, password: string) => {
    const params = new URLSearchParams();
    params.append("username", username);
    params.append("password", password);

    const res = await api.post("/auth/login", params, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    const { access_token, role } = res.data;

    sessionStorage.setItem("token", access_token);
    sessionStorage.setItem("username", username);
    sessionStorage.setItem("role", role);

    setUser({ username, role });
  };

  /* ---------------------------------------------- */
  const logout = () => {
    sessionStorage.clear();
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

/* ====================================================== */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};
