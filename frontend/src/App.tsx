import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api";
import { Dashboard } from "./pages/Dashboard";
import { RecordDetail } from "./pages/RecordDetail";
import { Records } from "./pages/Records";
import { Register } from "./pages/Register";
import { Verify } from "./pages/Verify";

function ApiStatus() {
  const [state, setState] = useState<"checking" | "up" | "down">("checking");
  useEffect(() => {
    const check = () =>
      api
        .health()
        .then(() => setState("up"))
        .catch(() => setState("down"));
    check();
    const t = setInterval(check, 15000);
    return () => clearInterval(t);
  }, []);
  const label = { checking: "Checking API…", up: "API online", down: "API offline" }[state];
  return (
    <span className={`status status--${state}`} title={label}>
      <i /> {label}
    </span>
  );
}

export function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <span>
            Dashcam<strong>Fingerprint</strong>
          </span>
        </NavLink>
        <nav className="nav">
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/register">Register</NavLink>
          <NavLink to="/verify">Verify</NavLink>
          <NavLink to="/records">Records</NavLink>
        </nav>
        <ApiStatus />
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/register" element={<Register />} />
          <Route path="/verify" element={<Verify />} />
          <Route path="/records" element={<Records />} />
          <Route path="/records/:id" element={<RecordDetail />} />
          <Route path="*" element={<p className="muted">Page not found.</p>} />
        </Routes>
      </main>
      <footer className="footer muted small">
        FastAPI · React + Vite + TypeScript · Supabase (PostgreSQL) — videos are fingerprinted, never
        stored.
      </footer>
    </div>
  );
}
