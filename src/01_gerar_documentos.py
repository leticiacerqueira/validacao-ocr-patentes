"""Gera PDFs de patentes de exemplo (textos fictícios, escritos para este projeto)
e versões "digitalizadas" com ruído, para simular documentos escaneados.

Saídas em documentos/:
  <id>_original.pdf      PDF com texto digital (gabarito)
  <id>_gabarito.txt      texto de referência, seção por seção
  <id>_escaneado.pdf     mesmo documento como imagem degradada (entrada do OCR)
"""
import json, random
from pathlib import Path
import pymupdf as fitz
from PIL import Image, ImageFilter
import numpy as np

random.seed(7); np.random.seed(7)
OUT = Path(__file__).resolve().parent.parent / "documentos"
OUT.mkdir(exist_ok=True)

DOCS = json.loads((Path(__file__).parent / "patentes_exemplo.json").read_text(encoding="utf-8"))

def desenhar_figura(page, rect, n):
    """Figura esquemática simples: um furo de sondagem com intervalos."""
    page.draw_rect(rect, color=(0, 0, 0), width=0.8)
    x = rect.x0 + rect.width / 2
    page.draw_line((x, rect.y0 + 10), (x, rect.y1 - 10), color=(0, 0, 0), width=2)
    for i in range(1, 5):
        y = rect.y0 + i * rect.height / 5
        page.draw_line((x - 25, y), (x + 25, y), color=(0, 0, 0), width=0.8)
        page.insert_text((x + 30, y + 4), f"{10 + i}", fontsize=8)

def gerar_pdf(doc, caminho):
    pdf = fitz.open()
    page = pdf.new_page(width=595, height=842)
    y = 60
    def bloco(texto, size=11, bold=False, gap=8):
        nonlocal y, page
        if y > 700:
            page = pdf.new_page(width=595, height=842); y = 60
        r = fitz.Rect(60, y, 535, 800)
        font = "tibo" if bold else "tiro"
        sobra = page.insert_textbox(r, texto, fontsize=size, fontname=font, align=fitz.TEXT_ALIGN_JUSTIFY)
        usado = (800 - y) - sobra
        y += usado + gap
    bloco(f"(11) {doc['numero']}    (22) Depósito: {doc['deposito']}", 9)
    bloco(f"(54) {doc['titulo']}", 13, True)
    bloco("(57) RESUMO", 11, True, 2)
    bloco(doc["resumo"])
    bloco("REIVINDICAÇÕES", 11, True, 2)
    for i, r in enumerate(doc["reivindicacoes"], 1):
        bloco(f"{i}. {r}")
    for f in doc["figuras"]:
        if y > 520:
            page = pdf.new_page(width=595, height=842); y = 60
        rect = fitz.Rect(200, y, 395, y + 150)
        desenhar_figura(page, rect, f["numero"])
        y += 158
        bloco(f"FIGURA {f['numero']} - {f['legenda']}", 10, False, 14)
    pdf.save(caminho)

def escanear(pdf_in, pdf_out, intensidade):
    """Renderiza cada página em 150 dpi, gira levemente, borra e adiciona ruído."""
    src = fitz.open(pdf_in); out = fitz.open()
    for p in src:
        pix = p.get_pixmap(dpi=150, colorspace=fitz.csGRAY)
        img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
        img = img.rotate(random.uniform(-1.2, 1.2) * intensidade, fillcolor=255, expand=False)
        img = img.filter(ImageFilter.GaussianBlur(0.6 + 0.5 * intensidade))
        a = np.array(img).astype(np.int16)
        a += np.random.normal(0, 18 * intensidade, a.shape).astype(np.int16)
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        img = img.resize((int(img.width * 0.8), int(img.height * 0.8)))  # perde resolução
        tmp = OUT / "_tmp.jpg"; img.save(tmp, quality=70)
        pg = out.new_page(width=595, height=842)
        pg.insert_image(pg.rect, filename=str(tmp))
        tmp.unlink()
    out.save(pdf_out)

for d in DOCS:
    base = OUT / d["id"]
    gerar_pdf(d, f"{base}_original.pdf")
    gab = {"titulo": d["titulo"], "resumo": d["resumo"],
           "reivindicacoes": d["reivindicacoes"],
           "legendas": [f"FIGURA {f['numero']} - {f['legenda']}" for f in d["figuras"]],
           "n_figuras": len(d["figuras"])}
    Path(f"{base}_gabarito.json").write_text(json.dumps(gab, ensure_ascii=False, indent=2), encoding="utf-8")
    escanear(f"{base}_original.pdf", f"{base}_escaneado.pdf", d["qualidade_scan"])
    print("gerado", d["id"])
