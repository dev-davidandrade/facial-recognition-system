# ADR 0001 — Portas e adaptadores para o núcleo biométrico

- Status: aceito
- Data: 2026-10-20

## Contexto

Modelos, transporte HTTP, persistência e fontes de imagem devem mudar sem reescrever as regras de
negócio ou incorporar dependência de hardware.

## Decisão

Usar domínio puro e contratos (`Protocol`) para capacidades externas. Casos de uso dependem das
portas; OpenCV, FastAPI, SQLAlchemy e publishers são adaptadores. Reconhecimento e autorização são
duas decisões distintas.

## Consequências

Testes usam fakes sem câmera ou modelo. Há mais objetos e composição explícita, mas substituição de
modelo, banco ou transporte fica localizada.
