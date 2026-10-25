# Protocolo experimental e calibração

## Objetivo

Investigar como qualidade da imagem, limiar de similaridade e confirmação temporal afetam cobertura,
falsas aceitações, falsas rejeições e latência no protótipo YuNet + SFace. O objetivo é produzir
evidência para um artigo e uma demonstração local, não certificar um sistema de segurança.

## Questão de pesquisa

Qual combinação de qualidade mínima, similaridade e confirmação temporal oferece o melhor
compromisso mensurável entre reconhecimento genuíno, rejeição de impostores, cobertura e tempo de
resposta nas condições avaliadas?

## Variáveis

Variáveis independentes iniciais:

- qualidade da referência de cadastro;
- qualidade mínima aceita na consulta;
- similaridade cosseno entre `0,35` e `0,65`;
- confirmação temporal, começando por uma decisão isolada e `3 de 5` quadros;
- condição da consulta: controlada, pouca luz, leve movimento, óculos e obstrução parcial.

Variáveis controladas:

- versão e checksum de YuNet e SFace;
- resolução e origem da câmera;
- implementação do alinhamento;
- composição da galeria;
- versão do código e configuração completa.

## Dados e separação

1. Obter consentimento explícito de cada participante.
2. Criar sessões independentes para cadastro, calibração e teste final.
3. Não extrair vários quadros adjacentes de um mesmo vídeo para lados diferentes da divisão.
4. Produzir comparações genuínas e impostoras rotuladas.
5. Não armazenar imagens ou embeddings no arquivo de análise. O CSV contém somente métricas.
6. Congelar os limiares após a calibração e antes do teste final.
7. Relatar número de pessoas, sessões, comparações e distribuição das condições; não ocultar o
   tamanho reduzido da amostra.

## Métricas

- **GAR/TAR:** proporção das tentativas genuínas aceitas;
- **FAR:** proporção das tentativas impostoras aceitas;
- **FRR:** proporção das tentativas genuínas não aceitas, incluindo baixa qualidade;
- **cobertura:** proporção das observações que ultrapassa o filtro de qualidade;
- **precisão:** proporção das aceitações que é genuína, quando houver aceitações;
- **acurácia balanceada:** média entre GAR e taxa de rejeição verdadeira;
- **latência média:** tempo de processamento observado, relatado junto ao hardware e à carga.

Acurácia isolada não deve orientar a escolha porque pode esconder desbalanceamento entre tentativas
genuínas e impostoras.

## Experimento E-001 — Grade de limiares

1. Preencher um CSV com as colunas:

   ```csv
   similarity,is_genuine,quality_score,processing_time_ms
   ```

2. Usar identificadores pseudônimos apenas no controle externo da coleta; eles não entram no CSV.
3. Executar:

   ```powershell
   uv run face-access-calibrate docs/examples/calibration_observations.example.csv `
     --output artifacts/calibration-grid.csv `
     --max-far 0.01 `
     --min-coverage 0.80
   ```

4. O arquivo em `docs/examples` é sintético e serve apenas para verificar a ferramenta.
5. Comparar todos os pontos, não somente o candidato sugerido automaticamente.
6. Repetir a análise por condição de captura antes de agregar os resultados.

O módulo `face_access.research` considera observações abaixo da qualidade mínima como não aceitas,
mas também as contabiliza como adiadas para preservar a medida de cobertura.

## Critério para o artigo

Um limiar só pode ser chamado de “selecionado” depois do conjunto de calibração. No conjunto final,
o texto deve informar intervalos, contagens e limitações. Os números do OpenCV ou dos artigos são
referências externas, não resultados deste protótipo.

## Ameaças à validade

- poucas identidades ou baixa diversidade demográfica;
- dependência de uma única câmera e ambiente;
- correlação entre quadros consecutivos;
- ajuste excessivo ao próprio conjunto de teste;
- ausência de prova de vida e ataques de apresentação;
- Laplaciano como aproximação imperfeita de nitidez;
- latência de computador não transferível diretamente para tablet Android.
