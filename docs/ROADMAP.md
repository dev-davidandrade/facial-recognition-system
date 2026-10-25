# Trilha de desenvolvimento

Atualizado em 2026-10-23.

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

## Etapa 3.5 — Console visual de testes: baseline concluído

- interface local servida pelo próprio FastAPI em `/demo`;
- criação de pessoa e cadastro de imagens consentidas;
- identificação 1:N e comparação 1:1 sem requisições manuais;
- estado de health/readiness e resultados biométricos traduzidos para a interface;
- pré-visualizações efêmeras no navegador, sem persistência adicional de imagens;
- captura opcional pela webcam, sem gravação do vídeo;
- cadastro assistido com cinco quadros guiados, revisão e confirmação pelo operador;
- apresentação de portfólio ainda pode receber polimento e explicações interativas.

## Etapa 4 — Confirmação temporal: baseline implementado, validação real pendente

- captura controlada de quadros JPEG no navegador, com uma requisição por vez;
- política configurável publicada pela API;
- janela deslizante de 5 quadros e exigência de 3 confirmações da mesma pessoa;
- análise iniciada somente após a primeira detecção de rosto;
- revisão após 5 segundos sem evidência consistente;
- câmera e quadros liberados ao encerrar ou sair do fluxo.

Pendente: testar com a webcam real em rosto cadastrado, desconhecido e interrupções do enquadramento.

## Etapas seguintes

5. Demonstração e publishers de integração.
6. Protocolo de avaliação e calibração: baseline documental e módulo de grade implementados;
   coleta consentida e teste final ainda pendentes.
7. Autenticação, auditoria, retenção e antispoofing.

Testes funcionais não constituem validação biométrica. FAR, FRR, EER, ROC e demais métricas exigem
um protocolo com identidades consentidas, conjuntos separados e limiar congelado antes do teste.
