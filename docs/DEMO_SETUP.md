# Execução da demonstração em outra máquina

Este guia reproduz localmente a prova de viabilidade. O sistema é experimental, não possui
detecção de vivacidade e não deve controlar acesso físico real.

## 1. Pré-requisitos no Windows

- Git;
- Docker Desktop configurado para contêineres Linux;
- `uv` disponível no terminal;
- acesso à internet para baixar dependências, a imagem PostgreSQL e os pesos registrados.

Confirme em um PowerShell:

```powershell
git --version
docker version
docker compose version
uv --version
```

Abra o Docker Desktop e aguarde o engine ficar pronto antes de continuar.

## 2. Obter e configurar o projeto

Clone o repositório quando o remoto estiver publicado e entre na pasta:

```powershell
git clone <URL_DO_REPOSITORIO>
Set-Location facial_recognition_system
Copy-Item .env.example .env
```

Se o projeto for transferido como pasta, basta abrir o PowerShell na raiz e executar somente o
`Copy-Item`. O `.env` é local e não deve ser enviado ao Git.

## 3. Instalar o ambiente Python

```powershell
uv sync --all-groups
```

O `uv` usa a versão fixada no projeto e cria o ambiente virtual automaticamente.

## 4. Subir e preparar o PostgreSQL/pgvector

```powershell
docker compose up -d postgres
docker compose ps
uv run alembic upgrade head
```

Prossiga quando o serviço `postgres` aparecer como `healthy`. O volume do Docker preserva os
cadastros entre reinicializações.

## 5. Obter e validar os modelos

Antes de executar, leia `docs/MODEL_CARD.md`. Os pesos são externos ao Git e estão limitados ao
laboratório experimental enquanto a procedência/licença não for completamente validada.

```powershell
uv run python scripts/fetch_models.py --accept-research-only
uv run python scripts/validate_models.py
```

O segundo comando deve confirmar os dois checksums e um embedding SFace de 128 dimensões.

## 6. Validar o projeto

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## 7. Iniciar a API

```powershell
uv run uvicorn face_access.main:app --host 127.0.0.1 --port 8000 --reload
```

Em outro terminal, confira:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
```

Abra `http://127.0.0.1:8000/docs`. A raiz `http://127.0.0.1:8000/` retornar `404` é esperado.

## 8. Roteiro curto da demonstração

Pelo Swagger, nesta ordem:

1. `POST /v1/persons`: crie uma pessoa com consentimento explícito e copie o `id`;
2. `POST /v1/persons/{person_id}/enroll`: envie de 2 a 10 imagens consentidas;
3. `POST /v1/identifications/identify`: envie outra foto da pessoa, não usada no cadastro;
4. `POST /v1/verifications/verify`: demonstre a comparação direta entre duas imagens;
5. opcionalmente demonstre as rejeições com zero rosto, múltiplos rostos ou baixa qualidade.

O cadastro guarda embeddings e metadados no PostgreSQL. As imagens recebidas são processadas em
memória e não são persistidas pela aplicação.

## 9. Encerrar sem apagar o banco

Interrompa a API com `Ctrl+C` e execute:

```powershell
docker compose stop postgres
```

Não use `docker compose down -v` se quiser preservar os cadastros; a opção `-v` remove o volume e
os dados locais.

## Solução rápida de problemas

- **Erro no pipe `dockerDesktopLinuxEngine`:** abra ou reinicie o Docker Desktop e valide com
  `docker info` antes de repetir o Compose.
- **PostgreSQL não fica saudável:** consulte `docker compose logs postgres`.
- **Porta 5432 ocupada:** altere `POSTGRES_PORT` e a porta correspondente em
  `FACE_ACCESS_DATABASE_URL` no `.env`.
- **`/ready` informa modelo ausente:** execute novamente os comandos da seção 5.
- **A rota nova não aparece no Swagger:** aguarde o `--reload` e faça `Ctrl+F5` no navegador.

## Limites da prova de viabilidade

O limiar atual é experimental. A demonstração comprova o fluxo técnico, mas não mede FAR, FRR,
EER, robustez demográfica ou resistência a ataques. Use somente dados próprios ou de voluntários
com consentimento, e não misture imagens, segredos ou configurações proprietárias da empresa com
o repositório pessoal.
