# Segurança

## Estado atual

Esta é uma fundação local de laboratório. A API ainda não possui autenticação, rate limiting,
OIDC, trilha administrativa completa ou detecção de vivacidade. Ela deve escutar apenas em
`127.0.0.1` e não deve ser exposta à internet.

Os endpoints de cadastro e revogação são administrativos. Enquanto autenticação não existir,
utilize-os somente na máquina local e não publique a porta 8000 na rede.

## Controles implementados

- `.env`, pesos, dados e artefatos são ignorados pelo Git;
- upload limitado por tipo MIME, bytes e quantidade de pixels;
- nomes de arquivo enviados pelo cliente não são utilizados;
- imagens são decodificadas em memória;
- modelos e banco fazem parte do readiness;
- a porta do PostgreSQL no Compose é vinculada explicitamente a `127.0.0.1`;
- respostas não expõem embeddings;
- logs estruturados não recebem imagens nem embeddings.

O modo webcam exige uma ação explícita do usuário. O navegador captura apenas um quadro por vez,
libera a câmera ao encerrar o fluxo e não persiste o vídeo ou os quadros analisados. No cadastro
assistido, cinco quadros ficam temporariamente na memória para revisão e são descartados ao sair,
cancelar ou concluir o envio.

## Antes de produção

Exigir TLS, autenticação OIDC/OAuth2, perfis administrativos, rate limiting, proteção do banco e
volumes, rotação de segredos, auditoria de cadastro/revogação/configuração, política de retenção,
monitoramento, backup testado, model threat assessment e antispoofing validado. Uma API key pode
ser adicionada somente como controle temporário de desenvolvimento.

Relate vulnerabilidades de forma privada ao mantenedor; não inclua amostras biométricas no relato.
