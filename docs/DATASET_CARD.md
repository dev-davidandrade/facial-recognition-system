# Dataset Card

## Estado

Nenhum dataset e nenhuma imagem biométrica fazem parte deste repositório. Os testes usam fakes e
vetores sintéticos, sem representar pessoas.

## Política para uma futura coleta

- somente imagens próprias, voluntários com consentimento documentado ou datasets formalmente
  licenciados para a finalidade;
- nada de scraping;
- registrar origem, licença, finalidade, população, condições, limitações e retenção;
- manter cadastro, validação, teste final e teste externo sem sobreposição de capturas;
- armazenar fora do Git, com acesso mínimo, criptografia de infraestrutura e exclusão verificável;
- revisar manualmente rótulos e qualidade.

## Protocolo mínimo de avaliação

Medir FAR, FRR, EER, TAR, ROC, rank-1, rejeição de desconhecidos, ambiguidades, p50/p95, FPS, CPU e
memória. Estratificar por iluminação, pose, distância, óculos, desfoque e quantidade de identidades.
Falhas e intervalos de confiança devem acompanhar qualquer métrica agregada.
