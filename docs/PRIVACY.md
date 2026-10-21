# Privacidade

## Finalidade e base de dados

Este laboratório trata dados faciais somente para experimentação consentida de reconhecimento em
controle de acesso. Nenhuma imagem deve ser coletada sem finalidade clara e consentimento
documentado. A adequação à LGPD e a outras normas aplicáveis deve ser avaliada por responsável
qualificado antes de qualquer implantação.

## Minimização

- imagens são processadas em memória e descartadas por padrão;
- respostas e logs nunca contêm imagens ou embeddings;
- eventos guardam decisão, métricas necessárias, versão e correlação;
- `display_name` é opcional; prefira identificadores internos pseudonimizados;
- datasets, imagens e artefatos biométricos ficam fora do Git.

## Ciclo de vida

O consentimento tem data e versão. Revogação deve desativar todos os templates da pessoa. Uma
solicitação de exclusão deve remover templates e apagar ou anonimizar dados relacionáveis conforme
uma política de retenção documentada. O prazo ainda não foi definido e bloqueia uso real.

O endpoint `DELETE` atual executa revogação lógica e desativa templates; ele ainda não satisfaz,
sozinho, uma solicitação de eliminação definitiva.

## Separação experimental

Cadastro, calibração, teste final e teste externo devem usar capturas separadas. Dados de qualquer
ambiente corporativo não podem ser copiados para este repositório pessoal.
