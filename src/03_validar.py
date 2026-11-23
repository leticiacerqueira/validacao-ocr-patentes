"""Valida o texto extraído por OCR contra o gabarito de cada patente.

Para cada documento:
  1. Aplica correções automáticas seguras (regras) ao texto do OCR.
  2. Alinha o texto com o gabarito palavra a palavra e mede CER e WER antes e depois.
  3. Classifica cada divergência (acentuação, número, símbolo/unidade, caractere trocado,
     palavra quebrada, omissão, inserção) e decide: corrigir direto ou sinalizar para revisão.
  4. Confere figuras: se todas as legendas foram encontradas e se a numeração está em sequência.
Saídas em saida/: inconsistencias.csv, resumo_por_documento.csv, figuras.csv
"""
import csv, json, re
from difflib import SequenceMatcher
from pathlib import Path
from rapidfuzz.distance import Levenshtein
from unidecode import unidecode

RAIZ = Path(__file__).resolve().parent.parent
DOCS, OCR, OUT = RAIZ / "documentos", RAIZ / "saida" / "ocr", RAIZ / "saida"
SIMBOLOS = set("²³°±µ%/")

# ---------- 1. correções automáticas por regras (sem olhar o gabarito) ----------
REGRAS = [
    (r"(\w)-\n(\w)", r"\1\2", "palavra hifenizada na quebra de linha"),
    (r"(?<=\d)\s?m[?23](?=\W|$)", " m³", "unidade m³ lida como m? / m3"),
    (r"(?<=\d)\s?º\s?C", " °C", "grau lido como º (ordinal)"),
    (r"(?<=\d) ?g/cm[?23]", " g/cm³", "unidade g/cm³"),
    (r"(?<=\d) um\b", " µm", "µm lido como um"),
    (r"(?<=\d) ?g[hl/]?t?\b(?= a | e |\.|,)", " g/t", "unidade g/t lida como gh"),
    (r"(?<=\s)\|(?=[\s.,])", "1", "número 1 lido como barra |"),
    (r"(?<=\d)O(?=\d)", "0", "letra O no meio de número"),
    (r"(?<=\d)[lI](?=\d)", "1", "letra l/I no meio de número"),
    (r"\+ ?/ ?-|\+ (?=0,)", "± ", "sinal ± "),
    (r"[ \t]+", " ", "espaços repetidos"),
]
def corrigir(texto):
    log = []
    for padrao, novo, nome in REGRAS:
        texto, n = re.subn(padrao, novo, texto)
        if n and nome != "espaços repetidos":
            log.append((nome, n))
    return texto, log

# ---------- 2. preparação e alinhamento ----------
def texto_gabarito(g):
    partes = [g["titulo"], "RESUMO", g["resumo"], "REIVINDICAÇÕES"]
    partes += [f"{i}. {r}" for i, r in enumerate(g["reivindicacoes"], 1)]
    partes += g["legendas"]
    return " ".join(partes)

def limpar_ocr(t):
    linhas = [l for l in t.splitlines() if l.strip()]
    linhas = [l for l in linhas if not re.search(r"Dep[óo]sito|^\W*\(?\d{1,2}\)?\s*BR", l)]  # cabeçalho
    linhas = [l for l in linhas if not re.fullmatch(r"\W*\d{1,2}\W*", l)]               # marcas da figura
    t = " ".join(linhas)
    t = re.sub(r"\(5[47]\)|4?5[47]\)", " ", t)  # códigos de campo (54) (57)
    return re.sub(r"\s+", " ", t).strip()

def tokens(t):
    return t.split()

def classificar(ext, cor):
    e, c = " ".join(ext), " ".join(cor)
    if not ext: return "omissão"
    if not cor: return "inserção"
    if e.replace(" ", "") == c.replace(" ", ""): return "palavra quebrada/unida"
    if unidecode(e) == unidecode(c): return "acentuação"
    if any(ch in SIMBOLOS for ch in c) or any(ch in SIMBOLOS for ch in e): return "símbolo/unidade"
    if any(ch.isdigit() for ch in c + e): return "número"
    if e.lower() == c.lower(): return "maiúscula/minúscula"
    return "caractere trocado"

