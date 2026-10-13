# ============================== app.py ==============================

"""QPDF - The Queryable PDF Assistant (Streamlit).



CHANGES IN THIS VERSION (nothing else was touched):

1\. Feedback text input + textarea: dark background, white (#FFFFFF) typed text, light-gray

   placeholder, visible caret / border / focus / selection. Scoped to the Feedback page only

   through st.container(key="feedback_wrap") -> CSS class .st-key-feedback_wrap, so the AI

   question input and every other input keep their existing style.

2\. Your code has no button labelled "Change". The per-file action next to each uploaded PDF is

   "Remove PDF", so it is treated as the secondary action (white background, dark text, subtle

   border, 42px height, centred next to its file card). It still calls remove_file().

   If "Change" is a different button in your local copy, give it key="change_..." and it

   receives the same style through the .st-key-change_ selectors below.

Requires Streamlit >= 1.39 (container keys / .st-key-* classes).



BACKEND: unchanged interface from your original app.py:

    from rag import LLM_NAME, PDFQAEngine

    engine.load_pdf(pdf_path)                  -> (chunks, index)

    engine.retrieve(question, chunks, index)   -> [{"page", "text", "score"}, ...]

    engine.ask(pdf_path, question)             -> (answer, anything)

Optional: engine.generate(question, sources) -> str is used for multi-PDF answers if present.

Upload limit: set \`maxUploadSize = 10\` under [server] in .streamlit/config.toml if needed.

"""

import hashlib

import html

import json

import os

import tempfile

from datetime import datetime



import streamlit as st

import streamlit.components.v1 as components



from rag import LLM_NAME, PDFQAEngine



MAX_MB = 10

TOP_K_TOTAL = 6

EXCERPT_CHARS = 900

FEEDBACK_FILE = "feedback.json"

PAGES = ["Home", "How It Works", "Features", "Feedback"]



st.set_page_config(page_title="QPDF - The Queryable PDF Assistant", page_icon="📄",

                   layout="wide", initial_sidebar_state="expanded")



# ----------------------------------------------------------------------------- CSS

