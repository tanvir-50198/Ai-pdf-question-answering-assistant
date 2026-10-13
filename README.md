# AI-Powered PDF Question Answering Assistant

Free, local RAG app: PyMuPDF -> chunking -> MiniLM embeddings -> FAISS -> Qwen2.5-Instruct -> Streamlit.

## Setup (VS Code)

1. Install Python 3.10-3.12 and open this folder in VS Code (`File > Open Folder`).
2. Open the terminal (`Ctrl + ~`) and create a virtual environment:

   Windows:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
   Mac/Linux:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Select the interpreter: `Ctrl+Shift+P` -> "Python: Select Interpreter" -> pick `.venv`.
5. Run:
   ```
   streamlit run app.py
   ```
6. It opens at http://localhost:8501.

First run downloads the models (~3.5 GB with Qwen2.5-1.5B), so it takes a while. After that it works offline.
CPU answers take roughly 10-40 seconds; a GPU is much faster.

## Notes
- Only text-based PDFs work (scanned image PDFs need OCR).
- Default LLM is `Qwen/Qwen2.5-1.5B-Instruct` (needs ~7 GB free RAM on CPU). If your PC is slow or low on RAM, use the smaller model:
  - Windows (cmd): `set LLM_NAME=Qwen/Qwen2.5-0.5B-Instruct` then `streamlit run app.py`
  - Windows (PowerShell): `$env:LLM_NAME="Qwen/Qwen2.5-0.5B-Instruct"; streamlit run app.py`
  - Mac/Linux: `LLM_NAME=Qwen/Qwen2.5-0.5B-Instruct streamlit run app.py`
- Retrieval settings (`CHUNK_SIZE`, `OVERLAP`, `TOP_K`) are at the top of `rag.py`.

## Structure
```
app.py            # Streamlit UI
rag.py            # extraction, chunking, FAISS retrieval, answer generation
requirements.txt
```
