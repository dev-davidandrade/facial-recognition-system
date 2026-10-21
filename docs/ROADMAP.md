# Trilha de desenvolvimento

Atualizado em 2026-10-20.

## Etapa 1 — Fundação: concluída

- Python 3.12, uv, qualidade, testes e CI;
- arquitetura modular e configuração tipada;
- PostgreSQL/pgvector, Alembic, health e readiness;
- documentação de segurança, privacidade, modelos e decisões.

## Etapa 2 — Comparação 1:1: baseline concluído

- YuNet, alinhamento e SFace atrás de interfaces;
- qualidade, similaridade cosseno e API multipart;
- testes manuais de baixa qualidade, imagem idêntica, capturas distintas, ausência de rosto e
  múltiplos rostos;
- limiares continuam experimentais e não calibrados.

## Etapa 3 — Cadastro e identificação 1:N: em andamento

Concluído:

- criação e consulta de pessoa consentida;
- cadastro atômico de 2 a 10 imagens;
- múltiplos templates normalizados no pgvector;
- registro da versão e checksum combinado dos modelos;
- revogação da pessoa e desativação de todos os templates;
- busca 1:N restrita à versão exata do modelo;
- melhor e segundo melhor candidatos, margem e rejeição de desconhecido/ambiguidade.

Próximo:

- política de autorização e eventos de reconhecimento;
- eliminação/anonimização conforme política de retenção.

## Etapas seguintes

4. Confirmação temporal em fluxos de quadros.
5. Demonstração e publishers de integração.
6. Protocolo de avaliação, calibração, autenticação, auditoria, retenção e antispoofing.

Testes funcionais não constituem validação biométrica. FAR, FRR, EER, ROC e demais métricas exigem
um protocolo com identidades consentidas, conjuntos separados e limiar congelado antes do teste.