st.markdown("""

<style>

:root{--bg:#F5F7FF;--accent:#635BFF;--accent-h:#5147E5;--head:#171B34;--sec:#667085;

      --card:#FFFFFF;--border:#E3E7F2;--subtle:#F0F2FF;}

.stApp{background:var(--bg);font-family:'Inter',-apple-system,'Segoe UI',Roboto,sans-serif;color:var(--head);}

header[data-testid="stHeader"]{background:transparent;}

footer{visibility:hidden;}

.block-container{max-width:1100px;padding-top:1rem;padding-bottom:3rem;}



/* text colours (always dark, high contrast) */

.stApp [data-testid="stMarkdownContainer"] p,

.stApp [data-testid="stMarkdownContainer"] li,

.stApp [data-testid="stMarkdownContainer"] ol,

.stApp [data-testid="stMarkdownContainer"] ul,

.stApp [data-testid="stMarkdownContainer"] td,

.stApp [data-testid="stMarkdownContainer"] th{color:var(--head);}

.stApp h1,.stApp h2,.stApp h3,.stApp h4{color:var(--head)!important;letter-spacing:-0.01em;}

.stApp [data-testid="stCaptionContainer"] p,.stApp .stCaption{color:var(--sec)!important;}

.stApp label p{color:var(--head)!important;font-weight:600;}



/* bordered containers = white cards (nav bar, ask card, answer card, sources card) */

div[data-testid="stVerticalBlockBorderWrapper"]{background:var(--card);border:1px solid var(--border)!important;

  border-radius:16px;box-shadow:0 6px 20px rgba(23,27,52,.05);}

div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] p,

div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] li{

  font-size:1.02rem;line-height:1.75;margin-bottom:.7rem;}

div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] li{margin-bottom:.35rem;}

div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] h1{font-size:1.35rem;margin:.8rem 0 .4rem;}

div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] h2{font-size:1.2rem;margin:.8rem 0 .4rem;}

div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] h3{font-size:1.08rem;margin:.7rem 0 .3rem;}



/* brand */

.brand{display:flex;align-items:center;gap:12px;padding:4px 0;}

.brand-logo{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,#635BFF,#8B85FF);

  display:flex;align-items:center;justify-content:center;box-shadow:0 6px 16px rgba(99,91,255,.3);flex:0 0 auto;}

.brand-name{font-weight:800;font-size:1.3rem;color:var(--head);line-height:1.1;}

.brand-sub{font-size:.76rem;color:var(--sec);}



/* LEFT SIDEBAR NAVIGATION: styles are scoped to Streamlit's sidebar */
[data-testid="stSidebar"]{background:#FFFFFF;border-right:1px solid var(--border);}
@media (min-width:761px){[data-testid="stSidebar"]{width:252px!important;min-width:252px!important;}}
[data-testid="stSidebar"] > div:first-child{padding-top:1.15rem;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:var(--head);}
[data-testid="stSidebar"] .brand{gap:11px;padding:.4rem .35rem 1.5rem;align-items:center;}
[data-testid="stSidebar"] .brand-logo{width:40px;height:40px;border-radius:12px;}
[data-testid="stSidebar"] .brand-name{font-size:1.28rem;letter-spacing:-.03em;}
[data-testid="stSidebar"] .brand-sub{font-size:.72rem;line-height:1.45;max-width:155px;}
[data-testid="stSidebar"] .nav-section-label{font-size:.7rem;font-weight:750;letter-spacing:.11em;text-transform:uppercase;color:#98A2B3;padding:.25rem .7rem .55rem;}
[data-testid="stSidebar"] [class*="st-key-nav_item_"]{margin:0 0 .28rem 0;}
[data-testid="stSidebar"] [class*="st-key-nav_item_"] button{width:100%;justify-content:flex-start;text-align:left;min-height:43px;padding:.55rem .8rem!important;border:1px solid transparent!important;border-radius:10px!important;background:transparent!important;box-shadow:none!important;transition:background .18s ease,color .18s ease,border-color .18s ease;}
[data-testid="stSidebar"] [class*="st-key-nav_item_"] button p{font-size:.94rem;font-weight:550;color:var(--head)!important;margin:0;}
[data-testid="stSidebar"] [class*="st-key-nav_item_"] button:hover{background:var(--subtle)!important;border-color:#E5E7FF!important;}
[data-testid="stSidebar"] [class*="st-key-nav_item_"] button:focus-visible{outline:2px solid var(--accent)!important;outline-offset:2px;}
[data-testid="stSidebar"] [class*="st-key-nav_active_"] button{background:var(--subtle)!important;border-color:#E0DEFF!important;}
[data-testid="stSidebar"] [class*="st-key-nav_active_"] button p{color:var(--accent)!important;font-weight:750!important;}
[data-testid="stSidebar"] .sidebar-footer{position:relative;margin-top:2rem;padding:1rem .7rem 0;border-top:1px solid var(--border);color:var(--sec);font-size:.78rem;line-height:1.6;}
[data-testid="stSidebar"] [data-testid="stButton"] button{white-space:normal;}

/* BUTTONS: primary / secondary hierarchy (no blanket selector) */

.stApp button[data-testid="stBaseButton-primary"],

.stApp button[data-testid="stBaseButton-primaryFormSubmit"],

.stApp button[kind="primary"],.stApp button[kind="primaryFormSubmit"]{

  background:var(--accent)!important;border:1px solid var(--accent)!important;border-radius:10px!important;

  min-height:42px;padding:.45rem 1.3rem!important;font-weight:600!important;

  box-shadow:0 4px 12px rgba(99,91,255,.25);transition:all .2s ease;}

.stApp button[data-testid="stBaseButton-primary"] *,

.stApp button[data-testid="stBaseButton-primaryFormSubmit"] *,

.stApp button[kind="primary"] *,.stApp button[kind="primaryFormSubmit"] *{color:#fff!important;}

.stApp button[data-testid="stBaseButton-primary"]:hover,

.stApp button[data-testid="stBaseButton-primaryFormSubmit"]:hover,

.stApp button[kind="primary"]:hover,.stApp button[kind="primaryFormSubmit"]:hover{

  background:var(--accent-h)!important;border-color:var(--accent-h)!important;transform:translateY(-1px);}

.stApp button[data-testid="stBaseButton-primary"]:focus-visible,

.stApp button[data-testid="stBaseButton-primaryFormSubmit"]:focus-visible{

  outline:3px solid rgba(99,91,255,.35)!important;outline-offset:2px;}

.stApp button[data-testid="stBaseButton-secondary"],

.stApp button[data-testid="stBaseButton-secondaryFormSubmit"],

.stApp button[kind="secondary"],.stApp button[kind="secondaryFormSubmit"]{

  background:#fff!important;border:1px solid var(--border)!important;border-radius:10px!important;

  min-height:38px;padding:.3rem 1rem!important;font-weight:600!important;box-shadow:none;transition:all .2s ease;}

.stApp button[data-testid="stBaseButton-secondary"] *,

.stApp button[data-testid="stBaseButton-secondaryFormSubmit"] *,

.stApp button[kind="secondary"] *{color:var(--head)!important;}

.stApp button[data-testid="stBaseButton-secondary"]:hover,

.stApp button[kind="secondary"]:hover{border-color:var(--accent)!important;background:var(--subtle)!important;}

.stApp button[data-testid="stBaseButton-secondary"]:focus-visible{outline:3px solid rgba(99,91,255,.3)!important;}



/* PER-FILE ACTION BUTTON ("Remove PDF" / "Change"): secondary style, consistent height, scoped by key */

.stApp [class*="st-key-rm_"] button,.stApp [class*="st-key-change_"] button{

  background:#fff!important;border:1px solid var(--border)!important;border-radius:10px!important;

  min-height:42px;height:42px;padding:0 1.1rem!important;font-weight:600!important;font-size:.92rem;

  line-height:1;box-shadow:none!important;white-space:nowrap;transition:background .15s ease,border-color .15s ease;}

.stApp [class*="st-key-rm_"] button *,.stApp [class*="st-key-change_"] button *{

  color:var(--head)!important;font-weight:600!important;}

.stApp [class*="st-key-rm_"] button:hover,.stApp [class*="st-key-change_"] button:hover{

  background:var(--subtle)!important;border-color:var(--accent)!important;transform:none;}

.stApp [class*="st-key-rm_"] button:hover *,.stApp [class*="st-key-change_"] button:hover *{color:var(--accent)!important;}

.stApp [class*="st-key-rm_"] button:focus-visible,.stApp [class*="st-key-change_"] button:focus-visible{

  outline:3px solid rgba(99,91,255,.3)!important;outline-offset:2px;}



/* uploader: light drag & drop area, purple "Upload PDF" browse button */

div[data-testid="stFileUploader"]{background:#fff;border:2px dashed #C9CDF5;border-radius:18px;padding:1rem;

  box-shadow:0 10px 30px rgba(99,91,255,.08);transition:all .25s ease;}

div[data-testid="stFileUploader"]:hover{border-color:var(--accent);background:#FAFAFF;}

div[data-testid="stFileUploaderDropzone"]{background:var(--subtle)!important;border:none!important;border-radius:14px;}

div[data-testid="stFileUploaderDropzone"] span,div[data-testid="stFileUploaderDropzone"] small{color:var(--sec)!important;}

div[data-testid="stFileUploaderDropzoneInstructions"] small{display:none;}

div[data-testid="stFileUploaderDropzone"] button{background:var(--accent)!important;border:1px solid var(--accent)!important;

  border-radius:10px!important;font-weight:600!important;min-height:42px;padding:.45rem 1.3rem!important;}

div[data-testid="stFileUploaderDropzone"] button *{color:#fff!important;}

div[data-testid="stFileUploaderDropzone"] button:hover{background:var(--accent-h)!important;}



/* form inputs (light theme: question box etc.) */

div[data-baseweb="input"],div[data-baseweb="textarea"],div[data-baseweb="select"] > div{

  background:#fff!important;border:1px solid var(--border)!important;border-radius:10px!important;}

div[data-baseweb="input"]:focus-within,div[data-baseweb="textarea"]:focus-within{

  border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(99,91,255,.15)!important;}

div[data-baseweb="input"] input,div[data-baseweb="textarea"] textarea{color:var(--head)!important;

  -webkit-text-fill-color:var(--head)!important;background:#fff!important;}

div[data-testid="stForm"]{background:#fff;border:1px solid var(--border);border-radius:16px;padding:1.1rem;}



/* FEEDBACK PAGE ONLY: dark inputs with white text (scoped via .st-key-feedback_wrap) */

.st-key-feedback_wrap div[data-baseweb="input"],

.st-key-feedback_wrap div[data-baseweb="textarea"],

.st-key-feedback_wrap div[data-testid="stTextInputRootElement"],

.st-key-feedback_wrap div[data-testid="stTextAreaRootElement"]{

  background:#1E2235!important;border:1px solid #475069!important;border-radius:10px!important;}

.st-key-feedback_wrap div[data-baseweb="input"] > div,

.st-key-feedback_wrap div[data-baseweb="textarea"] > div{background:#1E2235!important;}

.st-key-feedback_wrap div[data-baseweb="input"] input,

.st-key-feedback_wrap div[data-baseweb="textarea"] textarea,

.st-key-feedback_wrap input[type="text"],

.st-key-feedback_wrap textarea{

  background:#1E2235!important;color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;

  caret-color:#FFFFFF!important;opacity:1!important;}

.st-key-feedback_wrap div[data-baseweb="input"] input::placeholder,

.st-key-feedback_wrap div[data-baseweb="textarea"] textarea::placeholder,

.st-key-feedback_wrap input::placeholder,

.st-key-feedback_wrap textarea::placeholder{

  color:#CBD5E1!important;-webkit-text-fill-color:#CBD5E1!important;opacity:1!important;}

.st-key-feedback_wrap div[data-baseweb="input"]:focus-within,

.st-key-feedback_wrap div[data-baseweb="textarea"]:focus-within,

.st-key-feedback_wrap div[data-testid="stTextInputRootElement"]:focus-within,

.st-key-feedback_wrap div[data-testid="stTextAreaRootElement"]:focus-within{

  border-color:#635BFF!important;box-shadow:0 0 0 3px rgba(99,91,255,.45)!important;}

.st-key-feedback_wrap input::selection,.st-key-feedback_wrap textarea::selection{

  background:#635BFF!important;color:#FFFFFF!important;-webkit-text-fill-color:#FFFFFF!important;}

.st-key-feedback_wrap input:-webkit-autofill{

  -webkit-text-fill-color:#FFFFFF!important;-webkit-box-shadow:0 0 0 1000px #1E2235 inset!important;caret-color:#FFFFFF!important;}



/* hero */

.hero{text-align:center;margin:1.2rem auto 1.4rem auto;max-width:760px;}

.hero h1{font-size:2.7rem;font-weight:800;margin-bottom:.5rem;}

.hero h1 span{color:var(--accent);}

.hero p{color:var(--sec);font-size:1.08rem;}



/* generic card + pages */

.card{background:#fff;border:1px solid var(--border);border-radius:16px;padding:1.2rem 1.4rem;

  box-shadow:0 6px 20px rgba(23,27,52,.05);margin-bottom:1rem;}

.card h4{margin:0 0 .3rem 0;}

.muted{color:var(--sec);font-size:.92rem;}



/* file cards */

.file{background:#fff;border:1px solid var(--border);border-radius:14px;padding:.75rem 1rem;

  display:flex;justify-content:space-between;align-items:center;gap:10px;box-shadow:0 2px 8px rgba(23,27,52,.04);}

.file-name{font-weight:600;color:var(--head);word-break:break-all;}

.file-meta{font-size:.8rem;color:var(--sec);}

.badge{padding:.2rem .7rem;border-radius:999px;font-size:.75rem;font-weight:700;white-space:nowrap;}

.b-ready{background:#D1FAE5;color:#065F46;} .b-fail{background:#FEE2E2;color:#991B1B;}

.b-proc{background:#FEF3C7;color:#92400E;}



/* stepper */

.stepper{display:flex;align-items:flex-start;justify-content:space-between;background:#fff;

  border:1px solid var(--border);border-radius:18px;padding:1.3rem 1rem;box-shadow:0 6px 20px rgba(23,27,52,.05);

  margin:.8rem 0 1.1rem 0;flex-wrap:wrap;gap:.5rem;}

.step{flex:1;min-width:180px;text-align:center;padding:0 .5rem;}

.circle{width:50px;height:50px;border-radius:50%;margin:0 auto .6rem auto;display:flex;align-items:center;

  justify-content:center;font-weight:800;font-size:1.15rem;background:var(--subtle);color:var(--accent);

  border:2px solid #DADDFB;transition:all .3s ease;}

.s-active .circle{background:var(--accent);color:#fff;border-color:var(--accent);box-shadow:0 0 0 6px rgba(99,91,255,.18);}

.s-done .circle{background:#10B981;color:#fff;border-color:#10B981;}

.s-fail .circle{background:#EF4444;color:#fff;border-color:#EF4444;}

.step-title{font-weight:700;color:var(--head);}

.step-desc{color:var(--sec);font-size:.88rem;}

.step-status{margin-top:.45rem;font-size:.78rem;font-weight:700;color:var(--sec);}

.s-active .step-status{color:var(--accent);} .s-done .step-status{color:#059669;} .s-fail .step-status{color:#DC2626;}

.line{flex:0 0 60px;height:2px;background:#DADDFB;margin-top:25px;} .line.done{background:#10B981;}

.counter{display:inline-block;background:var(--subtle);color:var(--accent);font-weight:700;border-radius:999px;

  padding:.25rem .9rem;font-size:.85rem;margin:.6rem 0 .2rem 0;border:1px solid #DADDFB;}



/* question / answer / sources */

.q-box{background:var(--subtle);border:1px solid #DADDFB;border-radius:12px;padding:.75rem 1rem;margin:1.2rem 0 .7rem 0;}

.q-label{font-size:.72rem;font-weight:800;letter-spacing:.08em;color:var(--accent);text-transform:uppercase;}

.q-text{color:var(--head);font-weight:600;font-size:1.05rem;margin-top:.15rem;word-break:break-word;}

.sec-head{display:flex;align-items:center;gap:10px;margin:.1rem 0 .6rem 0;

  padding-bottom:.55rem;border-bottom:1px solid var(--border);}

.sec-title{font-size:1.25rem;font-weight:800;color:var(--head);}

.ico{width:34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex:0 0 auto;}

.ico-ans{background:var(--accent);}

.ico-src{background:var(--subtle);border:1px solid #DADDFB;}

.count-chip{margin-left:auto;font-size:.75rem;font-weight:700;color:var(--sec);background:#fff;

  border:1px solid var(--border);border-radius:999px;padding:.15rem .65rem;}

.src{background:#fff;border:1px solid var(--border);border-left:4px solid var(--accent);border-radius:12px;

  padding:.85rem 1rem;margin-bottom:.7rem;}

.src-top{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;margin-bottom:.45rem;}

.src-file{font-weight:700;color:var(--head);word-break:break-all;}

.src-page{font-size:.78rem;font-weight:700;color:var(--accent);background:var(--subtle);border-radius:999px;padding:.1rem .6rem;}

.src-score{font-size:.74rem;color:var(--sec);margin-left:auto;}

.src-text{color:var(--head);font-size:.96rem;line-height:1.7;white-space:pre-wrap;word-break:break-word;

  background:#FAFBFF;border-radius:8px;padding:.6rem .8rem;border:1px solid var(--border);}

.no-src{color:var(--head);background:#FFF7E6;border:1px solid #FBD38D;border-radius:10px;padding:.8rem 1rem;}



@media (max-width:760px){

  .hero h1{font-size:2rem;} .line{display:none;} .step{min-width:100%;margin-bottom:.8rem;}

  div[data-testid="stRadio"] div[role="radiogroup"]{justify-content:flex-start;}

  div[data-testid="stRadio"] label[data-baseweb="radio"]{padding:.4rem .6rem;}

}

</style>

""", unsafe_allow_html=True)





