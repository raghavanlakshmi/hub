# Hub
## Post-Hospital Recovery Co-Pilot — 2-Agent Architecture | Companion project to Nexus

Hub is a deliberately minimal redesign of [Nexus](../nexus), built to answer one question with running code instead of theory:

> If you collapse Nexus's five agents into a single agent and keep **only** the one load-bearing boundary — the gate in front of Escalation — what actually changes in tokens, cost, latency, and orchestration complexity?

Same tools, same prompts, same model, same Streamlit UI. The **only** thing that differs is how the work is orchestrated.

---

### The hypothesis

Nexus's five agents (Intake → Care Plan → Monitoring → Escalation → Admin) are mostly a **sequential, dependent pipeline** reasoning about one patient — not independent specialists. Only one hand-off is genuinely a judgment call that can trigger a real-world action (an SMS, a 911 screen): the gate into **Escalation**.

Hub keeps that one boundary as a real graph edge and collapses everything else into a single **Recovery Agent** that branches internally on `state["phase"]`.

---

### Architecture

| | Nexus | Hub |
|---|---|---|
| Agents / nodes | 5 nodes across **2** compiled graphs | **3** nodes in **1** compiled graph |
| Intake → Care Plan | graph edge | plain Python call (internal phase-chain) |
| Monitoring → Admin | graph edge | plain Python call (internal phase-chain) |
| Monitoring → Escalation | graph edge | **still a graph edge** (the one preserved boundary) |
| Escalation → Admin follow-up | graph edge | graph edge (`recovery_agent_admin` wrapper) |

```
                ┌──────────────────────────────────────┐
   run_intake → │            recovery_agent             │
run_daily_checkin             (intake│careplan│monitoring│admin)
                └──────────────────────────────────────┘
                             │ RED only
                             ▼
                      escalation_agent      ← the one load-bearing boundary
                             │ TIER_1/TIER_2
                             ▼
                    recovery_agent_admin (admin follow-up)
```

- **`agents/recovery_agent.py`** — one file, one public function `run_recovery_agent()`, consolidating four of Nexus's five agents with internal phase-chaining.
- **`agents/escalation_agent.py`** — copied verbatim from Nexus, unchanged (including the known keyword-matching limitation in `determine_escalation_tier()`).
- **`agents/orchestrator.py`** — one compiled LangGraph graph, three nodes, two conditional edges.
- **`instrumentation/usage_tracker.py`** — *new in Hub.* `tracked_claude_call()` wraps every Claude call and logs tokens/cost/latency into `state["token_log"]`, so the comparison uses real measured numbers, not estimates.

What is copied **verbatim** from Nexus: all four tools (`pdf_parser`, `pinecone_store`, `openfda`, `notification_tool`), `elevenlabs_stt`, the `RecoveryState` schema (plus two fields: `phase`, `token_log`), and all three system prompts (`INTAKE`, `CARE_PLAN`, `MONITORING`). This is intentional — keeping them identical means any measured difference is attributable to orchestration alone.

---

### Tech stack

LangGraph · Python · Claude `claude-sonnet-4-6` (Anthropic API) · Pinecone · Streamlit · PyMuPDF · OpenFDA API · Twilio · Gmail SMTP · ElevenLabs (STT) · Nebius Token Factory (`meta-llama/Llama-3.3-70B-Instruct`).

---

### Setup

1. **Create the virtual environment and install dependencies**

   ```bash
   cd week3/hub
   python -m venv venv
   venv\Scripts\activate            # Windows PowerShell
   # source venv/Scripts/activate   # Git Bash
   pip install -r requirements.txt
   ```

   > Uses the `pinecone` package (v9.x), **not** the deprecated `pinecone-client`.

2. **Configure secrets** — copy `.env.example` to `.env` and fill in your keys:

   ```bash
   cp .env.example .env
   ```

   `.env` is gitignored and never committed. Reusing Nexus's API keys is fine (accounts, not code).

