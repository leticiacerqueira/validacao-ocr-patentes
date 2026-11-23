# Relatório de validação

| Documento | Ruído do scan | CER bruto | CER após regras | WER bruto | WER após regras |
|---|---:|---:|---:|---:|---:|
| BR001 | 0.6 | 2.9% | 2.3% | 8.7% | 5.2% |
| BR002 | 1.0 | 4.6% | 3.8% | 12.2% | 9.3% |
| BR003 | 1.4 | 6.4% | 6.1% | 23.8% | 22.5% |
| BR004 | 1.6 | 27.5% | 27.4% | 51.2% | 50.6% |

**67 divergências**: 16 corrigíveis direto e 51 sinalizadas para revisão.

| Tipo | Ação | Ocorrências |
|---|---|---:|
| caractere trocado | revisar | 25 |
| número | revisar | 15 |
| caractere trocado | corrigir | 13 |
| inserção | revisar | 7 |
| símbolo/unidade | revisar | 4 |
| acentuação | corrigir | 3 |

| Documento | Figuras esperadas | Legendas lidas | Status |
|---|---:|---:|---|
| BR001 | 1 | 1 | ok |
| BR002 | 2 | 2 | ok |
| BR003 | 1 | 1 | ok |
| BR004 | 1 | 0 | revisar: numeração ou legenda divergente |