# ----------------------------------------------------------------------------- backend

@st.cache_resource(show_spinner="Loading models (first run downloads them, please wait)...")

def get_engine():

    return PDFQAEngine()





def fmt_size(n):

    if n < 1024:

        return f"{n} B"

    if n < 1024 * 1024:

        return f"{n / 1024:.1f} KB"

    return f"{n / (1024 * 1024):.2f} MB"





def chunk_text(c):

    return (c.get("text", "") if isinstance(c, dict) else str(c)) or ""





def process_pdf(engine, name, data):

    """Really run the pipeline for one file. Returns a status dict."""

    info = {"name": name, "size": len(data), "status": "failed", "error": "", "path": None,

            "chunks": None, "index": None}

    if len(data) == 0:

        info["error"] = "The file is empty."

        return info

    if len(data) > MAX_MB * 1024 * 1024:

        info["error"] = f"File exceeds the {MAX_MB} MB limit."

        return info

    if not data[:1024].lstrip().startswith(b"%PDF"):

        info["error"] = "This does not look like a valid PDF file."

        return info

    digest = hashlib.md5(data).hexdigest()

    path = os.path.join(tempfile.gettempdir(), f"pdfqa_{digest}.pdf")

    if not os.path.exists(path):

        with open(path, "wb") as f:

            f.write(data)

    info["path"] = path

    try:

        chunks, index = engine.load_pdf(path)

    except Exception as e:

        info["error"] = f"Processing error: {e}"

        return info

    if not chunks or not any(chunk_text(c).strip() for c in chunks):

        info["error"] = ("No extractable text found. This looks like a scanned/image-only PDF "

                         "(OCR is not supported).")

        return info

    info.update(status="ready", chunks=chunks, index=index)

    return info





