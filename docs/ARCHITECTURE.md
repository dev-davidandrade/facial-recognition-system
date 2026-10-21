# Arquitetura

## Princípios

- O domínio conhece decisões e contratos, não frameworks.
- A biometria identifica; uma política separada autoriza.
- A entrada é uma imagem ou `FrameSource`, nunca uma câmera específica.
- A saída é resposta estruturada ou `DecisionPublisher`, nunca comando de hardware.
- Modelos e limiares são versionados e substituíveis.

```mermaid
flowchart LR
    Client[Cliente / fonte de quadros] --> API[API versionada]
    API --> Decoder[ImageDecoder]
    Decoder --> UseCase[Casos de uso]
    UseCase --> Detector[FaceDetector: YuNet]
    UseCase --> Quality[FaceQualityEvaluator]
    UseCase --> Aligner[FaceAligner]
    UseCase --> Embedder[FaceEmbedder: SFace]
    UseCase --> Matcher[FaceMatcher]
    UseCase --> Bio[Decisão biométrica]
    Bio --> Policy[AuthorizationPolicy]
    Policy --> Auth[Decisão de autorização]
    Auth --> Publisher[DecisionPublisher]
    Bio --> Audit[(PostgreSQL + pgvector)]
    Auth --> Audit
```

## Camadas

- `domain`: entidades, enumerações, regras puras e protocolos.
- `application`: orquestração dos casos de uso.
- `adapters`: OpenCV, PostgreSQL, fontes de quadros e eventos.
- `api`: transporte HTTP e schemas públicos sem embeddings.
- `config`: configuração tipada por variáveis de ambiente.
- `observability`: logs estruturados; métricas e traces virão depois.

## Comparação 1:1 atual

Cada imagem é decodificada em memória, deve conter exatamente um rosto e passa pelos critérios de
qualidade. O rosto é alinhado pelos cinco landmarks do YuNet, transformado em embedding SFace,
normalizado e comparado por cosseno. O resultado é `identified` ou `unknown`; falhas anteriores
produzem decisões biométricas específicas.

## Cadastro e identificação 1:N

O cadastro consentido persiste pessoas, versões de modelo e múltiplos templates normalizados. Um
lote é transacional, e a revogação desativa todos os templates. A identificação consulta o
pgvector apenas na mesma versão de modelo, agrega o melhor template de cada pessoa e avalia o
melhor candidato, o segundo e a margem entre eles. O resultado continua sendo somente biométrico.

Política de autorização e registro persistente de eventos serão incrementos separados. O fluxo
temporal consumirá `FrameSource` e não alterará o domínio biométrico.
