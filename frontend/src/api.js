import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api",
  timeout: 10000,
  withCredentials: true,
});

let csrfToken = "";

api.interceptors.request.use((config) => {
  if (csrfToken && !["get", "head", "options"].includes(config.method?.toLowerCase())) {
    config.headers["X-CSRF-Token"] = csrfToken;
  }
  return config;
});

export function setCsrfToken(value) {
  csrfToken = value || "";
}

export default api;
