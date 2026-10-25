# Face Recognition Access Lab

Laboratório pessoal e open source para estudar um pipeline modular de reconhecimento facial em
cenários de acesso consentido. O projeto é exclusivamente de software: recebe imagens, produz
decisões estruturadas e publica eventos substituíveis. Ele **não controla câmera, cancela, motor,
GPIO ou qualquer outro equipamento físico**.

> **Status: experimental.** Não há detecção de vivacidade neste incremento. Fotografias, telas e
> replays podem enganar o sistema. Não use esta versão para conceder acesso físico real.

## O que já funciona

- domínio sem dependência de FastAPI, OpenCV ou SQLAlchemy;
- contratos substituíveis para detecção, alinhamento, embeddings, qualidade, matching,
  vivacidade, persistência, autorização, quadros e eventos;
- comparação facial 1:1 com YuNet + SFace por adaptadores OpenCV;
- cadastro consentido de pessoas e múltiplos templates faciais por pessoa;
- identificação 1:N contra templates ativos da mesma versão de modelo;
- consulta e revogação, com desativação atômica dos templates;
- rejeição de zero rosto, múltiplos rostos e baixa qualidade;
- comparação por similaridade cosseno com limiar configurável;
- `GET /health`, `GET /ready`, verificação 1:1 e identificação 1:N;
- esquema PostgreSQL/pgvector versionado com Alembic;
- testes sem câmera, pesos ONNX ou dados biométricos reais.

Confirmação temporal, autenticação, auditoria completa, métricas e ant-spoofing são incrementos
posteriores. A identificação atual é experimental e não constitui autorização de acesso.

## Requisitos

- Python 3.12 (o `uv` pode instalá-lo automaticamente);
- [uv](https://docs.astral.sh/uv/);
- Docker com Compose, para PostgreSQL/pgvector.

## Execução local

```powershell
Copy-Item .env.example .env
docker compose up -d postgres
uv sync --all-groups
uv run alembic upgrade head
uv run uvicorn face_access.main:app --reload
```

A documentação interativa fica em `http://127.0.0.1:8000/docs`.

Para testar os fluxos sem montar requisições manualmente, abra o console visual local em
`http://127.0.0.1:8000/demo`. A página permite criar uma pessoa, cadastrar imagens, identificar
uma imagem contra a galeria, comparar duas imagens, coletar cinco amostras de cadastro pela webcam
e usar a câmera com confirmação temporal.
No modo ao vivo, a mesma identidade precisa aparecer em 3 dos últimos 5 quadros; uma tentativa
inconclusiva termina em revisão após 5 segundos. As pré-visualizações e os quadros existem somente
na memória do navegador e não são persistidos pela interface.

No cadastro assistido, crie ou consulte a pessoa, selecione **Usar webcam**, capture as cinco
amostras guiadas e revise as miniaturas antes de confirmar. Quadros inválidos são descartados
individualmente; o cadastro continua quando pelo menos duas amostras válidas permanecem. Sair da
área de cadastro ou descartar a captura elimina imediatamente essas amostras temporárias.

Os pesos não estão no Git. Depois de revisar [o cartão dos modelos](docs/MODEL_CARD.md) e aceitar
o uso estritamente experimental:

```powershell
uv run python scripts/fetch_models.py --accept-research-only
uv run python scripts/validate_models.py
```

O validador confirma checksums e verifica programaticamente que o SFace configurado produz
embeddings de 128 dimensões, a dimensão da migration inicial.

## Pesquisa e calibração

As decisões experimentais são registradas no [diário de pesquisa](docs/RESEARCH_LOG.md). O
[protocolo experimental](docs/RESEARCH_METHOD.md) define separação de sessões, métricas e ameaças à
validade; a [base bibliográfica](docs/LITERATURE_REVIEW.md) começa pelas fontes primárias de YuNet e
SFace.

Uma grade de limiares pode ser avaliada sem imagens, embeddings ou nomes:

```powershell
uv run face-access-calibrate docs/examples/calibration_observations.example.csv `
  --output artifacts/calibration-grid.csv
```

O CSV de exemplo é sintético. Resultados dele verificam a ferramenta, não medem o sistema.

## Comparação 1:1

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/verifications/verify `
  -F "first_image=@primeira.jpg;type=image/jpeg" `
  -F "second_image=@segunda.jpg;type=image/jpeg" `
  -F "source_id=manual-test"
```

A resposta nunca inclui o embedding. `identified` indica apenas compatibilidade biométrica no
limiar experimental; não equivale a autorização de acesso.

## Cadastro consentido

Pelo Swagger em `http://127.0.0.1:8000/docs`:

1. use `POST /v1/persons` com consentimento explícito e um identificador pseudônimo;
2. copie o `id` retornado;
3. use `POST /v1/persons/{person_id}/enroll` com 2 a 10 imagens;
4. consulte com `GET /v1/persons/{person_id}`;
5. `DELETE /v1/persons/{person_id}` revoga a pessoa e desativa seus templates.

Imagens sem exatamente um rosto ou que falhem na qualidade são descartadas. Se restarem menos de
duas imagens válidas, nenhum template será persistido; caso contrário, apenas os templates válidos
são gravados na mesma transação. Revogação não equivale à exclusão/anonimização definitiva, que
será implementada junto à política de retenção.

## Identificação 1:N

Envie uma imagem nova, que não tenha sido usada no cadastro:

```powershell
curl.exe -X POST http://127.0.0.1:8000/v1/identifications/identify `
  -F "image=@consulta.jpg;type=image/jpeg" `
  -F "source_id=manual-identification-test"
```

A busca considera somente pessoas e templates ativos associados à versão exata dos modelos em
uso. O resultado informa o melhor escore, o segundo melhor, a margem e os limiares. Um escore
abaixo do limiar produz `unknown`; candidatos próximos produzem `ambiguous`. Com apenas uma pessoa
cadastrada, ainda não é possível exercitar a regra de ambiguidade.

## Qualidade

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## Segurança, privacidade e dados

Rostos e embeddings são dados biométricos sensíveis. Use apenas imagens próprias ou de
voluntários com consentimento documentado. Não faça scraping e não envie imagens, nomes ou
embeddings reais ao GitHub. O processamento é local; imagens recebidas são decodificadas em
memória e não são persistidas por padrão.

Leia [PRIVACY.md](docs/PRIVACY.md), [SECURITY.md](docs/SECURITY.md) e
[DATASET_CARD.md](docs/DATASET_CARD.md) antes de coletar qualquer dado.

## Modelos e licenças

O laboratório usa YuNet para detecção e SFace para embeddings. Os arquivos ONNX não são
distribuídos neste repositório. Embora os diretórios do OpenCV Zoo declarem MIT (YuNet) e
Apache-2.0 (SFace), a procedência dos dados de treinamento do peso SFace precisa de análise antes
de qualquer uso comercial. Por isso ambos estão marcados `research_only` neste projeto.

O código deste repositório é licenciado sob MIT. Essa licença não altera nem substitui as licenças
dos modelos ou datasets de terceiros.

## Documentação

- [Arquitetura](docs/ARCHITECTURE.md)
- [Contrato da API](docs/API_CONTRACT.md)
- [Política de decisão](docs/DECISION_POLICY.md)
- [Trilha de desenvolvimento](docs/ROADMAP.md)
- [Execução da demonstração em outra máquina](docs/DEMO_SETUP.md)
- [Cartão dos modelos](docs/MODEL_CARD.md)
- [Avisos de terceiros](docs/THIRD_PARTY_NOTICES.md)
