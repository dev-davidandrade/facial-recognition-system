# Contrato da API

## Endpoints atuais

### `POST /v1/persons`

Cria uma pessoa ativa. Exige `consent_confirmed=true` e uma versão de consentimento. Nome e
identificador externo são opcionais; prefira valores pseudônimos. Retorna `409` se o identificador
externo já estiver cadastrado.

### `GET /v1/persons/{person_id}`

Consulta estado e metadados mínimos da pessoa. Não devolve templates nem embeddings.

### `POST /v1/persons/{person_id}/enroll`

Recebe de 2 a 10 imagens JPEG/PNG no campo multipart `images`. Cada imagem deve conter exatamente
um rosto e passar na qualidade. Amostras inválidas são descartadas individualmente; o lote é
rejeitado apenas quando restam menos de duas imagens válidas. Em sucesso, persiste os templates
válidos normalizados associados à versão exata dos modelos e informa os descartes na resposta.

### `DELETE /v1/persons/{person_id}`

Revoga logicamente a pessoa e desativa todos os seus templates na mesma transação. A exclusão ou
anonimização definitiva será um caso de uso separado, sujeito à política de retenção.

### `GET /health`

Indica que o processo HTTP está vivo. Não testa modelos ou banco.

### `GET /ready`

Testa presença dos dois modelos e conectividade do PostgreSQL. Retorna `503` enquanto alguma
dependência obrigatória estiver indisponível.

### `POST /v1/verifications/verify`

`multipart/form-data` com:

- `first_image`: JPEG ou PNG;
- `second_image`: JPEG ou PNG;
- `source_id`: identificador lógico opcional, máximo de 100 caracteres.

Limites padrão: 8 MiB por arquivo e 16 megapixels após decodificação. A resposta traz transação,
decisão biométrica, `is_match`, similaridade, limiar, qualidade, motivo, versões, latência e
timestamp. Nunca traz embeddings.

Erros de transporte: `413` para excesso de bytes, `415` para mídia não permitida, `422` para
conteúdo vazio e `503` quando os modelos não estão configurados.

### `POST /v1/identifications/identify`

Recebe uma imagem JPEG/PNG no campo multipart `image` e um `source_id` opcional. A imagem deve
conter exatamente um rosto e passar nos critérios de qualidade. A busca 1:N usa somente templates
ativos, pessoas ativas e a versão exata dos modelos em execução.

A resposta contém `identified`, `unknown`, `ambiguous` ou uma rejeição de qualidade/detecção,
além do melhor escore, segundo melhor escore, margem, limiares, pessoa encontrada e versões dos
modelos. Dados do candidato só são devolvidos em `identified`; embeddings nunca são expostos.
Esta decisão é biométrica e não equivale a autorização de acesso.

### `GET /v1/identifications/temporal-policy`

Expõe somente os parâmetros públicos usados pelo console local: confirmações exigidas, tamanho da
janela, intervalo máximo entre observações, prazo para revisão e intervalo entre capturas. O
endpoint não cria sessão, não recebe biometria e não expõe segredos ou limiares administrativos.

## Evento futuro

```json
{
  "event_type": "access_decision",
  "correlation_id": "uuid",
  "decision": "access_granted",
  "person_id": "uuid",
  "reason": "authorized_identity",
  "confidence": 0.87,
  "model_version": "string",
  "occurred_at": "ISO-8601"
}
```

O evento é uma decisão para consumo externo; não é comando de cancela.
