# app.py
import os
import io
import re
import json
import base64
import tempfile
import uuid
from datetime import datetime
from collections import defaultdict

from flask import (
    Flask, request, redirect, url_for, render_template_string,
    session, send_file, flash
)

# --- CHANGED: server-side sessions via filesystem
from flask_session import Session

# ===== Optional heavy deps handled gracefully =====
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try: 
    import docx
except Exception:
    convert_from_bytes = None

# ===== Google Cloud Vision (OCR) =====
USE_MOCK = os.getenv("USE_MOCK", "0") == "1"
vision = None
if not USE_MOCK:
    try:
        from google.cloud import vision as vision_mod
        vision = vision_mod
    except Exception:
        vision = None

# ===== Gemini (Generative AI) =====
genai = None
if not USE_MOCK:
    try:
        import google.generativeai as genai_mod
        genai = genai_mod
    except Exception:
        genai = None

# ===== Flask app =====
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25MB PDF limit
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(16))

# --- CHANGED: Flask-Session filesystem configuration
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(tempfile.gettempdir(), "flask_sessions")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# In production behind HTTPS, uncomment:
# app.config["SESSION_COOKIE_SECURE"] = True
Session(app)

# ====== Basic HTML (single-file app) ======
PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Syllabus FAQ Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />

  <style>
    /* ========= THEME & TOKENS ========= */
    :root {
      /* color palette */
      --bg: #0b1020;
      --surface: #0f172a;
      --elev: #111827;
      --border: #1f2937;
      --text: #e5e7eb;
      --muted: #9fb0c2;
      --accent: #22d3ee;
      --accent-2: #3b82f6;
      --ok: #34d399;
      --warn: #f59e0b;
      --err: #ef4444;

      /* typography */
      --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Apple Color Emoji", "Segoe UI Emoji";
      --fs-0: clamp(14px, 0.85vw + 10px, 16px);
      --fs-1: clamp(16px, 1vw + 12px, 18px);
      --fs-2: clamp(18px, 1.2vw + 12px, 22px);
      --fs-3: clamp(20px, 1.6vw + 12px, 26px);
      --fs-4: clamp(24px, 2vw + 12px, 32px);

      /* spacing & radius */
      --space-1: 6px;
      --space-2: 10px;
      --space-3: 14px;
      --space-4: 20px;
      --space-5: 28px;
      --space-6: 40px;

      --radius-s: 10px;
      --radius-m: 14px;
      --radius-l: 18px;

      /* effects */
      --shadow-1: 0 1px 2px rgba(0,0,0,.4), 0 6px 16px rgba(0,0,0,.25);
      --shadow-2: 0 2px 8px rgba(0,0,0,.35), 0 12px 28px rgba(0,0,0,.25);

      /* component dims */
      --max-w: 1200px;
      --grid-gap: 18px;
    }

    @media (prefers-color-scheme: light) {
      :root {
        --bg: #f6f7fb;
        --surface: #ffffff;
        --elev: #ffffff;
        --border: #e5e7eb;
        --text: #0b1020;
        --muted: #5b6b7f;
      }
      .pill { background: #f1f5f9; color: #334155; border-color: #e2e8f0; }
    }

    /* ========= BASE ========= */
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      background: radial-gradient(1000px 500px at 0% -10%, rgba(34,211,238,.12), transparent 50%),
                  radial-gradient(800px 400px at 100% -10%, rgba(59,130,246,.12), transparent 50%),
                  var(--bg);
      color: var(--text);
      font: 500 var(--fs-0)/1.55 var(--font-sans);
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    a { color: var(--accent-2); text-decoration: none; }
    a:hover { text-decoration: underline; }

    /* ========= LAYOUT ========= */
    .container { max-width: var(--max-w); margin: 0 auto; padding: var(--space-5) var(--space-4); }
    header.site {
      backdrop-filter: saturate(120%) blur(6px);
      background: linear-gradient(180deg, rgba(15,23,42,.8), rgba(15,23,42,.55));
      border-bottom: 1px solid var(--border);
      position: sticky; top: 0; z-index: 20;
    }
    .header-inner {
      max-width: var(--max-w);
      margin: 0 auto; padding: var(--space-3) var(--space-4);
      display: flex; align-items: center; gap: var(--space-3);
    }
    .brand { display: flex; align-items: center; gap: var(--space-2); }
    .brand h1 { font-size: var(--fs-3); margin: 0; letter-spacing: .2px; }
    .pill {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 4px 10px; border-radius: 999px; font-size: 12px;
      background: #0d1b2a; border: 1px solid var(--border); color: var(--muted);
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: var(--grid-gap);
    }
    .col-8 { grid-column: span 8; }
    .col-4 { grid-column: span 4; }
    .col-12 { grid-column: span 12; }

    @media (max-width: 980px) {
      .col-8, .col-4 { grid-column: span 12; }
    }

    /* ========= CARDS ========= */
    .card {
      background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(255,255,255,0)) , var(--elev);
      border: 1px solid var(--border);
      border-radius: var(--radius-m);
      padding: var(--space-4);
      box-shadow: var(--shadow-1);
    }
    .card h2 {
      margin: 0 0 var(--space-2) 0;
      font-size: var(--fs-2);
      line-height: 1.3;
      letter-spacing: .2px;
    }
    .subtle { color: var(--muted); font-size: var(--fs-0); }

    /* ========= FORMS ========= */
    .form-row { display: flex; gap: var(--space-3); align-items: center; flex-wrap: wrap; }
    .input, .btn {
      border-radius: var(--radius-s);
      border: 1px solid var(--border);
      padding: 12px 14px;
      font: inherit;
      transition: border-color .15s ease, box-shadow .15s ease, transform .04s ease;
    }
    .input {
      width: 100%;
      background: var(--surface);
      color: var(--text);
      outline: none;
    }
    .input:focus {
      border-color: color-mix(in hsl, var(--accent) 55%, white 45%);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 25%, transparent);
    }

    .btn {
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
      color: white; border: 0; cursor: pointer; font-weight: 600;
      padding-inline: 16px;
      box-shadow: 0 2px 8px rgba(34,211,238,.25), 0 6px 20px rgba(59,130,246,.25);
    }
    .btn:hover { transform: translateY(-1px); }
    .btn:active { transform: translateY(0); }
    .btn[disabled] { opacity: .6; cursor: not-allowed; box-shadow: none; }

    /* ========= ALERTS ========= */
    .alerts { display: grid; gap: 10px; margin-bottom: var(--space-3); }
    .alert {
      padding: 10px 14px; border-radius: var(--radius-s);
      border: 1px solid var(--border); background: var(--surface);
    }
    .alert.ok { border-color: color-mix(in srgb, var(--ok) 50%, var(--border)); background: rgba(52,211,153,.12); }
    .alert.err { border-color: color-mix(in srgb, var(--err) 50%, var(--border)); background: rgba(239,68,68,.12); }

    /* ========= FAQ ========= */
    .faq-grid {
      display: grid; gap: var(--grid-gap);
      grid-template-columns: repeat(12, minmax(0,1fr));
    }
    .faq-item { grid-column: span 6; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-s); padding: var(--space-3); }
    .faq-item h3 { margin: 0 0 6px 0; font-size: var(--fs-1); }
    .faq-wide { grid-column: 1 / -1; }

    @media (max-width: 820px) {
      .faq-item { grid-column: span 12; }
    }

    /* ========= MEDIA / CODE ========= */
    .chart { width: 100%; height: auto; border-radius: var(--radius-s); border: 1px solid var(--border); background: var(--surface); }
    details.disclosure {
      border: 1px dashed var(--border); border-radius: var(--radius-s); padding: var(--space-2) var(--space-3);
      background: var(--surface);
    }
    summary { cursor: pointer; font-weight: 600; }
    pre.code {
      white-space: pre-wrap; font-size: 12px; line-height: 1.5;
      background: var(--surface); padding: var(--space-3);
      border-radius: var(--radius-s); border: 1px solid var(--border);
      max-height: 420px; overflow: auto;
    }

    /* ========= UTILITIES ========= */
    .stack-s > * + * { margin-top: var(--space-2); }
    .stack-m > * + * { margin-top: var(--space-3); }
    .stack-l > * + * { margin-top: var(--space-4); }
    .divider { height: 1px; background: var(--border); margin: var(--space-3) 0; border: 0; }
    .footer { color: var(--muted); margin-top: var(--space-5); display: flex; align-items: center; gap: var(--space-2); }
    .kbd { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono"; background: var(--surface); border: 1px solid var(--border); padding: 2px 6px; border-radius: 6px; font-size: 12px;}
  </style>
</head>

<body>
  <!-- ======= HEADER ======= -->
  <header class="site" role="banner">
    <div class="header-inner">
      <div class="brand">
        <div aria-hidden="true">📚</div>
        <h1>Syllabus FAQ Dashboard</h1>
      </div>
      <span class="pill" title="Tech stack">Flask · Google Vision · Gemini · Matplotlib</span>
    </div>
  </header>

  <!-- ======= CONTENT ======= -->
  <main class="container" role="main">
    <!-- Alerts -->
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <div class="alerts" role="status" aria-live="polite">
          {% for category, message in messages %}
            <div class="alert {{ 'ok' if category=='success' else 'err' }}">{{ message|safe }}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}

    <section class="grid stack-l">
      <!-- Upload -->
      <div class="card col-8 stack-m" aria-labelledby="uploadTitle">
        <h2 id="uploadTitle">Upload Syllabus (PDF)</h2>
        <p class="subtle">We’ll OCR it with Google Vision, extract policies &amp; schedule with Gemini, then build charts.</p>

        <form method="POST" action="{{ url_for('upload') }}" enctype="multipart/form-data" class="form-row" aria-label="Upload PDF">
          <input class="input" type="file" name="pdf" accept="application/pdf" required aria-label="Choose PDF file" />
          <button class="btn" type="submit">Process PDF</button>
        </form>

        {% if syllabus_summary %}
          <hr class="divider" />
          <details class="disclosure" open>
            <summary><strong>Summary</strong> (auto-generated)</summary>
            <p class="subtle" style="margin-top:8px;">{{ syllabus_summary }}</p>
          </details>
        {% endif %}
      </div>

      <!-- Ask -->
      <div class="card col-4 stack-m" aria-labelledby="askTitle">
        <h2 id="askTitle">Ask a Question</h2>
        <p class="subtle">Ask anything about this course’s policies or schedule.</p>

        <form method="POST" action="{{ url_for('ask') }}" class="form-row" aria-label="Ask a question">
          <input class="input" type="text" name="question" placeholder="e.g., What’s the late submission penalty?" required aria-label="Your question" />
          <button class="btn" type="submit" {% if not syllabus_text %}disabled aria-disabled="true"{% endif %}>Ask</button>
        </form>

        {% if answer %}
          <hr class="divider" />
          <div aria-live="polite"><strong>Answer:</strong> {{ answer }}</div>
        {% endif %}
      </div>

      <!-- FAQs -->
      {% if faq %}
      <div class="card col-12 stack-m">
        <h2>Extracted FAQs</h2>
        <div class="faq-grid">
          <div class="faq-item">
            <h3>📌 Late Work Policy</h3>
            <div class="subtle">{{ faq.get('late_work_policy','—') }}</div>
          </div>
          <div class="faq-item">
            <h3>🧍 Attendance Policy</h3>
            <div class="subtle">{{ faq.get('attendance_policy','—') }}</div>
          </div>
          <div class="faq-item faq-wide">
            <h3>🏗️ Course Structure</h3>
            <div class="subtle">{{ faq.get('course_structure','—') }}</div>
          </div>
        </div>
      </div>
      {% endif %}

      <!-- Charts -->
      {% if schedule %}
      <div class="card col-8 stack-m">
        <h2>Grade % by Week (Cumulative)</h2>
        <img class="chart" src="{{ url_for('chart_weights') }}" alt="Line chart of cumulative grade percentage by week" />
        <p class="subtle">Shows the cumulative portion of the final grade allocated up to each week.</p>
      </div>

      <div class="card col-4 stack-m">
        <h2>Assignments by Week</h2>
        <img class="chart" src="{{ url_for('chart_assignments') }}" alt="Bar chart of number of assignments per week" />
        <p class="subtle">Counts of assessments/assignments detected for each week.</p>
      </div>

      <div class="card col-12 stack-m">
        <h2>Structured Schedule (JSON)</h2>
        <pre class="code">{{ schedule|tojson(indent=2) }}</pre>
      </div>
      {% endif %}

      <!-- Raw OCR Text -->
      {% if syllabus_text %}
      <div class="card col-12 stack-m">
        <h2>Raw OCR Text</h2>
        <details class="disclosure">
          <summary>Toggle OCR text</summary>
          <pre class="code" aria-label="OCR text">{{ syllabus_text }}</pre>
        </details>
      </div>
      {% endif %}
    </section>

    <footer class="footer">
      <span>Built with Flask, Google Vision, Gemini, and Matplotlib.</span>
      {% if use_mock %}<span class="pill" title="Using built-in demo data">Mock Mode</span>{% endif %}
    </footer>
  </main>
