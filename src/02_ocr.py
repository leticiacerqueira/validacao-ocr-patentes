"""Roda OCR (Tesseract, português) nos PDFs escaneados.
Saídas em saida/ocr/: <id>.txt (texto) e <id>_palavras.csv (palavra + confiança)."""
import csv, io, subprocess
from pathlib import Path
import pymupdf as fitz

RAIZ = Path(__file__).resolve().parent.parent
DOCS, OUT = RAIZ / "documentos", RAIZ / "saida" / "ocr"
OUT.mkdir(parents=True, exist_ok=True)

for pdf in sorted(DOCS.glob("*_escaneado.pdf")):
    doc_id = pdf.name.split("_")[0]
    textos, palavras = [], []
    for n, page in enumerate(fitz.open(pdf), 1):
        png = OUT / f"_{doc_id}_{n}.png"
        page.get_pixmap(dpi=300).save(png)
        txt = subprocess.run(["tesseract", png, "-", "-l", "por", "--psm", "4"],
                             capture_output=True, text=True).stdout
        tsv = subprocess.run(["tesseract", png, "-", "-l", "por", "--psm", "4", "tsv"],
                             capture_output=True, text=True).stdout
        pal = [{"pagina": n, "palavra": r["text"], "confianca": float(r["conf"])}
               for r in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE)
               if r["text"] and r["text"].strip()]
        media = sum(p["confianca"] for p in pal) / max(len(pal), 1)
        confiaveis = sum(p["confianca"] >= 80 for p in pal)
        if confiaveis < 3:  # página só com ruído (ex.: verso em branco escaneado)
            print(f"  {doc_id} pág. {n}: confiança média {media:.0f}, ignorada como página sem conteúdo")
            png.unlink(); continue
        palavras += pal
        textos.append(txt)
        png.unlink()
    (OUT / f"{doc_id}.txt").write_text("\n".join(textos), encoding="utf-8")
    with open(OUT / f"{doc_id}_palavras.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pagina", "palavra", "confianca"]); w.writeheader(); w.writerows(palavras)
    print(doc_id, len(palavras), "palavras")
