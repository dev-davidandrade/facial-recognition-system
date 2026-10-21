# ADR 0002 — Pesos fora do Git e uso de pesquisa

- Status: aceito
- Data: 2026-10-20

## Contexto

Pesos são grandes, possuem licença e procedência próprias e podem não estar aprovados para uso
comercial mesmo quando o código ao redor é permissivo.

## Decisão

Não versionar ONNX. Manter manifesto com origem, hash, licença declarada e status; exigir ação
explícita para obter modelos; validar checksum e dimensão. YuNet e SFace começam como
`research_only`.

## Consequências

Saúde e testes funcionam sem pesos, mas readiness e verificação real permanecem indisponíveis até
a instalação local. Promoção exige revisão documental e avaliação.
