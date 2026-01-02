import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Protocol

from subjective_abstract_data_source_package import SubjectiveDataSource
from brainboost_data_source_logger_package.BBLogger import BBLogger

TEXT_EXTS = {
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".js",
    ".ts",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".html",
    ".css",
    ".md",
    ".txt",
    ".ini",
    ".cfg",
    ".toml",
    ".csv",
}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}
PDF_EXTS = {".pdf"}
DOCX_EXTS = {".docx"}
SPREADSHEET_EXTS = {".xlsx", ".xls", ".csv"}
OCR_IMAGE_MAX_SIDE = int(os.environ.get("CONTEXT_OCR_MAX_SIDE", "1600"))
OCR_PDF_SCALE = float(os.environ.get("CONTEXT_OCR_PDF_SCALE", "1.0"))
IGNORE_DIRS = {
    ".git",
    ".snapshots",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    ".idea",
    ".vscode",
}
MAX_TEXT_BYTES = 200_000

class SubjectiveLocalFolderDataSource(SubjectiveDataSource):

    def __init__(self, params=None, name=None, **kwargs):
        super().__init__(params=params, name=name, **kwargs)
        params = params or {}
        self.time_interval = params.get("time_interval")

    def fetch(self):
        log_path = None
        if isinstance(self.params, dict):
            log_path = self.params.get("log_path")
        _prime_bbconfig(log_path=log_path)
        _safe_log("Starting local folder context extraction.")

        start_path = None
        if isinstance(self.params, dict):
            start_path = self.params.get("path")
        if not start_path:
            raise ValueError("Missing required param: path")

        use_gpu = None
        if isinstance(self.params, dict) and "gpu" in self.params:
            use_gpu = bool(self.params.get("gpu"))

        context = _collect_context(start_path, progress=self, use_gpu=use_gpu)
        return context

    # ------------------ New Methods ------------------
    def get_icon(self):
        """Return SVG icon content, preferring a local icon.svg in the plugin folder."""
        import os
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        try:
            if os.path.exists(icon_path):
                with open(icon_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception:
            pass
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24" rx="4" fill="#f59e0b"/><path fill="#fff" d="M6 7h12v2H6zm0 4h12v2H6zm0 4h8v2H6z"/></svg>'

    def get_connection_data(self):
        """
        Return the connection type and required fields for KnowledgeHooks real-time data.
        """
        return {
            "connection_type": "LocalFolder",
            "fields": ["path", "time_interval"]
        }


def _safe_stat(path: str) -> Dict[str, object]:
    st = os.stat(path)
    return {
        "size": st.st_size,
        "mtime_iso": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
    }


def _file_hash(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _looks_binary(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(2048)
        return b"\x00" in chunk
    except Exception:
        return True


def _read_text_file(path: str) -> Optional[str]:
    if _looks_binary(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(MAX_TEXT_BYTES)
    except Exception:
        return None


_EASYOCR_READER: Dict[bool, object] = {}


def _get_easyocr_reader(use_gpu: Optional[bool]):
    import easyocr
    import torch

    use_gpu = torch.cuda.is_available() if use_gpu is None else use_gpu
    if use_gpu not in _EASYOCR_READER:
        _EASYOCR_READER[use_gpu] = easyocr.Reader(["en"], gpu=use_gpu)
    return _EASYOCR_READER[use_gpu]


def _ocr_image(image_path: str, use_gpu: Optional[bool]) -> Optional[str]:
    try:
        import numpy as np
        from PIL import Image

        reader = _get_easyocr_reader(use_gpu)
        img = Image.open(image_path)
        max_side = max(img.size)
        if OCR_IMAGE_MAX_SIDE > 0 and max_side > OCR_IMAGE_MAX_SIDE:
            scale = OCR_IMAGE_MAX_SIDE / max_side
            new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
            img = img.resize(new_size, Image.LANCZOS)
        results = reader.readtext(np.array(img), detail=0)
        return "\n".join(r for r in results if r).strip()
    except Exception:
        return None


def _extract_pdf_text(pdf_path: str) -> Optional[str]:
    try:
        import fitz

        texts = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                page_text = page.get_text("text")
                if page_text:
                    texts.append(page_text)
        merged = "\n\n".join(t for t in texts if t).strip()
        return merged if merged else None
    except Exception:
        return None


def _extract_docx_text(docx_path: str) -> Optional[str]:
    try:
        import docx

        doc = docx.Document(docx_path)
        parts = [p.text for p in doc.paragraphs if p.text]
        merged = "\n".join(parts).strip()
        return merged if merged else None
    except Exception:
        return None


def _extract_spreadsheet_text(path: str) -> Optional[str]:
    try:
        import pandas as pd

        ext = Path(path).suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(path)
        elif ext == ".xlsx":
            df = pd.read_excel(path, engine="openpyxl")
        elif ext == ".xls":
            df = pd.read_excel(path, engine="xlrd")
        else:
            return None
        text = df.to_csv(index=False)
        return text.strip() if text else None
    except Exception:
        return None


class _ProgressSink(Protocol):
    def set_total_items(self, total: int) -> None:
        ...

    def set_total_processing_time(self, elapsed: float) -> None:
        ...

    def set_processed_items(self, processed_items: int) -> None:
        ...

    def set_fetch_completed(self, completed: bool) -> None:
        ...


def _collect_context(
    start_path: str,
    progress: Optional[_ProgressSink] = None,
    use_gpu: Optional[bool] = None,
) -> Dict[str, object]:
    root = Path(start_path).expanduser().resolve()
    entries: List[Dict[str, object]] = []
    counts = {"files": 0, "dirs": 0, "bytes": 0, "text_files": 0}
    if not root.exists():
        raise FileNotFoundError(f"Start path does not exist: {root}")

    all_items: List[Tuple[str, str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        rel_dir = os.path.relpath(dirpath, root)
        all_items.append(("dir", dirpath, rel_dir))
        for filename in filenames:
            fpath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(fpath, root)
            all_items.append(("file", fpath, rel_path))

    if progress is not None:
        progress.set_total_items(len(all_items))

    start = time.time()
    processed = 0
    for kind, fpath, rel_path in all_items:
        if kind == "dir":
            entries.append({"path": rel_path if rel_path != "." else ".", "type": "dir"})
            counts["dirs"] += 1
        else:
            ext = Path(fpath).suffix.lower()
            meta = _safe_stat(fpath)
            entry = {
                "path": rel_path,
                "type": "file",
                "ext": ext,
                "sha1": _file_hash(fpath),
                **meta,
            }
            counts["files"] += 1
            counts["bytes"] += meta["size"]
            content = _read_text_file(fpath)
            if content is not None:
                entry["content"] = content
                counts["text_files"] += 1
            else:
                if ext in IMAGE_EXTS:
                    ocr_text = _ocr_image(fpath, use_gpu)
                    if ocr_text:
                        entry["content"] = ocr_text
                        entry["content_note"] = "ocr_image"
                    else:
                        entry["content_note"] = "unreadable_or_ocr_failed"
                elif ext in PDF_EXTS:
                    pdf_text = _extract_pdf_text(fpath)
                    if pdf_text:
                        entry["content"] = pdf_text
                        entry["content_note"] = "pdf_text"
                    else:
                        entry["content_note"] = "unreadable_or_empty_pdf_text"
                elif ext in DOCX_EXTS:
                    docx_text = _extract_docx_text(fpath)
                    if docx_text:
                        entry["content"] = docx_text
                        entry["content_note"] = "docx_text"
                    else:
                        entry["content_note"] = "unreadable_or_empty_docx_text"
                elif ext in SPREADSHEET_EXTS:
                    sheet_text = _extract_spreadsheet_text(fpath)
                    if sheet_text:
                        entry["content"] = sheet_text
                        entry["content_note"] = "spreadsheet_text"
                    else:
                        entry["content_note"] = "unreadable_or_empty_spreadsheet_text"
                else:
                    entry["content_note"] = "unreadable_or_binary"
            entries.append(entry)
        if progress is not None:
            processed += 1
            progress.set_total_processing_time(time.time() - start)
            progress.set_processed_items(processed)

    if progress is not None:
        progress.set_fetch_completed(True)

    return {
        "root_path": str(root),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "counts": counts,
        "entries": entries,
    }


def _safe_log(message: str) -> None:
    try:
        BBLogger.log(message)
    except Exception:
        print(message, flush=True)


def _prime_bbconfig(log_path: Optional[str] = None) -> None:
    try:
        from brainboost_configuration_package.BBConfig import BBConfig

        resolved_log_path = log_path or "."
        os.makedirs(resolved_log_path, exist_ok=True)
        if not getattr(BBConfig, "_conf", None):
            BBConfig._conf = {
                "log_debug_mode": "False",
                "log_path": resolved_log_path,
                "log_prefix": "log",
            }
            BBConfig._resolved_conf = {}
        else:
            BBConfig._conf["log_path"] = resolved_log_path
            BBConfig._conf["log_prefix"] = "log"
    except Exception:
        pass

