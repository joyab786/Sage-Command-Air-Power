"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Activity,
  Database,
  Lock,
  Layers,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Terminal,
  Cpu,
  Clock,
  Compass,
} from "lucide-react";

interface HealthData {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  database: {
    status: string;
    connected: boolean;
    driver?: string;
    wal_mode?: boolean;
  };
  timestamp: string;
}

export default function AeroFoundationDashboard() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastCheck, setLastCheck] = useState<string>("");
  const [activeTab, setActiveTab] = useState<string>("foundation");

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/health", { cache: "no-store" });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      const json = await res.json();
      if (json.success && json.data) {
        setHealth(json.data);
      } else {
        throw new Error(json.message || "Invalid health response");
      }
    } catch (err: any) {
      setError(err.message || "Backend server unreachable");
    } finally {
      setLoading(false);
      setLastCheck(new Date().toLocaleTimeString());
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-obsidian-900 bg-grid-pattern text-slate-100 flex flex-col font-sans">
      {/* --- TOP COMMAND HEADER --- */}
      <header className="border-b border-obsidian-600/80 bg-obsidian-800/90 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center space-x-4">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-lg shadow-cyan-500/10">
            <Compass className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold tracking-wider text-slate-100 font-mono">
                SAGECOMMAND // AERO
              </h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-mono">
                PHASE 1
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Air Power Autonomous Command & Decision Governance Platform
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-md bg-obsidian-700/60 border border-obsidian-600 text-xs font-mono">
            <div
              className={`w-2 h-2 rounded-full ${
                health?.status === "HEALTHY"
                  ? "bg-emerald-400 shadow-sm shadow-emerald-400 animate-pulse"
                  : error
                  ? "bg-rose-500"
                  : "bg-amber-400"
              }`}
            />
            <span className="text-slate-300">
              {health?.status === "HEALTHY"
                ? "API GATEWAY ONLINE"
                : error
                ? "GATEWAY OFFLINE"
                : "CONNECTING..."}
            </span>
          </div>

          <button
            onClick={fetchHealth}
            disabled={loading}
            className="p-2 rounded-md bg-obsidian-700 hover:bg-obsidian-600 text-slate-300 hover:text-white border border-obsidian-600 transition-colors"
            title="Refresh System Health"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-cyan-400" : ""}`} />
          </button>
        </div>
      </header>

      {/* --- NAVIGATION FOUNDATION TABS --- */}
      <nav className="border-b border-obsidian-700/60 bg-obsidian-850 px-6 flex space-x-1 text-sm font-medium">
        <button
          onClick={() => setActiveTab("foundation")}
          className={`py-3 px-4 border-b-2 transition-colors flex items-center space-x-2 font-mono text-xs tracking-wider ${
            activeTab === "foundation"
              ? "border-cyan-400 text-cyan-400 bg-cyan-500/5"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>SYSTEM FOUNDATION</span>
        </button>

        <button
          disabled
          className="py-3 px-4 border-b-2 border-transparent text-slate-600 cursor-not-allowed flex items-center space-x-2 font-mono text-xs tracking-wider"
          title="Deferred to Phase 2"
        >
          <span>FLEET OPERATIONS</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-obsidian-700 text-slate-500">
            PHASE 2
          </span>
        </button>

        <button
          disabled
          className="py-3 px-4 border-b-2 border-transparent text-slate-600 cursor-not-allowed flex items-center space-x-2 font-mono text-xs tracking-wider"
          title="Deferred to Phase 5"
        >
          <span>SUBSYSTEM DIAGNOSTICS</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-obsidian-700 text-slate-500">
            PHASE 5
          </span>
        </button>

        <button
          disabled
          className="py-3 px-4 border-b-2 border-transparent text-slate-600 cursor-not-allowed flex items-center space-x-2 font-mono text-xs tracking-wider"
          title="Deferred to Phase 7"
        >
          <span>MISSION MANAGER</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-obsidian-700 text-slate-500">
            PHASE 7
          </span>
        </button>

        <button
          disabled
          className="py-3 px-4 border-b-2 border-transparent text-slate-600 cursor-not-allowed flex items-center space-x-2 font-mono text-xs tracking-wider"
          title="Deferred to Phase 10"
        >
          <span>GOVERNANCE GATES</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-obsidian-700 text-slate-500">
            PHASE 10
          </span>
        </button>
      </nav>

      {/* --- MAIN WORKSPACE VIEW --- */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        {/* Banner Alert if Offline */}
        {error && (
          <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start space-x-3 text-rose-300">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-400" />
            <div>
              <h3 className="text-sm font-semibold">Backend Gateway Connection Notice</h3>
              <p className="text-xs text-rose-300/80 mt-0.5">
                {error}. Ensure the Aero FastAPI backend service is running on port 8000.
              </p>
            </div>
          </div>
        )}

        {/* --- FOUNDATION STATUS MATRIX --- */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-100 flex items-center space-x-2">
                <span>Core Technical Foundation Matrix</span>
              </h2>
              <p className="text-xs text-slate-400">
                Phase 1 architectural components verified and operational
              </p>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Last probe: {lastCheck || "Never"}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Card 1: FastAPI Gateway */}
            <div className="p-5 rounded-lg bg-obsidian-800/60 border border-obsidian-600 hover:border-cyan-500/40 transition-all space-y-3">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                  <Activity className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  ACTIVE
                </span>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-100">API Gateway & Runtime</h3>
                <p className="text-xs text-slate-400 mt-1">
                  FastAPI application with structured logging, CORS, and request correlation.
                </p>
              </div>
              <div className="pt-2 border-t border-obsidian-700/60 text-xs font-mono space-y-1 text-slate-400">
                <div className="flex justify-between">
                  <span>Version:</span>
                  <span className="text-slate-200">{health?.version || "0.1.0"}</span>
                </div>
                <div className="flex justify-between">
                  <span>Environment:</span>
                  <span className="text-slate-200">{health?.environment || "development"}</span>
                </div>
              </div>
            </div>

            {/* Card 2: Database Foundation */}
            <div className="p-5 rounded-lg bg-obsidian-800/60 border border-obsidian-600 hover:border-cyan-500/40 transition-all space-y-3">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                  <Database className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  WAL READY
                </span>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-100">Database Foundation</h3>
                <p className="text-xs text-slate-400 mt-1">
                  SQLite engine with Write-Ahead Logging (WAL) and atomic session management.
                </p>
              </div>
              <div className="pt-2 border-t border-obsidian-700/60 text-xs font-mono space-y-1 text-slate-400">
                <div className="flex justify-between">
                  <span>Status:</span>
                  <span className="text-emerald-400">{health?.database.status || "HEALTHY"}</span>
                </div>
                <div className="flex justify-between">
                  <span>WAL Concurrency:</span>
                  <span className="text-slate-200">
                    {health?.database.wal_mode ? "ENABLED" : "CONFIGURED"}
                  </span>
                </div>
              </div>
            </div>

            {/* Card 3: Deterministic Policy Engine */}
            <div className="p-5 rounded-lg bg-obsidian-800/60 border border-obsidian-600 hover:border-cyan-500/40 transition-all space-y-3">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  STANDALONE
                </span>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-100">Deterministic Policy Engine</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Enforces strict precedence: DENY &gt; REQUIRE_APPROVAL &gt; HOLD &gt; ALLOW.
                </p>
              </div>
              <div className="pt-2 border-t border-obsidian-700/60 text-xs font-mono space-y-1 text-slate-400">
                <div className="flex justify-between">
                  <span>Default Policy:</span>
                  <span className="text-slate-200">FAIL-CLOSED (HOLD)</span>
                </div>
                <div className="flex justify-between">
                  <span>Domain Coupling:</span>
                  <span className="text-emerald-400">NEUTRAL (0 MFG ENTITIES)</span>
                </div>
              </div>
            </div>

            {/* Card 4: Cryptographic Audit Ledger */}
            <div className="p-5 rounded-lg bg-obsidian-800/60 border border-obsidian-600 hover:border-cyan-500/40 transition-all space-y-3">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded bg-purple-500/10 border border-purple-500/20 text-purple-400">
                  <Lock className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  TAMPER-EVIDENT
                </span>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-100">Cryptographic Audit Ledger</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Append-only immutable record store with unbroken SHA-256 hash chaining.
                </p>
              </div>
              <div className="pt-2 border-t border-obsidian-700/60 text-xs font-mono space-y-1 text-slate-400">
                <div className="flex justify-between">
                  <span>Chaining Hash:</span>
                  <span className="text-slate-200">SHA-256</span>
                </div>
                <div className="flex justify-between">
                  <span>Verification:</span>
                  <span className="text-emerald-400">MATHEMATICALLY DEFUSED</span>
                </div>
              </div>
            </div>

            {/* Card 5: Deterministic Execution Gateway */}
            <div className="p-5 rounded-lg bg-obsidian-800/60 border border-obsidian-600 hover:border-cyan-500/40 transition-all space-y-3">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400">
                  <Cpu className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  10-GATE BOUNDARY
                </span>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-100">Execution Gateway Boundary</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Transactional write boundary with Two-Person Rule and atomic rollback.
                </p>
              </div>
              <div className="pt-2 border-t border-obsidian-700/60 text-xs font-mono space-y-1 text-slate-400">
                <div className="flex justify-between">
                  <span>Two-Person Rule:</span>
                  <span className="text-slate-200">ENFORCED</span>
                </div>
                <div className="flex justify-between">
                  <span>Idempotency:</span>
                  <span className="text-emerald-400">DEDUPLICATION CACHED</span>
                </div>
              </div>
            </div>

            {/* Card 6: Base Contracts & Schemas */}
            <div className="p-5 rounded-lg bg-obsidian-800/60 border border-obsidian-600 hover:border-cyan-500/40 transition-all space-y-3">
              <div className="flex items-center justify-between">
                <div className="p-2 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  PYDANTIC V2
                </span>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-100">Base Contracts & Envelopes</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Standardized ApiResponse, ApiErrorResponse, and pagination envelopes.
                </p>
              </div>
              <div className="pt-2 border-t border-obsidian-700/60 text-xs font-mono space-y-1 text-slate-400">
                <div className="flex justify-between">
                  <span>Deprecations:</span>
                  <span className="text-emerald-400">ZERO (CLEAN V2)</span>
                </div>
                <div className="flex justify-between">
                  <span>Aerospace Domain:</span>
                  <span className="text-cyan-400">PREPARED FOR PHASE 2</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* --- ARCHITECTURAL ROADMAP & DEFERRED CAPABILITIES --- */}
        <section className="p-6 rounded-lg bg-obsidian-800/40 border border-obsidian-600 space-y-4">
          <div className="flex items-center space-x-2 text-cyan-400">
            <Clock className="w-5 h-5" />
            <h3 className="text-sm font-semibold tracking-wide uppercase font-mono">
              System Evolution Roadmap (Deferred by Architecture Design)
            </h3>
          </div>
          <p className="text-xs text-slate-300">
            Per architectural guidelines, the following specialized aerospace capabilities are
            deliberately deferred to ensure clean technical domain boundaries:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div className="p-3 rounded bg-obsidian-700/40 border border-obsidian-600/60 text-xs space-y-1">
              <div className="font-semibold text-slate-200 font-mono">PHASE 2: AERO DOMAIN</div>
              <div className="text-slate-400">
                Airframes, Squadrons, Wings, Sorties, Avionics, Turbofan Propulsion, Munitions.
              </div>
            </div>
            <div className="p-3 rounded bg-obsidian-700/40 border border-obsidian-600/60 text-xs space-y-1">
              <div className="font-semibold text-slate-200 font-mono">PHASE 3: TELEMETRY FABRIC</div>
              <div className="text-slate-400">
                High-rate flight telemetry ingestion, ARINC 429 / MIL-STD-1553 parser bus.
              </div>
            </div>
            <div className="p-3 rounded bg-obsidian-700/40 border border-obsidian-600/60 text-xs space-y-1">
              <div className="font-semibold text-slate-200 font-mono">PHASE 4: AIRCRAFT DIGITAL TWIN</div>
              <div className="text-slate-400">
                Bitemporal aircraft twin state, flight hours, landing cycles, structural life.
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* --- FOOTER --- */}
      <footer className="border-t border-obsidian-700/60 bg-obsidian-850 px-6 py-3 text-xs text-slate-500 flex justify-between items-center font-mono">
        <div>SageCommand Air Power System — Aero // Phase 1 Baseline</div>
        <div>FastAPI 0.115+ // Python 3.12 // Next.js 16</div>
      </footer>
    </div>
  );
}