3. **Create a fresh Pinecone index**
   - Name: `hub` (a **different** index from Nexus's, so stored data never mixes)
   - Dimensions: `1024`
   - Metric: `cosine`

4. **Run the app**

   ```bash
   streamlit run ui/streamlit_app.py
   ```

---

### UI

Seven Streamlit screens (soft theme via `.streamlit/config.toml`), copied from Nexus with only the orchestrator call sites swapped:
Onboarding · Care plan · Daily check-in (ElevenLabs voice + typed fallback) · Approval queue · Recovery dashboard · Provider summary · Hospital history — **plus** a Hub-only **System Usage (Debug)** page that surfaces live token/cost/latency from `summarize_usage()`.

---

### The comparison (Phase 10)

Run the **same** discharge PDF (`data/01_chf_john_demo.pdf`) and the **same** check-in through both Nexus and Hub. Results below are from one run each: `01_chf_john_demo.pdf` intake + care plan + one GREEN daily check-in (2026-06-23).

| Metric | Nexus (5 agents) | Hub (1 agent) |
|---|---|---|
| Total Claude calls | 3 | 3 |
| Total input tokens | 2456 | 2454 |
| Total output tokens | 3078 | 2761 |
| Total cost (USD) | $0.0535 | $0.0488 |
| Total latency | 45.8 s | 42.4 s |
| Graph nodes | 5 (across 2 graphs) | 3 (in 1 graph) |
| `add_node` / `add_edge` / conditional edges | 5 / 3 / 2 | 3 / 2 / 1 |
| `.compile()` calls | 2 | 1 |
| Orchestration code (non-blank, non-comment lines) | 56 | 41 |

**Reading the results:**

- **Input tokens are identical to within 2 tokens** (2456 vs 2454; careplan input is *exactly* 1005 in both). Input is the part orchestration controls — so this is the empirical proof of the hypothesis: **collapsing 5 agents into 1 changed the wiring, not the model workload.**
- **The cost / latency / output-token differences are LLM nondeterminism, not architecture.** Almost the entire gap is one cell — careplan output (Nexus 2188 vs Hub 1860 tokens): same prompt, same call, Claude just wrote a longer plan in the Nexus run. Re-run and the two could swap. The ~$0.005 difference is noise, not a structural saving.
- **Where Hub genuinely wins is structural** — 3 nodes vs 5, 1 compiled graph vs 2, 1 conditional edge vs 2, ~15 fewer lines of orchestration code (41 vs 56) — exactly the prediction. (Hub's `orchestrator.py` is actually *longer* in raw lines because it carries heavy explanatory comments; the code itself is leaner.)

> Bottom line: for this pipeline, the five-agent split bought **no measurable token/cost benefit** — the agents were a sequential pipeline over one patient, not independent specialists. The single load-bearing boundary (escalation) is preserved in both. The trade Hub makes is *less orchestration code* for *less per-node observability* — Nexus's separate nodes make it marginally easier to see which stage a bug lives in.

#### RED-path run — the preserved boundary firing (2026-06-23)

Both projects were run with a **RED** check-in ("Chest pain or pressure") to exercise the one hand-off that still goes through the graph. The two are nearly indistinguishable:

| RED-run total | Nexus (5 agents) | Hub (1 agent) |
|---|---|---|
| Claude calls | 3 | 3 |
| Input tokens | 2473 | 2470 |
| Output tokens | 3004 | 2986 |
| Total cost | $0.0525 | $0.0522 |
| Total latency | 48.5 s | 48.5 s |

Per-phase (Hub run shown; Nexus within a few tokens at each phase):

| Phase | Calls | In / Out tokens | Cost | Latency |
|---|---|---|---|---|
| intake | 1 | 798 / 785 | $0.0142 | 8.6 s |
| careplan | 1 | 1005 / 1888 | $0.0313 | 32.6 s |
| monitoring (RED) | 1 | 667 / 313 | $0.0067 | 7.3 s |

The **monitoring** call's `monitoring (RED)` row is the tell: Nexus 669/297, Hub 667/313 — near-identical input (the same RED check-in), output within LLM variance. Compared to the GREEN run (107 output tokens), the RED call emits ~300 output tokens — the fuller RED JSON (flags + `escalation_reason`). Cost within **$0.0003** and latency identical to the tenth of a second. Crucially, a RED check-in is **still just 1 Claude call** in both — `escalation_agent` and `admin` make no model calls, so the escalation boundary adds **zero** token cost; it is pure routing.

Terminal log of the run (the architectural payoff — watch the log prefix change from `[Recovery Agent: …]` to `[Escalation Agent]`, which marks crossing from the consolidated node into the separate escalation node):

```
[Recovery Agent: intake] Starting...
[Recovery Agent: intake] PDF parsed. 2 pages, 1541 chars.
[usage] intake: 798 in / 785 out | $0.0142 | 8595ms
[Recovery Agent: intake] Complete. Diagnosis: Congestive Heart Failure (CHF) Exacerbation
[Recovery Agent: careplan] Starting...
[Recovery Agent: careplan] Checking 4 medications via OpenFDA...
[Recovery Agent: careplan] 1 medications flagged.
[usage] careplan: 1005 in / 1888 out | $0.0313 | 32605ms
[Nebius] Skipped — NEBIUS_API_KEY not set (optional integration).
[Recovery Agent: careplan] Complete.
[Recovery Agent: monitoring] Processing Day 2 check-in...
[usage] monitoring: 667 in / 313 out | $0.0067 | 7264ms
[Recovery Agent: monitoring] Classification: RED      ← consolidated node, monitoring phase
[Escalation Agent] RED flag detected. Determining tier...   ← graph edge fired into the SEPARATE escalation node
[Escalation Agent] Tier: TIER_3
[Notification] SMS skipped — Twilio credentials not configured.
```

> **Note:** this Hub log was captured *before* the escalation→admin parity fix (2026-06-24). At capture time Hub sent TIER_3 straight to `END` and skipped the admin follow-up. After the fix, Hub's `escalation_agent → recovery_agent_admin` edge is unconditional (mirroring Nexus), so a re-run now also prints the admin step (`[Recovery Agent: admin] Running daily task check...` / `Done. Actions: []`). Behavior is now identical to Nexus; only the node *structure* differs.

For contrast, here is **Nexus's** terminal for the same RED check-in. Note that *every* stage prints its own agent prefix — there is a node boundary at each hand-off, not just at escalation:

```
[Intake Agent] Starting...
[Intake Agent] PDF parsed. 2 pages, 1541 chars.
[usage] intake: 799 in / 773 out | $0.0140 | 11473ms
[Intake Agent] Complete. Diagnosis: Congestive Heart Failure (CHF) Exacerbation
[Care Plan Agent] Starting...
[Care Plan Agent] Checking 4 medications via OpenFDA...
[Care Plan Agent] 1 medications flagged.
[usage] careplan: 1005 in / 1934 out | $0.0320 | 30309ms
[Care Plan Agent] Complete.
[Nebius] Care plan generation complete.          ← Nebius ran here (Nexus has NEBIUS_API_KEY set)
[Monitoring Agent] Processing Day 2 check-in...
[usage] monitoring: 669 in / 297 out | $0.0065 | 6716ms
[Monitoring Agent] Classification: RED
[Escalation Agent] RED flag detected. Determining tier...
[Escalation Agent] Tier: TIER_3
[Notification] SMS not sent (Twilio error 21659 — country mismatch).
[Admin Agent] Running daily task check...         ← admin runs after escalation (unconditional edge)
[Admin Agent] Done. Actions: []
```

The difference is purely structural: Hub logs one `[Recovery Agent: …]` block (intake/careplan/monitoring/admin all in one node) with a single crossing into `[Escalation Agent]`; Nexus logs five separate agent prefixes because each stage is its own graph node. Same tools, same prompts, same model calls, same outcome (TIER_3 → **🚨 CALL 911 NOW**) — `escalation_agent.py` is a byte-for-byte copy, including `determine_escalation_tier()` and its known keyword-matching limitation.

---

### Safety & data

- Uses **synthetic** discharge data only (`data/`). No real patient data.
- Not medical advice. In an emergency, call 911.
- All outbound messages (provider drafts, escalations) require human approval before sending.