</body>
</html>

"""

# ===== Helpers =====

def ensure_genai():
    """Configure Gemini once per process."""
    global genai
    if USE_MOCK:
        return None
    if genai is None:
        raise RuntimeError("google.generativeai not available. Install google-generativeai.")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    genai.configure(api_key=api_key)
    return genai

def ocr_pdf_with_vision(pdf_bytes: bytes) -> str:
    """
    Convert PDF to page images, then OCR with Google Cloud Vision.
    Returns concatenated text.
    If USE_MOCK, returns a realistic sample.
    """
    if USE_MOCK:
        return (
            "Course: Intro to Data Science (Fall 2025)\n"
            "Instructor: Dr. Smith\n"
            "Attendance: Required; more than 2 unexcused absences reduces final grade by one letter.\n"
            "Late work: 10% penalty per day up to 3 days; no submissions after 72 hours.\n"
            "Grading: Homework 30%, Project 30%, Midterm 20%, Final 20%.\n"
            "Weekly schedule:\n"
            "Week 1: Syllabus, HW0 (0%).\n"
            "Week 2: Python basics, HW1 (5%).\n"
            "Week 3: EDA, HW2 (5%).\n"
            "Week 4: Data Wrangling, Quiz 1 (5%).\n"
            "Week 5: Modeling 1, Project Proposal (5%).\n"
            "Week 6: Modeling 2, HW3 (5%).\n"
            "Week 7: Midterm (20%).\n"
            "Week 8: Feature Engineering, HW4 (5%).\n"
            "Week 9: Model Evaluation, HW5 (5%).\n"
            "Week 10: Project Milestone (10%).\n"
            "Week 11: Ethics, HW6 (5%).\n"
            "Week 12: Deployment, Quiz 2 (5%).\n"
            "Week 13: Presentations, Final Project (20%).\n"
        )

    if vision is None:
        raise RuntimeError("google-cloud-vision not available. Install google-cloud-vision or use USE_MOCK=1.")

    # Convert PDF → images
    images = []
    if fitz is not None:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                images.append(pix.tobytes("png"))
        finally:
            doc.close()
    elif convert_from_bytes is not None:
        pil_pages = convert_from_bytes(pdf_bytes, dpi=200)
        for img in pil_pages:
            with io.BytesIO() as buf:
                img.save(buf, format="PNG")
                images.append(buf.getvalue())
    else:
        raise RuntimeError("No PDF renderer found (PyMuPDF or pdf2image). Install one or set USE_MOCK=1.")

    client = vision.ImageAnnotatorClient()
    texts = []
    for idx, img_bytes in enumerate(images, start=1):
        image = vision.Image(content=img_bytes)
        resp = client.text_detection(image=image)
        if resp.error.message:
            raise RuntimeError(f"Vision OCR error on page {idx}: {resp.error.message}")
        if resp.text_annotations:
            texts.append(resp.text_annotations[0].description)
    return "\n".join(texts).strip()

# --- CHANGED: helpers to persist/retrieve large blobs outside the cookie session
def _save_large_blob(prefix: str, content: str) -> str:
    """Persist large text to a temp file; return its path."""
    path = os.path.join(tempfile.gettempdir(), f"{prefix}-{uuid.uuid4().hex}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path

def _read_blob(path: str) -> str:
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def extract_structured_with_gemini(ocr_text: str):
    """
    Ask Gemini to parse:
      - FAQs: late_work_policy, attendance_policy, course_structure
      - Weekly schedule array of {week:int, assignments:int, weight_pct:float, notes:str}
      - A short summary
    Returns (faq_dict, schedule_list, summary_str)
    """
    if USE_MOCK:
        faq = {
            "late_work_policy": "10% per day late up to 3 days; no submissions after 72 hours.",
            "attendance_policy": "Attendance required; >2 unexcused absences = final grade reduced by one letter.",
            "course_structure": "Weekly lectures + labs; 6 HWs, 2 quizzes, 1 midterm, final project & presentation."
        }
        schedule = [
            {"week": 1, "assignments": 1, "weight_pct": 0, "notes": "HW0 (setup)"},
            {"week": 2, "assignments": 1, "weight_pct": 5, "notes": "HW1"},
            {"week": 3, "assignments": 1, "weight_pct": 5, "notes": "HW2"},
            {"week": 4, "assignments": 1, "weight_pct": 5, "notes": "Quiz 1"},
            {"week": 5, "assignments": 1, "weight_pct": 5, "notes": "Project proposal"},
            {"week": 6, "assignments": 1, "weight_pct": 5, "notes": "HW3"},
            {"week": 7, "assignments": 1, "weight_pct": 20, "notes": "Midterm"},
            {"week": 8, "assignments": 1, "weight_pct": 5, "notes": "HW4"},
            {"week": 9, "assignments": 1, "weight_pct": 5, "notes": "HW5"},
            {"week":10, "assignments": 1, "weight_pct":10, "notes": "Project milestone"},
            {"week":11, "assignments": 1, "weight_pct": 5, "notes": "HW6"},
            {"week":12, "assignments": 1, "weight_pct": 5, "notes": "Quiz 2"},
            {"week":13, "assignments": 1, "weight_pct":20, "notes": "Final project"}
        ]
        summary = "Course mixes weekly HWs, two quizzes, a midterm, and a final project; strict late policy; attendance required."
        return faq, schedule, summary

    ensure_genai()
    model = genai.GenerativeModel("gemini-flash-latest")

    system_instructions = (
        "You are extracting structured policy and schedule data from a course syllabus OCR text.\n"
        "Return STRICT JSON with keys: faq, schedule, summary.\n"
        "faq must include: late_work_policy, attendance_policy, course_structure (all strings).\n"
        "schedule is an array of objects with keys: week (int), assignments (int), weight_pct (float), notes (string).\n"
        "Interpret weights by week as the total percentage of final grade assessed that week (sum may be ~100%). "
        "If a week mentions multiple graded items, sum their percentages in that week and set assignments count accordingly. "
        "If an item is ungraded, weight_pct=0 but still increment assignments if it's an assignment.\n"
        "summary: one-sentence overview.\n"
        "Only output JSON. No markdown."
    )

    prompt = f"{system_instructions}\n\nOCR_TEXT_START\n{ocr_text}\nOCR_TEXT_END"
    resp = model.generate_content(prompt)
    text = (resp.text or "").strip()
    try:
        data = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise RuntimeError("Gemini did not return valid JSON.")
        data = json.loads(m.group(0))

    faq = data.get("faq", {})
    schedule = data.get("schedule", [])
    summary = data.get("summary", "")
    norm = []
    for item in schedule:
        try:
            norm.append({
                "week": int(item.get("week")),
                "assignments": int(item.get("assignments", 0)),
                "weight_pct": float(item.get("weight_pct", 0.0)),
                "notes": str(item.get("notes", "")).strip()
            })
        except Exception:
            continue
    norm.sort(key=lambda x: x["week"])
    return faq, norm, summary


def compute_cumulative_weights(schedule):
    weeks = []
    cumulative = []
    total = 0.0
    for item in sorted(schedule, key=lambda x: x["week"]):
        weeks.append(item["week"])
        total += float(item.get("weight_pct", 0.0))
        cumulative.append(total)
    return weeks, cumulative


def compute_assignments_by_week(schedule):
    weeks = []
    counts = []
    for item in sorted(schedule, key=lambda x: x["week"]):
        weeks.append(item["week"])
        counts.append(int(item.get("assignments", 0)))
    return weeks, counts


# ===== Routes =====

@app.route("/", methods=["GET"])
def index():
    # --- CHANGED: read OCR text from temp file path stored in session
    syllabus_text = _read_blob(session.get("syllabus_text_path", ""))
    return render_template_string(
        PAGE,
        faq=session.get("faq"),
        schedule=session.get("schedule"),
        syllabus_text=syllabus_text,
        syllabus_summary=session.get("syllabus_summary"),
        answer=session.pop("last_answer", None),
        use_mock=USE_MOCK
    )

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("pdf")
    if not file or file.filename == "":
        flash("Please choose a PDF file.", "error")
        return redirect(url_for("index"))

    if not file.filename.lower().endswith(".pdf"):
        flash("Only PDF files are supported.", "error")
        return redirect(url_for("index"))

    try:
        pdf_bytes = file.read()
        ocr_text = ocr_pdf_with_vision(pdf_bytes)
        faq, schedule, summary = extract_structured_with_gemini(ocr_text)

        # --- CHANGED: persist large OCR text to a temp file; store only the path in session
        ocr_text_path = _save_large_blob("syllabus", ocr_text)
        session["syllabus_text_path"] = ocr_text_path

        # Keep small data in session (FAQ, schedule, summary). If they get large, persist similarly.
        session["faq"] = faq
        session["schedule"] = schedule
        session["syllabus_summary"] = summary

        total_weight = sum(float(i.get("weight_pct", 0.0)) for i in schedule)
        if 90 <= total_weight <= 110:
            flash(f"OCR + parsing complete. Detected total grading weight ≈ <b>{total_weight:.1f}%</b>.", "success")
        else:
            flash(f"OCR + parsing complete. Detected total grading weight ≈ <b>{total_weight:.1f}%</b> (may be incomplete).", "success")

    except Exception as e:
        flash(f"Processing failed: {e}", "error")

    return redirect(url_for("index"))

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question", "").strip()
    if not question:
        flash("Please enter a question.", "error")
        return redirect(url_for("index"))

    # --- CHANGED: load OCR text from temp file rather than session blob
    ocr_text = _read_blob(session.get("syllabus_text_path", ""))

    if not ocr_text:
        flash("Upload a syllabus first.", "error")
        return redirect(url_for("index"))

    try:
        if USE_MOCK:
            answer = f"(Demo) Based on the syllabus: {question} → Late penalty is 10%/day up to 3 days; attendance mandatory."
        else:
            ensure_genai()
            model = genai.GenerativeModel("gemini-flash-latest")
            qa_prompt = (
                "You are a helpful assistant answering questions ONLY from the provided syllabus text.\n"
                "If the answer is not present, say you cannot find it. Keep responses concise.\n"
                f"SYLLABUS_START\n{ocr_text}\nSYLLABUS_END\n\n"
                f"QUESTION: {question}\n"
                "ANSWER:"
            )
            resp = model.generate_content(qa_prompt)
            answer = (resp.text or "").strip() or "I couldn't find that in the syllabus."

        session["last_answer"] = answer
    except Exception as e:
        session["last_answer"] = f"Q&A failed: {e}"

    return redirect(url_for("index"))

# ===== Charts (Matplotlib) =====
@app.route("/chart/weights")
def chart_weights():
    schedule = session.get("schedule", [])
    if not schedule:
        return _blank_png()

    weeks, cumulative = compute_cumulative_weights(schedule)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(weeks, cumulative, marker="o")
    ax.set_xlabel("Week")
    ax.set_ylabel("Cumulative % of Final Grade")
    ax.set_title("Cumulative Grade Allocation by Week")
    ax.grid(True, which="both", linestyle="--", alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/chart/assignments")
def chart_assignments():
    schedule = session.get("schedule", [])
    if not schedule:
        return _blank_png()

    weeks, counts = compute_assignments_by_week(schedule)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(weeks, counts)
    ax.set_xlabel("Week")
    ax.set_ylabel("# Assignments")
    ax.set_title("Assignments per Week")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

def _blank_png():
    """Return a tiny transparent PNG placeholder."""
    pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAuMBgMc1A8kAAAAASUVORK5CYII=")
    return send_file(io.BytesIO(pixel), mimetype="image/png")

# ===== Main =====
if __name__ == "__main__":
    if USE_MOCK:
        print(">>> Running in MOCK mode (no external API calls). Set USE_MOCK=1 explicitly.")
    else:
        if not os.getenv("GEMINI_API_KEY"):
            print("WARNING: GEMINI_API_KEY not set; Q&A and structured extraction will fail.")
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            print("WARNING: GOOGLE_APPLICATION_CREDENTIALS not set; Vision OCR will fail.")

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=True)