def ensure_state():

    ss = st.session_state

    ss.setdefault("page", "Home")

    ss.setdefault("files", {})         # digest -> {name, size, data}

    ss.setdefault("docs", {})          # digest -> processing result

    ss.setdefault("messages", [])      # [{q, a, sources}]

    ss.setdefault("ready_sig", ())

    ss.setdefault("uploader_key", 0)

    ss.setdefault("notice", None)

    ss.setdefault("feedback_status", None)





def go(page):

    st.session_state.page = page





def remove_file(digest):

    st.session_state.files.pop(digest, None)

    st.session_state.docs.pop(digest, None)





def clear_chat():

    st.session_state.messages = []





def answer_question(engine, question, ready):

    """Retrieve across all ready PDFs and generate a grounded answer."""

    sources = []

    for d in ready:

        for s in engine.retrieve(question, d["chunks"], d["index"]) or []:

            s = dict(s)

            s["file"] = d["name"]

            sources.append(s)

    if sources and all(s.get("score") is not None for s in sources):

        sources.sort(key=lambda s: s["score"], reverse=True)

    if len(ready) > 1:

        sources = sources[:TOP_K_TOTAL]

    if not sources:

        return ("I could not find relevant content in the uploaded documents to answer this question.", [])



    if len(ready) == 1:

        answer, _ = engine.ask(ready[0]["path"], question)

        return answer, sources

    if hasattr(engine, "generate"):

        return engine.generate(question, sources), sources

    parts = []

    for d in ready:

        ans, _ = engine.ask(d["path"], question)

        parts.append(f"**{d['name']}**\n\n{ans}")

    return "\n\n---\n\n".join(parts), sources





