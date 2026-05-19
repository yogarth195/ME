"""
Fine-tune SBERT on ExplainHire resume-JD pairs.

Uses labeled rows from friends_rows.csv (label=1 or label=0).
Trains with CosineSimilarityLoss — pairs with label=1 get similarity=1.0,
pairs with label=0 get similarity=0.0.

The fine-tuned model is saved to models/sbert_finetuned/
and the semantic_matcher.py is updated to load it automatically.

Run:
    python pipeline/l4_match/finetune_sbert.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
import fitz  # PyMuPDF

FRIENDS_DIR  = Path("data/raw/friends")
JDS_DIR      = Path("data/raw/jds")
PAIRS_CSV    = Path("data/friends_rows.csv")
OUTPUT_DIR   = Path("models/sbert_finetuned")
BASE_MODEL   = "all-MiniLM-L6-v2"

# Map resume_id → PDF filename
def _build_resume_map() -> dict[str, Path]:
    mapping = {}
    for pdf in FRIENDS_DIR.glob("*.pdf"):
        # resume_id is like "friend_abdul_ahad" — built from filename
        key = "friend_" + pdf.stem.lower().replace(" ", "_")
        mapping[key] = pdf
    return mapping


def _extract_pdf_text(path: Path) -> str:
    try:
        doc  = fitz.open(str(path))
        text = " ".join(page.get_text() for page in doc)
        doc.close()
        return text[:3000]  # cap at 3000 chars — SBERT token limit
    except Exception:
        return ""


def _load_jd_text(jd_id: str) -> str:
    path = JDS_DIR / f"{jd_id}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")[:3000]
    return ""


def load_training_pairs() -> list[InputExample]:
    df = pd.read_csv(PAIRS_CSV)
    labeled = df[df["label"].isin([0, 1])].reset_index(drop=True)
    print(f"Labeled pairs: {len(labeled)}  (1={len(labeled[labeled.label==1])}, 0={len(labeled[labeled.label==0])})")

    resume_map = _build_resume_map()
    examples   = []
    skipped    = 0

    for _, row in labeled.iterrows():
        resume_text = ""
        pdf_path    = resume_map.get(row["resume_id"])
        if pdf_path:
            resume_text = _extract_pdf_text(pdf_path)

        jd_text = _load_jd_text(row["jd_id"])

        if not resume_text.strip() or not jd_text.strip():
            skipped += 1
            continue

        # CosineSimilarityLoss expects float label: 1.0 = similar, 0.0 = dissimilar
        examples.append(InputExample(
            texts=[resume_text, jd_text],
            label=float(row["label"]),
        ))

    print(f"Training examples built: {len(examples)}  (skipped {skipped} — missing text)")
    return examples


def finetune():
    print(f"Loading base model: {BASE_MODEL}")
    model = SentenceTransformer(BASE_MODEL)

    print("Loading training pairs...")
    examples = load_training_pairs()

    if len(examples) < 50:
        print("ERROR: Need at least 50 labeled pairs. Label more rows in friends_rows.csv.")
        sys.exit(1)

    train_dataloader = DataLoader(examples, shuffle=True, batch_size=16)
    train_loss       = losses.CosineSimilarityLoss(model)

    warmup_steps = int(len(train_dataloader) * 0.1)
    epochs       = 4

    print(f"\nFine-tuning for {epochs} epochs on {len(examples)} pairs...")
    print(f"Batch size: 16 | Warmup steps: {warmup_steps}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        output_path=str(OUTPUT_DIR),
        show_progress_bar=True,
    )

    print(f"\nFine-tuned model saved to: {OUTPUT_DIR}")
    print("Next step: run python pipeline/l4_match/update_semantic_matcher.py")
    print("           to switch the pipeline to the fine-tuned model.")


if __name__ == "__main__":
    finetune()
