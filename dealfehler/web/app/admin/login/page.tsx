"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, setToken } from "@/lib/api";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const r = await api<{ access_token: string }>("/api/auth/login", { method: "POST", json: { email, password } });
      setToken(r.access_token);
      router.replace("/admin");
    } catch (err: any) {
      setError(err.message);
    }
  };
  return (
    <div style={{ display: "grid", placeItems: "center", minHeight: "100vh", padding: 16 }}>
      <form onSubmit={submit} className="card grid" style={{ width: "100%", maxWidth: 360 }}>
        <div className="logo" style={{ color: "var(--text)" }}>DEAL<span style={{ color: "var(--accent)" }}>FEHLER</span></div>
        <label>E-Mail<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="username" /></label>
        <label>Passwort<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" /></label>
        {error && <p className="error">{error}</p>}
        <button className="btn primary">Anmelden</button>
      </form>
    </div>
  );
}
