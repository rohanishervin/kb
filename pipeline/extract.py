"""Parse notebooks in nodes/ into notes and individual problems."""
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime

NODES_DIR = "nodes"
PROBLEM_RE = re.compile(r"^(#{2,3})\s*Problem\s*(\d+)\s*[:.\-–]?\s*(.*)$", re.M)
LINK_RE = re.compile(r"\]\(([^)\s]*?\.ipynb)(#[^)\s]*)?\)")


@dataclass
class Note:
    id: str            # filename without .ipynb
    file: str
    title: str
    text: str
    date: str          # ISO date (frontmatter date or file mtime)
    links: list = field(default_factory=list)   # note ids this note links to
    is_pset: bool = False
    mtime: float = 0.0  # notebook file modification time (for the edit-settle delay)
    broken: list = field(default_factory=list)  # .ipynb link targets that don't exist

    @property
    def chars(self):
        return len(self.text)

    @property
    def hash(self):
        return hashlib.sha1(self.text.encode("utf-8")).hexdigest()[:12]


@dataclass
class Problem:
    id: str            # "<pset-id>#<number>"
    pset: str
    number: int
    title: str
    text: str          # statement + solution
    date: str
    links: list = field(default_factory=list)
    mtime: float = 0.0  # mtime of the pset notebook

    @property
    def hash(self):
        return hashlib.sha1(self.text.encode("utf-8")).hexdigest()[:12]


def _nb_text(path):
    with open(path, "r", encoding="utf-8") as fh:
        nb = json.load(fh)
    parts = []
    for c in nb.get("cells", []):
        src = c.get("source", "")
        src = "".join(src) if isinstance(src, list) else src
        if c.get("cell_type") == "code":
            src = "```python\n" + src + "\n```"
        parts.append(src)
    text = "\n\n".join(parts)
    # drop inline base64 images and html noise that only wastes LLM context
    text = re.sub(r"data:image/[^)\"']+", "data:image", text)
    return text


def _links(text, valid_ids):
    out = []
    for target, _anchor in LINK_RE.findall(text):
        nid = os.path.basename(target)[:-6]
        if nid in valid_ids and nid not in out:
            out.append(nid)
    return out


def _date(text, path):
    m = re.search(r'^date:\s*"?(\d{4}-\d{2}-\d{2})', text, re.M)
    if m:
        return m.group(1)
    return date.fromtimestamp(os.path.getmtime(path)).isoformat()


TEX = [(r"\\mathbb\{R\}", "ℝ"), (r"\\mathbb\{Q\}", "ℚ"), (r"\\mathbb\{N\}", "ℕ"), (r"\\mathbb\{Z\}", "ℤ"),
       (r"\\mathbb\{C\}", "ℂ"), (r"\\cdot", "·"), (r"\\times", "×"), (r"\\infty", "∞"), (r"\\le(q)?\b", "≤"),
       (r"\\ge(q)?\b", "≥"), (r"\\to\b", "→"), (r"\\sigma", "σ"), (r"\\mu", "μ"), (r"\\lambda", "λ"),
       (r"\\(text|mathrm|mathbf|operatorname)\{([^}]*)\}", r"\2"), (r"\\[a-zA-Z]+", ""), (r"[{}$]", "")]


def plain(s):
    """Readable plain-text version of a heading that may contain LaTeX."""
    for a, b in TEX:
        s = re.sub(a, b, s)
    return re.sub(r"\s+", " ", s).strip()


def _title(text, nid):
    m = re.search(r"^title:\s*\"?(.+?)\"?\s*$", text, re.M) or re.search(r"^#\s+(.+)$", text, re.M)
    if m:
        t = plain(re.sub(r"^\s*(\d+\.|[IVX]+\.)\s+", "", m.group(1)))
        if t:
            return t
    return nid.replace("-", " ").title()


def load(nodes_dir=NODES_DIR):
    files = sorted(f for f in os.listdir(nodes_dir) if f.endswith(".ipynb"))
    ids = {f[:-6] for f in files}
    notes, problems = {}, {}
    for f in files:
        path = os.path.join(nodes_dir, f)
        try:
            text = _nb_text(path)
        except Exception as e:  # half-written notebook during autosave etc.
            print(f"[extract] skip {f}: {e}")
            continue
        nid = f[:-6]
        n = Note(nid, f, _title(text, nid), text, _date(text, path),
                 [l for l in _links(text, ids) if l != nid], nid.startswith("pset-"), os.path.getmtime(path))
        n.broken = sorted({os.path.basename(t) for t, _a in LINK_RE.findall(text)} - {x + ".ipynb" for x in ids})
        notes[nid] = n
        if n.is_pset:
            heads = list(PROBLEM_RE.finditer(text))
            for i, m in enumerate(heads):
                end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
                body = text[m.start():end].strip()
                num = int(m.group(2))
                pid = f"{nid}#{num}"
                if pid in problems:  # duplicate numbering: keep unique
                    pid = f"{nid}#{num}-{i + 1}"
                problems[pid] = Problem(pid, nid, num, plain(m.group(3)) or f"Problem {num}",
                                        body, n.date, [l for l in _links(body, ids) if l != nid], n.mtime)
    return notes, problems


def today():
    return datetime.now().date()
