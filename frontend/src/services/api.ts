// frontend/src/services/api.ts

import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000";

/* =========================================================
   AXIOS INSTANCE (JWT ENABLED)
========================================================= */
const api = axios.create({
  baseURL: BASE_URL,
});

/* =========================================================
   REQUEST INTERCEPTOR → Attach JWT
========================================================= */
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("token");
  

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

/* =========================================================
   RESPONSE INTERCEPTOR → GLOBAL AUTH HANDLING
========================================================= */
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;

    if (status === 401) {
      sessionStorage.clear();

      // 🔥 Tell React Router to redirect (NO reload)
      window.dispatchEvent(new CustomEvent("auth-logout"));
    }

    if (status === 403) {
      window.dispatchEvent(new CustomEvent("auth-forbidden"));
    }

    return Promise.reject(error);
  }
);

export default api;

/* =========================================================
   🔍 EXISTING FORENSIC MODULE APIs (UNCHANGED)
========================================================= */

// Image Deepfake Detection
export const uploadImage = (file: File, caseId: number) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("case_id", String(caseId));
  return api.post("/detect/image", formData).then((res) => res.data);
};

// Video Deepfake Detection
export const uploadVideo = (file: File, caseId: number) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("case_id", String(caseId));
  return api.post("/detect/video", formData).then((res) => res.data);
};

// Audio Deepfake Detection
export const uploadAudio = (file: File, caseId: number) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("case_id", String(caseId));
  return api.post("/detect/audio", formData).then((res) => res.data);
};

// GAN Fingerprinting
export const uploadGANFingerprint = (file: File, caseId: number) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("case_id", String(caseId));
  return api.post("/detect/gan", formData).then((res) => res.data);
};

// BigGAN Reconstruction
export const uploadBigGANReconstruct = async (file: File, caseId: number) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("case_id", String(caseId));

  const res = await api.post("/gan/reconstruct", formData, {
    responseType: "blob",
  });

  return URL.createObjectURL(res.data);
};

// StyleGAN Reconstruction
export const uploadStyleGANReconstruct = (file: File, caseId: number) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("case_id", String(caseId));

  return api.post("/gan/stylegan/reconstruct", formData).then((res) => res.data);
};

/* =========================================================
   🛡️ ADMIN DASHBOARD APIs
========================================================= */

export const getAdminSummary = () => {
  return api.get("/admin/summary").then((res) => res.data);
};

export const getAuditLogs = () => {
  return api.get("/audit").then((res) => res.data);
};

/* =========================================================
   📜 ADMIN EVIDENCE LEDGER APIs
========================================================= */

// Local detection ledger (DB)
export const getEvidenceLedger = () => {
  return api.get("/admin/evidence-ledger").then((res) => res.data);
};

// Blockchain anchored evidence ledger
export const getEvidenceAnchorLedger = () => {
  return api.get("/admin/evidence-anchor-ledger").then((res) => res.data);
};


/* =========================================================
   👥 ADMIN USER MANAGEMENT APIs
========================================================= */

export const getAdminUsers = () => {
  return api.get("/admin/users").then((res) => res.data);
};

export const updateUserRole = (id: number, role: string) => {
  return api.put(`/admin/users/${id}/role`, { role });
};

export const toggleUserStatus = (id: number) => {
  return api.put(`/admin/users/${id}/status`);
};

export const createUser = (data: {
  username: string;
  password: string;
  role: "FORENSIC_ANALYST" | "LEGAL_AUTHORITY";
}) => {
  const formData = new FormData();
  formData.append("username", data.username);
  formData.append("password", data.password);
  formData.append("role", data.role);

  return api.post("/auth/create-user", formData);
};

export const getCurrentUsername = () => {
  const token = sessionStorage.getItem("token");
  if (!token) return null;

  const payload = JSON.parse(atob(token.split(".")[1]));
  return payload.sub;
};

export const uploadAndRegisterEvidence = (
  file: File,
  caseId: number
) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("case_id", String(caseId)); // ✅ REQUIRED

  return api
    .post("/forensics/upload-and-register", formData)
    .then((res) => res.data);
};


/* =========================================================
   📁 CASE MANAGEMENT APIs
========================================================= */

// Create new case
export const createCase = (data: {
  title: string;
  description?: string;
}) => {
  const formData = new FormData();
  formData.append("title", data.title);
  formData.append("description", data.description || "");

  return api.post("/cases/create", formData).then(res => res.data);
};

// List cases for analyst / legal authority
export const getCases = () => {
  return api.get("/cases").then(res => res.data);
};
/* =========================================================
   👤 USER DEEPFAKE DETECTION APIs (NO CASE)
========================================================= */

export const uploadUserImage = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  return api.post("/detect/image", formData).then(res => res.data);
};

export const uploadUserAudio = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  return api.post("/detect/audio", formData).then(res => res.data);
};

export const uploadUserVideo = (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  return api.post("/detect/video", formData).then(res => res.data);
};
