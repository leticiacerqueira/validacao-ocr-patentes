"""Gera o gráfico de qualidade e o relatório em Markdown a partir das saídas do validador."""
import csv, json
from collections import Counter
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parent.parent
OUT = RAIZ / "saida"
ler = lambda n: list(csv.DictReader(open(OUT / n, encoding="utf-8")))
res, inc, fig = ler("resumo_por_documento.csv"), ler("inconsistencias.csv"), ler("figuras.csv")
qual = {d["id"]: d["qualidade_scan"] for d in json.load(open(RAIZ / "src/patentes_exemplo.json", encoding="utf-8"))}

# gráfico: CER antes e depois das regras, por documento (ordenado por ruído do scan)
fig_, ax = plt.subplots(figsize=(7, 3.6))
docs = [r["documento"] for r in res]
x = range(len(docs))
ax.bar([i - 0.2 for i in x], [float(r["cer_antes_pct"]) for r in res], 0.4, label="OCR bruto", color="#9aa59f")
ax.bar([i + 0.2 for i in x], [float(r["cer_depois_pct"]) for r in res], 0.4, label="Após regras", color="#1f6f62")
ax.set_xticks(list(x), [f"{d}\nruído {qual[d]}" for d in docs])
ax.set_ylabel("CER (% de caracteres errados)")
ax.spines[["top", "right"]].set_visible(False); ax.legend(frameon=False)
plt.tight_layout(); plt.savefig(OUT / "cer_por_documento.png", dpi=150)

tipos = Counter((i["tipo"], i["acao"]) for i in inc)
acoes = Counter(i["acao"] for i in inc)
linhas = ["# Relatório de validação", "",
          "| Documento | Ruído do scan | CER bruto | CER após regras | WER bruto | WER após regras |",
          "|---|---:|---:|---:|---:|---:|"]
for r in res:
    linhas.append(f"| {r['documento']} | {qual[r['documento']]} | {r['cer_antes_pct']}% | {r['cer_depois_pct']}% | {r['wer_antes_pct']}% | {r['wer_depois_pct']}% |")
linhas += ["", f"**{len(inc)} divergências**: {acoes['corrigir']} corrigíveis direto e {acoes['revisar']} sinalizadas para revisão.", "",
           "| Tipo | Ação | Ocorrências |", "|---|---|---:|"]
linhas += [f"| {t} | {a} | {n} |" for (t, a), n in tipos.most_common()]
linhas += ["", "| Documento | Figuras esperadas | Legendas lidas | Status |", "|---|---:|---:|---|"]
linhas += [f"| {f['documento']} | {f['figuras_esperadas']} | {f['legendas_encontradas']} | {f['status']} |" for f in fig]
(OUT / "relatorio.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
print("\n".join(linhas))
