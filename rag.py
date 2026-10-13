"""Core RAG logic: PDF -> chunks -> embeddings -> FAISS -> Qwen answer."""
import os

import faiss
import fitz  # PyMuPDF
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer

EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# Default: good quality. If your PC is slow / low on RAM, set the env var
# LLM_NAME=Qwen/Qwen2.5-0.5B-Instruct (see README).
LLM_NAME = os.environ.get("LLM_NAME", "Qwen/Qwen2.5-1.5B-Instruct")

CHUNK_SIZE = 200   # words per chunk
OVERLAP = 40
TOP_K = 4

# Questions like these are usually answered by the abstract / introduction,
# which plain similarity search often misses.
GENERIC_HINTS = (
    "purpose", "aim", "objective", "goal", "main topic", "about",
    "summary", "summarize", "summarise", "abstract", "overview",
    "contribution", "what is this", "what does this",
)


def extract_pdf_text(pdf_path):
    pages = []
    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append({"page": page_number, "text": text})
    return pages


def create_chunks(pages, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    chunks = []
    step = max(1, chunk_size - overlap)
    for item in pages:
        words = item["text"].split()
        for start in range(0, len(words), step):
            chunk_text = " ".join(words[start:start + chunk_size])
            if chunk_text.strip():
                chunks.append({"page": item["page"], "text": chunk_text})
    return chunks


class PDFQAEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("Device:", self.device)

        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer(EMBED_MODEL_NAME, device=self.device)

        print(f"Loading language model: {LLM_NAME} (first run downloads it)...")
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(LLM_NAME)
        if self.device == "cuda":
            self.model = self.model.half()
        self.model = self.model.to(self.device)
        self.model.eval()

        self._cache_key = None
        self._chunks = None
        self._index = None
        print("Models loaded successfully!")

    def _build_index(self, chunks):
        texts = [c["text"] for c in chunks]
        embeddings = self.embedding_model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False,
        )
        embeddings = np.asarray(embeddings, dtype="float32")
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        return index

    def load_pdf(self, pdf_path):
        key = (pdf_path, os.path.getmtime(pdf_path))
        if key == self._cache_key:
            return self._chunks, self._index

        pages = extract_pdf_text(pdf_path)
        if not pages:
            raise ValueError("No readable text found in this PDF (it may be scanned images).")
        chunks = create_chunks(pages)
        if not chunks:
            raise ValueError("No text chunks were created.")
        index = self._build_index(chunks)

        self._cache_key, self._chunks, self._index = key, chunks, index
        return chunks, index

    def retrieve(self, question, chunks, index, top_k=TOP_K):
        query_embedding = self.embedding_model.encode(
            [question], convert_to_numpy=True, normalize_embeddings=True
        ).astype("float32")
        k = min(top_k, len(chunks))
        scores, indices = index.search(query_embedding, k)

        picked = []   # list of (chunk_idx, score)
        seen = set()

        # For "purpose / aim / summary" style questions, always include the
        # beginning of the document (abstract + introduction).
        if any(h in question.lower() for h in GENERIC_HINTS):
            for i in range(min(2, len(chunks))):
                picked.append((i, None))
                seen.add(i)

        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and int(idx) not in seen:
                picked.append((int(idx), float(score)))
                seen.add(int(idx))

        results = []
        for idx, score in picked:
            item = dict(chunks[idx])
            item["score"] = score
            results.append(item)
        return results

    def generate_answer(self, question, relevant_chunks):
        context = "\n\n".join(
            f"[Page {c['page']}]\n{c['text']}" for c in relevant_chunks
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a PDF question-answering assistant. "
                    "Answer using only the supplied PDF context. "
                    "If the answer is not supported by the context, clearly say "
                    "that you could not find it in the PDF. "
                    "Answer in the same language as the user's question. "
                    "Give a clear, complete answer in 2-5 sentences and do not invent facts."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"PDF Context:\n{context}\n\n"
                    f"Question: {question}\n\n"
                    "Answer based on the PDF context."
                ),
            },
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=250,
                do_sample=False,
                repetition_penalty=1.1,
            )
        new_tokens = outputs[0][inputs["input_ids"].shape[-1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    def ask(self, pdf_path, question):
        chunks, index = self.load_pdf(pdf_path)
        relevant = self.retrieve(question, chunks, index)
        if not relevant:
            return "No relevant information found.", ""
        answer = self.generate_answer(question, relevant)
        sources = "\n\n".join(
            f"Page {c['page']}"
            + (f" (similarity: {c['score']:.3f})" if c["score"] is not None else " (document start)")
            + f"\n{c['text'][:500]}..."
            for c in relevant
        )
        return answer, sources