# ----------------------------------------------------------------------------- UI pieces

LOGO_SVG = ('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" '

            'stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12'

            'a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><circle cx="11" cy="14" r="2.5"/><path d="m13 16 2.5 2.5"/></svg>')

ICON_ANSWER = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" '

               'stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1'

               'L5 10l5.1-1.9z"/><path d="M19 17v4M17 19h4"/></svg>')

ICON_SOURCES = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#635BFF" stroke-width="2" '

                'stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h6"/>'

                '<path d="M14 2v6h6"/><circle cx="17" cy="17" r="3"/><path d="m21 21-1.9-1.9"/></svg>')





def render_header():
    """Render the persistent, native Streamlit left-sidebar navigation."""
    nav_items = [
        ("Home", "⌂"),
        ("How It Works", "▤"),
        ("Features", "✦"),
        ("Feedback", "✉"),
    ]

    with st.sidebar:
        st.markdown(
            f"""
            <div class="brand">
                <div class="brand-logo">{LOGO_SVG}</div>
                <div>
                    <div class="brand-name">QPDF</div>
                    <div class="brand-sub">The Queryable PDF Assistant</div>
                </div>
            </div>
            <div class="nav-section-label">Workspace</div>
            """,
            unsafe_allow_html=True,
        )

        for nav_page, nav_icon in nav_items:
            slug = nav_page.lower().replace(" ", "_")
            active = st.session_state.page == nav_page
            container_key = f"nav_active_{slug}" if active else f"nav_item_{slug}"
            with st.container(key=container_key):
                st.button(
                    f"{nav_icon}   {nav_page}",
                    key=f"nav_{slug}",
                    type="secondary",
                    use_container_width=True,
                    on_click=go,
                    args=(nav_page,),
                )

        st.markdown(
            '<div class="sidebar-footer">AI-powered document search<br>Ask questions. Find answers.</div>',
            unsafe_allow_html=True,
        )