def decidir(tipo, ext, cor, conf_min):
    """Corrigir direto só o que é inequívoco; o resto vai para revisão humana."""
    if tipo in ("palavra quebrada/unida", "maiúscula/minúscula"): return "corrigir"
    if tipo == "acentuação" and len(cor) == 1: return "corrigir"
    if tipo == "caractere trocado" and len(ext) == len(cor) == 1 \
            and Levenshtein.distance(ext[0], cor[0]) <= 2 and conf_min >= 60: return "corrigir"
    return "revisar"

def confiancas(doc_id):
    conf = {}
    with open(OCR / f"{doc_id}_palavras.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            conf.setdefault(r["palavra"], []).append(float(r["confianca"]))
    return {k: min(v) for k, v in conf.items()}

# ---------- 3. execução ----------
inconsist, resumo, figuras, regras_log = [], [], [], []
for gab_path in sorted(DOCS.glob("*_gabarito.json")):
    doc_id = gab_path.name.split("_")[0]
    g = json.loads(gab_path.read_text(encoding="utf-8"))
    ref = texto_gabarito(g)
    bruto = (OCR / f"{doc_id}.txt").read_text(encoding="utf-8")
    corrigido, log = corrigir(bruto)
    for nome, n in log: regras_log.append({"documento": doc_id, "regra": nome, "aplicacoes": n})
    ocr_antes, ocr_depois = limpar_ocr(bruto), limpar_ocr(corrigido)
    conf = confiancas(doc_id)

    tr, ta, td = tokens(ref), tokens(ocr_antes), tokens(ocr_depois)
    m = SequenceMatcher(a=td, b=tr, autojunk=False)
    for op, i1, i2, j1, j2 in m.get_opcodes():
        if op == "equal": continue
        ext, cor = td[i1:i2], tr[j1:j2]
        cmin = min([conf.get(w, 0) for w in ext], default=0)
        tipo = classificar(ext, cor)
        inconsist.append({"documento": doc_id, "tipo": tipo,
                          "extraido": " ".join(ext)[:120], "correto": " ".join(cor)[:120],
                          "confianca_ocr": round(cmin), "acao": decidir(tipo, ext, cor, cmin)})

    def wer(h): return Levenshtein.distance(h, tr) / len(tr)
    resumo.append({"documento": doc_id, "palavras_gabarito": len(tr),
                   "cer_antes_pct": round(100 * Levenshtein.normalized_distance(ocr_antes, ref), 1),
                   "cer_depois_pct": round(100 * Levenshtein.normalized_distance(ocr_depois, ref), 1),
                   "wer_antes_pct": round(100 * wer(ta), 1), "wer_depois_pct": round(100 * wer(td), 1)})

    achadas = [int(n) for n in re.findall(r"FIGURA\s+(\d+)", corrigido, flags=re.I)]
    esperadas = list(range(1, g["n_figuras"] + 1))
    figuras.append({"documento": doc_id, "figuras_esperadas": g["n_figuras"],
                    "legendas_encontradas": len(achadas), "numeros_lidos": " ".join(map(str, achadas)),
                    "status": "ok" if achadas == esperadas else "revisar: numeração ou legenda divergente"})

def salvar(nome, linhas):
    with open(OUT / nome, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0])); w.writeheader(); w.writerows(linhas)
salvar("inconsistencias.csv", inconsist)
salvar("resumo_por_documento.csv", resumo)
salvar("figuras.csv", figuras)
salvar("regras_aplicadas.csv", regras_log)
for r in resumo: print(r)
for f in figuras: print(f)
from collections import Counter
print(Counter((i["tipo"], i["acao"]) for i in inconsist).most_common())
print(len(inconsist))
