"""
Generates 'Nexus_vs_Hub_Comparison.docx' — a plain-English, presentation-ready
comparison of the Nexus (5-agent) and Hub (1-agent) recovery co-pilots,
including workflow diagrams drawn with matplotlib and the measured numbers.

Run:  venv\\Scripts\\python.exe generate_comparison_doc.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# ── palette ───────────────────────────────────────────────────────────────────
SAGE   = "#8A9A6B"
SAGE_D = "#5F6B47"
CLAY   = "#B07D62"
INK    = "#2E2E2E"
CREAM  = "#F4F1E8"
BLUEG  = "#6E8398"
RED    = "#C0504D"

# ════════════════════════════════════════════════════════════════════════════
# 1. DIAGRAMS
# ════════════════════════════════════════════════════════════════════════════

def _box(ax, cx, cy, w, h, text, fc, ec, tc="white", fs=11, bold=True):
    box = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                         boxstyle="round,pad=0.02,rounding_size=0.08",
                         linewidth=1.6, edgecolor=ec, facecolor=fc, zorder=2)
    ax.add_patch(box)
    ax.text(cx, cy, text, ha="center", va="center", color=tc,
            fontsize=fs, fontweight="bold" if bold else "normal", zorder=3)


def _arrow(ax, p1, p2, color=INK, style="-|>", lw=2.0, ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=18,
                                 lw=lw, color=color, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}", zorder=1))


def _label(ax, x, y, text, color=INK, fs=9, style="italic", ha="center"):
    ax.text(x, y, text, ha=ha, va="center", color=color, fontsize=fs,
            fontstyle=style)


def draw_nexus(path):
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 8); ax.axis("off")
    ax.text(5, 7.6, "NEXUS — 5 agents across 2 separate graphs",
            ha="center", fontsize=14, fontweight="bold", color=SAGE_D)

    # Graph 1 — onboarding
    ax.text(0.2, 6.55, "GRAPH 1  ·  Onboarding (Day 0)", fontsize=10,
            fontweight="bold", color=INK, ha="left")
    _box(ax, 2.0, 5.6, 2.4, 0.9, "Intake\nAgent", SAGE, SAGE_D, fs=10)
    _box(ax, 5.5, 5.6, 2.4, 0.9, "Care Plan\nAgent", SAGE, SAGE_D, fs=10)
    _box(ax, 8.6, 5.6, 1.3, 0.9, "END", "#9AA0A6", "#5F6368", fs=10)
    _arrow(ax, (3.2, 5.6), (4.3, 5.6))
    _arrow(ax, (6.7, 5.6), (7.95, 5.6))

    # divider
    ax.plot([0.2, 9.8], [4.4, 4.4], color="#CFC9BA", lw=1, ls="--", zorder=0)

    # Graph 2 — daily check-in
    ax.text(0.2, 4.0, "GRAPH 2  ·  Daily Check-in (Day N)", fontsize=10,
            fontweight="bold", color=INK, ha="left")
    yb = 3.1
    _box(ax, 1.7, yb, 2.2, 0.9, "Monitoring\nAgent", SAGE, SAGE_D, fs=10)
    _box(ax, 4.6, yb, 2.2, 0.9, "Escalation\nAgent", CLAY, "#7E5642", fs=10)
    _box(ax, 7.2, yb, 2.0, 0.9, "Admin\nAgent", SAGE, SAGE_D, fs=10)
    _box(ax, 9.4, yb, 1.0, 0.7, "END", "#9AA0A6", "#5F6368", fs=9)

    # RED path: monitoring -> escalation -> admin -> END, clean straight row
    _arrow(ax, (2.8, yb), (3.45, yb), color=RED, lw=2.4)
    _label(ax, 3.13, yb + 0.45, "RED", color=RED, fs=8.5)
    _arrow(ax, (5.7, yb), (6.15, yb))
    _arrow(ax, (8.2, yb), (8.85, yb))

    # GREEN/YELLOW: monitoring -> admin, routed clearly BELOW the row (no overlaps)
    _arrow(ax, (1.9, yb - 0.5), (7.0, yb - 0.5), color=BLUEG, rad=0.30)
    _label(ax, 4.45, 0.85, "GREEN / YELLOW  —  skips escalation, straight to Admin",
           color=BLUEG, fs=8.5)

    ax.text(5, 0.25, "5 agents  ·  2 compiled graphs  ·  every hand-off is a graph edge",
            ha="center", fontsize=9.5, color=INK, fontstyle="italic")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def draw_hub(path):
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 8); ax.axis("off")
    ax.text(5, 7.6, "HUB — 1 agent (4 phases) + escalation, in 1 graph",
            ha="center", fontsize=14, fontweight="bold", color=SAGE_D)

    # Big Recovery Agent container
    _box(ax, 2.5, 4.2, 3.4, 4.3, "", "#EDEFE4", SAGE_D)
    ax.text(2.5, 6.05, "Recovery Agent\n(one node)", ha="center", va="center",
            fontsize=11, fontweight="bold", color=SAGE_D)
    phases = ["intake", "care plan", "monitoring", "admin"]
    ys = [5.2, 4.4, 3.6, 2.8]
    for p, y in zip(phases, ys):
        _box(ax, 2.5, y, 2.2, 0.55, p, SAGE, SAGE_D, fs=9.5)
    for i in range(len(ys) - 1):
        _arrow(ax, (2.5, ys[i]-0.30), (2.5, ys[i+1]+0.30), color=SAGE_D, lw=1.8)
    ax.text(2.5, 1.55, "the 4 phases run in order as plain function\ncalls — no graph wiring between them",
            ha="center", va="center", fontsize=8.5, color=SAGE_D, fontstyle="italic")

    # Escalation + admin follow-up + END
    _box(ax, 6.7, 4.4, 2.0, 0.9, "Escalation\nAgent", CLAY, "#7E5642", fs=10)
    _box(ax, 6.7, 2.4, 2.2, 0.9, "Admin\nfollow-up", SAGE, SAGE_D, fs=9.5)
    _box(ax, 9.2, 2.4, 1.0, 0.7, "END", "#9AA0A6", "#5F6368", fs=9)
    _box(ax, 9.2, 5.6, 1.0, 0.7, "END", "#9AA0A6", "#5F6368", fs=9)

    # the ONE real edge
    _arrow(ax, (4.25, 4.4), (5.65, 4.4), color=RED, lw=2.6)
    _label(ax, 4.95, 4.75, "RED", color=RED, fs=8)
    ax.text(4.95, 4.05, "the ONE\nreal edge", ha="center", va="center",
            fontsize=7.5, color=RED, fontstyle="italic")
    _arrow(ax, (6.7, 3.92), (6.7, 2.88))            # escalation -> admin follow-up
    _arrow(ax, (7.8, 2.4), (8.65, 2.4))             # admin -> END
    # recovery -> END (green/yellow): admin already ran inside the node
    _arrow(ax, (4.25, 5.3), (8.65, 5.55), color=BLUEG, rad=-0.12)
    _label(ax, 6.4, 5.95, "GREEN / YELLOW  (admin already ran inside the node)",
           color=BLUEG, fs=8)

    ax.text(5, 0.5, "3 nodes  ·  1 compiled graph  ·  only the escalation hand-off is a graph edge",
            ha="center", fontsize=9.5, color=INK, fontstyle="italic")
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ════════════════════════════════════════════════════════════════════════════
# 2. DATA (measured 2026-06-23/24, same patient PDF: 01_chf_john_demo.pdf)
# ════════════════════════════════════════════════════════════════════════════

GREEN_RUN = {
    "Nexus": dict(calls=3, tin=2456, tout=3078, cost=0.0535, lat=45.8),
    "Hub":   dict(calls=3, tin=2454, tout=2761, cost=0.0488, lat=42.4),
}
RED_RUN = {
    "Nexus": dict(calls=3, tin=2473, tout=3004, cost=0.0525, lat=48.5),
    "Hub":   dict(calls=3, tin=2470, tout=2986, cost=0.0522, lat=48.5),
}
STRUCT = {
    "Agents / nodes":              ("5", "3"),
    "Compiled graphs":             ("2", "1"),
    "Graph edges (fixed)":         ("3", "2"),
    "Graph edges (conditional)":   ("2", "1"),
    "Orchestration code (lines)":  ("56", "41"),
}

# ════════════════════════════════════════════════════════════════════════════
# 3. DOCUMENT
# ════════════════════════════════════════════════════════════════════════════

def set_cell_bg(cell, hexcolor):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def h(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = RGBColor.from_string(SAGE_D.lstrip("#"))
    return p


def para(doc, text, size=11, italic=False, bold=False, space_after=8):
    p = doc.add_paragraph()
    r = p.add_run(text); r.font.size = Pt(size); r.italic = italic; r.bold = bold
    p.paragraph_format.space_after = Pt(space_after)
    return p


def bullet(doc, text, bold_lead=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_lead:
        r = p.add_run(bold_lead); r.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    return p


def qa(doc, question, answer):
    pq = doc.add_paragraph()
    rq = pq.add_run("Q.  " + question); rq.bold = True; rq.font.size = Pt(11)
    rq.font.color.rgb = RGBColor.from_string(SAGE_D.lstrip("#"))
    pq.paragraph_format.space_after = Pt(2)
    pa = doc.add_paragraph()
    ra = pa.add_run("A.  " + answer); ra.font.size = Pt(11)
    pa.paragraph_format.space_after = Pt(10)
    pa.paragraph_format.left_indent = Inches(0.0)


def totals_table(doc, data, title):
    para(doc, title, bold=True, space_after=4)
    t = doc.add_table(rows=1, cols=3); t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, x in enumerate(["Metric", "Nexus (5 agents)", "Hub (1 agent)"]):
        hdr[i].paragraphs[0].add_run(x).bold = True
        set_cell_bg(hdr[i], "DDE3CE")
    rows = [
        ("Claude (AI) calls",      str(data["Nexus"]["calls"]), str(data["Hub"]["calls"])),
        ("Words in (input tokens)", f'{data["Nexus"]["tin"]:,}', f'{data["Hub"]["tin"]:,}'),
        ("Words out (output tokens)", f'{data["Nexus"]["tout"]:,}', f'{data["Hub"]["tout"]:,}'),
        ("Cost (USD)",             f'${data["Nexus"]["cost"]:.4f}', f'${data["Hub"]["cost"]:.4f}'),
        ("Time taken",             f'{data["Nexus"]["lat"]:.1f} s', f'{data["Hub"]["lat"]:.1f} s'),
    ]
    for name, a, b in rows:
        c = t.add_row().cells
        c[0].text = name; c[1].text = a; c[2].text = b
    doc.add_paragraph()


def build():
    draw_nexus("nexus_workflow.png")
    draw_hub("hub_workflow.png")

    doc = Document()
    # base font
    style = doc.styles["Normal"]; style.font.name = "Calibri"; style.font.size = Pt(11)

    # ── Title ──
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Nexus vs. Hub"); r.bold = True; r.font.size = Pt(30)
    r.font.color.rgb = RGBColor.from_string(SAGE_D.lstrip("#"))
    s = doc.add_paragraph(); s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs = s.add_run("Does splitting one AI agent into five actually help?")
    rs.italic = True; rs.font.size = Pt(14)
    d = doc.add_paragraph(); d.alignment = WD_ALIGN_PARAGRAPH.CENTER
    d.add_run("A plain-English comparison of two post-hospital recovery co-pilots  ·  June 2026").font.size = Pt(10)
    doc.add_paragraph()

    # ── The question / TL;DR ──
    h(doc, "The one-line takeaway", 1)
    para(doc,
         "I built the same product two ways — Nexus, with five specialist agents, and Hub, "
         "with a single agent doing the same work — and measured both on identical inputs. "
         "Result: the two cost and perform almost exactly the same, but Hub is built with far less "
         "plumbing. For this kind of step-by-step task, splitting the work into five agents did not "
         "make it cheaper, faster, or smarter — it mainly added wiring.", bold=False)

    # ── What each does ──
    h(doc, "What each system does", 1)
    para(doc,
         "Both are the same product: you upload a hospital discharge summary, and the system builds a "
         "30-day recovery plan, runs a daily symptom check-in, and raises an alarm if something looks "
         "dangerous. They use the same tools, the same instructions to the AI, and the same AI model. "
         "The ONLY difference is how the work is organized internally.")
    para(doc, "Nexus — the team of five specialists", bold=True, space_after=2)
    bullet(doc, "Reads the discharge PDF and pulls out the key facts.", "Intake Agent — ")
    bullet(doc, "Turns those facts into a plain-language recovery plan and checks the medicines.", "Care Plan Agent — ")
    bullet(doc, "Reviews each daily check-in and rates it green, yellow, or red.", "Monitoring Agent — ")
    bullet(doc, "Decides how urgently to act on a red flag (up to a 911 screen).", "Escalation Agent — ")
    bullet(doc, "Sends reminders and weekly summaries.", "Admin Agent — ")
    para(doc, "Hub — the single capable generalist (plus one specialist)", bold=True, space_after=2)
    bullet(doc, "One Recovery Agent does intake, care plan, monitoring, and admin — the same four jobs, "
                "just inside one component instead of four.")
    bullet(doc, "The Escalation step is kept separate on purpose — it is the only step that can take a "
                "real-world action (send an SMS, show a 911 screen), so it deserves its own clear gate.")

    # ── Diagrams ──
    h(doc, "The two designs, side by side", 1)
    para(doc, "Nexus splits the job into five boxes wired across two separate flowcharts:")
    doc.add_picture("nexus_workflow.png", width=Inches(6.3))
    doc.add_paragraph()
    para(doc, "Hub folds the four routine steps into one box and keeps a single real connection — the "
              "hand-off to Escalation:")
    doc.add_picture("hub_workflow.png", width=Inches(6.3))
    para(doc,
         "The plain-English difference: in Nexus, the work passes between five separate boxes, and every "
         "hand-off is a wired connection that has to be built and maintained. In Hub, the routine steps "
         "simply happen one after another inside a single box (ordinary code, no wiring), and only the "
         "decision that can trigger a real-world action — escalation — is kept as its own box with a real "
         "connection.", italic=True)

    # ── The experiment ──
    h(doc, "How I tested it", 1)
    para(doc,
         "To compare fairly, both systems ran the exact same inputs: the same patient discharge summary "
         "(a heart-failure case), then a daily check-in. I did this twice — once with a normal 'all good' "
         "(GREEN) check-in, and once with a 'chest pain' (RED) check-in that triggers the emergency path. "
         "Every call to the AI was measured for word count, cost, and time.")

    # ── Numbers ──
    h(doc, "The numbers", 1)
    totals_table(doc, GREEN_RUN, "Run 1 — normal 'all good' (GREEN) check-in")
    totals_table(doc, RED_RUN, "Run 2 — 'chest pain' (RED) check-in that triggers the 911 path")

    para(doc, "How the systems are built (this is where they really differ)", bold=True, space_after=4)
    st = doc.add_table(rows=1, cols=3); st.style = "Light Grid Accent 1"
    st.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = st.rows[0].cells
    for i, x in enumerate(["Build complexity", "Nexus", "Hub"]):
        hdr[i].paragraphs[0].add_run(x).bold = True; set_cell_bg(hdr[i], "DDE3CE")
    for metric, (a, b) in STRUCT.items():
        c = st.add_row().cells
        c[0].text = metric; c[1].text = a; c[2].text = b
    doc.add_paragraph()

    # ── Findings ──
    h(doc, "What I found", 1)
    bullet(doc, "Across both runs, total cost differed by less than half a cent and time by seconds. "
                "Splitting into five agents bought no measurable cost or speed advantage.",
                "Cost and speed are basically the same. ")
    bullet(doc, "The amount of information sent to the AI — the part the design actually controls — was "
                "identical to within 2 words out of ~2,450. The small differences in cost come from the "
                "AI writing a slightly longer or shorter care plan on a given run (normal variation), not "
                "from the architecture.",
                "The AI did the same amount of work. ")
    bullet(doc, "Hub uses 3 building blocks instead of 5, one flowchart instead of two, and about 15 fewer "
                "lines of wiring code. Less to build, less to break.",
                "Hub is simpler to build. ")
    bullet(doc, "A red 'chest pain' check-in produced the same outcome in both — a 911 screen — using the "
                "exact same emergency logic. Keeping that one step separate is the part of the multi-agent "
                "design that genuinely earns its place.",
                "The one boundary that matters still works. ")
    bullet(doc, "Nexus's five separate boxes make it a little easier to see which step a problem came from "
                "(each prints its own label). That is the main thing you give up by consolidating.",
                "The trade-off: ")

    # ── Bottom line ──
    h(doc, "Bottom line", 1)
    para(doc,
         "For a task like this — a fixed sequence of steps all working on one patient's data — the five "
         "agents were really a pipeline, not five independent experts. Collapsing them into one agent kept "
         "the cost, speed, and results the same while cutting the plumbing roughly in half. The lesson is "
         "not 'never use multiple agents' — it is 'add an agent boundary only where it earns its keep.' "
         "Here, exactly one did: the escalation gate that can take a real-world action. Hub keeps that one "
         "and drops the rest.", bold=False)

    # ── Note on the preserved quirk ──
    h(doc, "A note on one quirk I deliberately kept", 1)
    para(doc,
         "In Nexus, the Admin step (appointment reminders and weekly summaries) runs at the end of every "
         "daily check-in — including right after a red 'call 911' alert. That happens because Admin is the "
         "shared 'end of the day' step that every check-in passes through; on a red day the system simply "
         "inserts the Escalation step in front of it. It is harmless (Admin makes no AI call and usually has "
         "nothing to do), but on a genuine 911 it is a little tone-deaf to follow an emergency screen with a "
         "routine appointment reminder.")
    para(doc,
         "I kept this behaviour in Hub on purpose, so the two systems behave identically and the comparison "
         "stays fair. It is also a neat illustration of the project's whole point: a fixed multi-step pipeline "
         "can carry a step into a moment where it does not really belong, simply because that is how the flow "
         "is wired. A real product would gate Admin so it is skipped during a true emergency.", italic=True)

    # ── Q&A ──
    h(doc, "Questions you might have", 1)
    qa(doc,
       "Why keep the Escalation step as its own separate piece, but merge the other four?",
       "Escalation is the only step that can take a real-world action — send a text message or show a 911 "
       "screen. Every other step just has the AI reason about the patient and hand the result to the next "
       "step. A clear, separate gate in front of the one step that acts in the real world is worth the extra "
       "structure; splitting the purely-internal steps apart is not. Hub keeps that one boundary and drops "
       "the rest.")
    qa(doc,
       "How does the system decide green / yellow / red — and why does a red check-in still cost only one AI call?",
       "A single AI call reads the day's answers and labels them green (all good), yellow (worth noting), or "
       "red (urgent). Only that one call uses the AI. Everything that follows a red — deciding the urgency "
       "level, showing the 911 screen, drafting a message — is plain rules and templates, with no AI. So a "
       "dramatic red day costs the same single AI call as a calm green one.")
    qa(doc,
       "Why doesn't a yellow flag trigger an alert?",
       "Yellow means 'a little off' — a missed dose, a mild symptom — something to note and watch, not to act "
       "on. It is recorded and shown, but it deliberately does not page anyone. Only red, which means an "
       "emergency warning sign, triggers the escalation path. (Several yellows in a row are designed to be "
       "raised to red by the monitoring step.)")
    qa(doc,
       "The emergency level keys off words like 'chest pain'. What if someone describes an emergency differently?",
       "The urgency levels (up to the 911 screen) are decided by matching the patient's words against a list "
       "of keywords. This is simple and predictable, but it is a known limitation: if a serious symptom is "
       "described in unusual wording that is not on the list, it can be under-rated. This is identical in both "
       "systems (the emergency code is copied byte-for-byte), and it is the clearest place a real product "
       "would replace keyword-matching with something smarter.")
    qa(doc,
       "There is a second AI (a Llama model) that runs but its result is not shown — why?",
       "My project brief had a requirement: use at least one AI model that isn't Claude. To satisfy that, the "
       "care-plan step also asks a second model (Llama) to draft a plan — but the app ignores Llama's version "
       "and always shows Claude's. Llama's draft is just printed to the logs and thrown away. It runs off to "
       "the side (in the background) so it never makes you wait, and if its access key isn't set up it simply "
       "skips. It is left out of the cost comparison on purpose: the comparison is about the Claude pipeline, "
       "and the Llama call is only there to tick the requirement box.")
    qa(doc,
       "Why does my data disappear when I restart the app?",
       "These are demos. The current patient's information lives in the app's memory only for the session, so "
       "restarting clears it and you begin again from onboarding. Every sample patient is synthetic — there "
       "is no real patient data anywhere.")
    qa(doc,
       "Why aren't the text messages and emails actually sending?",
       "Real sending needs phone (Twilio) and email (Gmail) accounts configured. Without them — or on a free "
       "trial — those steps simply log 'skipped' and carry on, by design, so a missing account never crashes "
       "a check-in. The on-screen guidance, including the 911 screen, still appears.")
    qa(doc,
       "Are the dollar figures exact?",
       "They are calculated from the AI's word counts using standard published rates, so treat them as close "
       "estimates, not a bill. The most reliable signal in the comparison is not the dollar amount (which "
       "wobbles a little because the AI writes a slightly different-length plan each run) — it is the amount "
       "of information sent in, which the design controls and which came out essentially identical.")
    qa(doc,
       "Why doesn't the long-term 'memory' feel smart about recalling past details?",
       "The memory store uses a simplified, placeholder method for indexing text rather than true "
       "meaning-based search. It reliably stores and looks up a patient's records, but it will not do clever "
       "'find anything similar' matching. This was carried over from Nexus unchanged on purpose — improving "
       "it is a separate exercise from the single-versus-multi-agent question this project is about.")

    # ── Appendix ──
    doc.add_page_break()
    h(doc, "Appendix — per-step detail", 1)
    para(doc, "GREEN run, broken down by step (input / output words, cost, time):", bold=True, space_after=4)
    ap = doc.add_table(rows=1, cols=5); ap.style = "Light Grid Accent 1"
    for i, x in enumerate(["Step", "Nexus in/out", "Nexus cost", "Hub in/out", "Hub cost"]):
        ap.rows[0].cells[i].paragraphs[0].add_run(x).bold = True
        set_cell_bg(ap.rows[0].cells[i], "DDE3CE")
    green_detail = [
        ("Intake",     "799 / 775", "$0.0140", "798 / 794", "$0.0143"),
        ("Care plan",  "1005 / 2188", "$0.0358", "1005 / 1860", "$0.0309"),
        ("Monitoring", "652 / 115", "$0.0037", "651 / 107", "$0.0036"),
    ]
    for row in green_detail:
        c = ap.add_row().cells
        for i, v in enumerate(row):
            c[i].text = v
    doc.add_paragraph()
    para(doc, "Note: 'words in/out' are the AI's tokens; care-plan output varies run-to-run, which is the "
              "main source of the tiny cost gap. Escalation and Admin make no AI calls, so a red check-in "
              "still costs just one AI call — the emergency routing is free.", italic=True, size=10)

    out = "Nexus_vs_Hub_Comparison.docx"
    doc.save(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    build()