def stepper_html(n_files, state, n_ready):

    """state: upload | processing | ready | failed"""

    if state == "upload":

        s = [("s-active", "Upload required"), ("", "Waiting for a document"), ("", "Not ready")]

        lines = ["", ""]

    elif state == "processing":

        s = [("s-done", f"{n_files} file(s) uploaded"), ("s-active", "AI processing..."), ("", "Not ready")]

        lines = ["done", ""]

    elif state == "failed":

        s = [("s-done", f"{n_files} file(s) uploaded"), ("s-fail", "Processing failed"), ("", "Not ready")]

        lines = ["done", ""]

    else:

        s = [("s-done", f"{n_files} file(s) uploaded"), ("s-done", f"{n_ready} processed"),

             ("s-active", "Ready to ask questions")]

        lines = ["done", "done"]

    marks = ["✓" if s[0][0] == "s-done" else "1",

             "✓" if s[1][0] == "s-done" else ("!" if s[1][0] == "s-fail" else "2"),

             "3"]

    titles = [("Upload Your PDF", "Drag & drop or browse your files"),

              ("AI Processing", "We analyze your document content"),

              ("Ask Questions", "Get instant, accurate answers")]

    out = '<div class="stepper">'

    for i in range(3):

        out += (f'<div class="step {s[i][0]}"><div class="circle">{marks[i]}</div>'

                f'<div class="step-title">{titles[i][0]}</div><div class="step-desc">{titles[i][1]}</div>'

                f'<div class="step-status">{s[i][1]}</div></div>')

        if i < 2:

            out += f'<div class="line {lines[i]}"></div>'

    return out + "</div>"





def file_card_html(f):

    name = html.escape(f["name"])

    if f["status"] == "ready":

        badge, extra = '<span class="badge b-ready">Ready</span>', ""

    elif f["status"] == "failed":

        badge = '<span class="badge b-fail">Failed</span>'

        extra = f'<div class="file-meta" style="color:#B91C1C">{html.escape(f["error"])}</div>'

    else:

        badge, extra = '<span class="badge b-proc">Processing</span>', ""

    return (f'<div class="file"><div><div class="file-name">📄 {name}</div>'

            f'<div class="file-meta">{fmt_size(f["size"])}</div>{extra}</div>{badge}</div>')





def copy_button(text):

    """Real clipboard copy via a tiny HTML component; reports honestly if the browser blocks it."""

    payload = json.dumps(text).replace("</", "<\\\\/")

    components.html(f"""

    <button id="b" style="font:600 14px Inter,Arial,sans-serif;color:#171B34;background:#fff;

      border:1px solid #E3E7F2;border-radius:10px;padding:8px 16px;cursor:pointer;">📋 Copy Answer</button>

    <script>

      const text = {payload};

      const b = document.getElementById('b');

      function fallback(){{

        const t = document.createElement('textarea'); t.value = text; document.body.appendChild(t);

        t.select(); let ok = false; try {{ ok = document.execCommand('copy'); }} catch(e) {{}}

        document.body.removeChild(t); return ok;

      }}

      b.onmouseover = () => b.style.borderColor = '#635BFF';

      b.onmouseout = () => b.style.borderColor = '#E3E7F2';

      b.onclick = async () => {{

        let ok = false;

        try {{ await navigator.clipboard.writeText(text); ok = true; }} catch(e) {{ ok = fallback(); }}

        b.textContent = ok ? '✓ Copied' : 'Copy failed - select the text manually';

        setTimeout(() => b.textContent = '📋 Copy Answer', 2200);

      }};

    </script>""", height=48)





