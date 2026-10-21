# Model Card

## Uso pretendido

YuNet + SFace formam um baseline local para pesquisa e aprendizado. O sistema é experimental, não
foi calibrado para uma população-alvo e não está aprovado para conceder acesso físico real.

| Componente | Arquivo de referência | Origem | Licença declarada | Status local |
|---|---|---|---|---|
| Detector | `face_detection_yunet_2023mar.onnx` | OpenCV Zoo | MIT | `research_only` |
| Embedder | `face_recognition_sface_2021dec.onnx` | OpenCV Zoo | Apache-2.0 | `research_only` |

URLs exatas, hashes SHA-256 e metadados estão em `models/manifest.toml`. Os pesos não fazem parte
do repositório. `scripts/validate_models.py` rejeita checksum divergente e confirma a dimensão do
embedding SFace antes do uso.

## Procedência

O YuNet do OpenCV Zoo aponta para o repositório de treinamento `libfacedetection.train`. O SFace é
uma conversão de uma instância MobileFaceNet treinada com a loss SFace, mas a procedência exata do
dataset usado para o peso distribuído não está suficientemente documentada para aprovação
comercial. Uma licença de arquivo não resolve, sozinha, direitos derivados dos dados de treino.

## Limitações conhecidas

- ausência de vivacidade: foto, tela e replay podem funcionar como ataque;
- qualidade cobre tamanho, desfoque e iluminação, mas pose ainda não é estimada;
- limiares atuais são provisórios e não transferíveis entre modelos ou populações;
- desempenho e vieses demográficos não foram medidos neste projeto;
- sem garantia sob oclusão, pose extrema, iluminação severa ou envelhecimento;
- identificação 1:N e rejeição de desconhecidos ainda não foram implementadas.

## Avaliação necessária

Antes de promoção de um modelo, registrar versão, hash, dimensão, licença, procedência, população,
FAR, FRR, EER, TAR em FAR definidos, ROC, rank-1, rejeição de desconhecidos, latência p50/p95,
condições ambientais e análise por grupos relevantes. O limiar deve ser calibrado apenas na
validação e congelado antes do teste final.