def sources_html(sources):

    if not sources:

        return ('<div class="no-src">No relevant source was found in your documents for this question, '

                'so no excerpt can be shown.</div>')

    out = ""

    for s in sources:

        fname = html.escape(str(s.get("file") or "document"))

        page = (f'<span class="src-page">Page {html.escape(str(s["page"]))}</span>'

                if s.get("page") is not None else "")

        score = ""

        if isinstance(s.get("score"), (int, float)):

            score = f'<span class="src-score">similarity {s["score"]:.3f}</span>'

        text = (s.get("text") or "").strip()

        if len(text) > EXCERPT_CHARS:

            text = text[:EXCERPT_CHARS].rstrip() + "…"

        out += (f'<div class="src"><div class="src-top"><span class="src-file">📄 {fname}</span>{page}{score}</div>'

                f'<div class="src-text">{html.escape(text) if text else "(no text excerpt available)"}</div></div>')

    return out





def render_message(m):

    st.markdown(f'<div class="q-box"><div class="q-label">Your question</div>'

                f'<div class="q-text">{html.escape(m["q"])}</div></div>', unsafe_allow_html=True)



    with st.container(border=True):

        st.markdown(f'<div class="sec-head"><div class="ico ico-ans">{ICON_ANSWER}</div>'

                    f'<div class="sec-title">AI Answer</div></div>', unsafe_allow_html=True)

        st.markdown(m["a"])

        copy_button(m["a"])



    with st.container(border=True):

        n = len(m["sources"])

        st.markdown(f'<div class="sec-head"><div class="ico ico-src">{ICON_SOURCES}</div>'

                    f'<div class="sec-title">Retrieved Sources</div>'

                    f'<span class="count-chip">{n} excerpt{"s" if n != 1 else ""}</span></div>',

                    unsafe_allow_html=True)

        st.markdown(sources_html(m["sources"]), unsafe_allow_html=True)





# ----------------------------------------------------------------------------- pages

def render_home(engine):

    ss = st.session_state

    st.markdown('<div class="hero"><h1>Your Documents. <span>Your Answers.</span></h1>'

                '<p>Upload your PDFs and get instant, accurate answers grounded in your documents.</p></div>',

                unsafe_allow_html=True)



    # --- intake: the uploader only receives files; our own list below is the source of truth

    uploaded = st.file_uploader("Upload PDF documents", type=["pdf"], accept_multiple_files=True,

                                key=f"uploader_{ss.uploader_key}", label_visibility="collapsed")

    st.caption(f"PDF files only · up to {MAX_MB} MB each · you can add several files at once")

    if uploaded:

        for uf in uploaded:

            data = uf.getvalue()

            digest = hashlib.md5(data).hexdigest()

            if digest in ss.files:

                ss.notice = f"“{uf.name}” is already in your list (identical content), so it was not added again."

            else:

                ss.files[digest] = {"name": uf.name, "size": len(data), "data": data}

        ss.uploader_key += 1

        st.rerun()

    if ss.notice:

        st.warning(ss.notice)

        ss.notice = None



    n_files = len(ss.files)

    st.markdown(f'<span class="counter">Uploaded PDFs: {n_files}</span>', unsafe_allow_html=True)

    stepper_slot = st.empty()



    # --- real processing, only for files not processed yet

    pending = [d for d in ss.files if d not in ss.docs]

    if n_files == 0:

        stepper_slot.markdown(stepper_html(0, "upload", 0), unsafe_allow_html=True)

    elif pending:

        stepper_slot.markdown(stepper_html(n_files, "processing", 0), unsafe_allow_html=True)

        with st.spinner("Extracting text, chunking and indexing your PDFs..."):

            for d in pending:

                f = ss.files[d]

                ss.docs[d] = process_pdf(engine, f["name"], f["data"])

                f["data"] = None   # bytes are on disk now; free memory



    infos = []

    for d, f in ss.files.items():

        info = dict(ss.docs.get(d) or {"status": "processing", "error": "", "path": None})

        info["name"], info["size"] = f["name"], f["size"]

        info["digest"] = d

        infos.append(info)

    ready = [i for i in infos if i["status"] == "ready"]



    if n_files:

        stepper_slot.markdown(stepper_html(n_files, "ready" if ready else "failed", len(ready)),

                              unsafe_allow_html=True)

        for info in infos:

            c1, c2 = st.columns([6, 1.4], vertical_alignment="center")

            with c1:

                st.markdown(file_card_html(info), unsafe_allow_html=True)

            with c2:

                st.button("Remove PDF", key=f"rm_{info['digest']}", on_click=remove_file,

                          args=(info["digest"],))



    # reset chat whenever the set of ready documents changes (answers must match the documents)

    sig = tuple(sorted(i["path"] for i in ready))

    if sig != ss.ready_sig:

        ss.messages = []

        ss.ready_sig = sig



    st.write("")

    if not ready:

        st.info("Upload and successfully process at least one PDF to enable question answering.")

        return



    with st.container(border=True):

        st.markdown("#### Ask a question")

        with st.form("ask_form", clear_on_submit=True, border=False):

            question = st.text_input("Your question", placeholder="Ask a question about your PDFs...",

                                     label_visibility="collapsed")

            asked = st.form_submit_button("Ask Question", type="primary")



    if asked:

        q = (question or "").strip()

        if not q:

            st.warning("Please type a question first.")

        else:

            with st.spinner("Searching your PDFs and generating the answer..."):

                try:

                    ans, srcs = answer_question(engine, q, ready)

                    ss.messages.append({"q": q, "a": ans, "sources": srcs})

                except Exception as e:

                    st.error(f"Could not generate an answer: {e}")



    if ss.messages:

        st.button("Clear Chat", key="clear_chat", on_click=clear_chat)

        for m in reversed(ss.messages):

            render_message(m)





def render_how():

    st.markdown("## How It Works")

    st.markdown(f"""

<div class="card"><h4>1 · Upload Your PDF</h4><p class="muted">Add one or more PDF files (max {MAX_MB} MB each).

Text is extracted page by page.</p></div>

<div class="card"><h4>2 · AI Processing</h4><p class="muted">The text is split into overlapping chunks,

embedded into vectors and stored in a searchable index.</p></div>

<div class="card"><h4>3 · Ask Questions</h4><p class="muted">Your question retrieves the most relevant chunks,

and the language model ({html.escape(str(LLM_NAME))}) answers using that content, citing file and page.</p></div>

""", unsafe_allow_html=True)

    st.warning("Scanned (image-only) PDFs are not supported because OCR is not implemented.")

    st.button("Go to Home", on_click=go, args=("Home",), type="primary")





def render_features():

    st.markdown("## Features")

    feats = [("📚", "Multiple PDFs", "Search several documents together."),

             ("🎯", "Grounded answers", "Answers are based on retrieved document content."),

             ("🔖", "Source citations", "See the file, page and excerpt behind each answer."),

             ("⚡", "Smart caching", "Models load once; unchanged files are never reprocessed."),

             ("🛡️", "Honest handling", "Unreadable PDFs and unrelated questions are reported clearly."),

             ("🧠", f"Model: {html.escape(str(LLM_NAME))}", "Uses your existing RAG pipeline.")]

    cols = st.columns(3)

    for i, (ic, t, d) in enumerate(feats):

        with cols[i % 3]:

            st.markdown(f'<div class="card"><div style="font-size:1.6rem">{ic}</div><h4>{t}</h4>'

                        f'<p class="muted">{d}</p></div>', unsafe_allow_html=True)





def render_feedback():

    st.markdown("## Feedback")

    # key="feedback_wrap" -> CSS class .st-key-feedback_wrap scopes the dark input theme to this page only

    with st.container(key="feedback_wrap"):

        with st.form("feedback_form", clear_on_submit=True):

            name = st.text_input("Name (optional)", placeholder="Your name")

            category = st.selectbox("Category", ["General", "Bug report", "Feature request", "UI/UX", "Other"])

            rating = st.slider("Your experience", 1, 5, 4)

            message = st.text_area("Your feedback", placeholder="Tell us what you think...")

            sent = st.form_submit_button("Submit Feedback", type="primary")

    if sent:

        if not message.strip():

            st.session_state.feedback_status = ("error", "Please write a feedback message before submitting.")

        else:

            entry = {"timestamp": datetime.now().isoformat(timespec="seconds"), "name": name.strip(),

                     "category": category, "rating": rating, "message": message.strip()}

            try:

                data = []

                if os.path.exists(FEEDBACK_FILE):

                    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:

                        data = json.load(f)

                data.append(entry)

                with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:

                    json.dump(data, f, indent=2, ensure_ascii=False)

                st.session_state.feedback_status = ("success", f"Saved locally to {FEEDBACK_FILE}. Thank you!")

            except Exception as e:

                st.session_state.feedback_status = ("error", f"Your feedback could not be saved: {e}")

    status = st.session_state.feedback_status

    if status:

        (st.success if status[0] == "success" else st.error)(status[1])





# ----------------------------------------------------------------------------- main

ensure_state()

engine = get_engine()

render_header()



page = st.session_state.page

if page == "Home":

    render_home(engine)

elif page == "How It Works":

    render_how()

elif page == "Features":

    render_features()

else:

    render_feedback()