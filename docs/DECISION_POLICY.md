# Política de decisão

## Separação obrigatória

1. O pipeline biométrico produz `identified`, `unknown`, `ambiguous`, `no_face`,
   `multiple_faces`, `low_quality`, `spoof_suspected` ou `processing_error`.
2. Uma `AuthorizationPolicy` avalia esse resultado junto ao estado da pessoa e produz
   `access_granted`, `access_denied` ou `manual_review`.

Uma similaridade alta não concede acesso por si só. Pessoa inativa ou revogada deve ser negada
mesmo quando identificada.

## Verificação 1:1 atual

- zero rosto: `no_face`;
- mais de um: `multiple_faces`;
- rosto pequeno, desfocado ou fora da faixa de iluminação: `low_quality`;
- similaridade abaixo do limiar: `unknown`, `is_match=false`;
- similaridade igual ou acima: `identified`, `is_match=true`.

O limiar padrão `0.50` é deliberadamente provisório e serve apenas para tornar o laboratório
executável. Não representa valor universal e precisa ser substituído por configuração calibrada e
versionada. Tamanho, desfoque e iluminação também são provisórios. A estimativa de pose ainda não
está implementada.

## Identificação 1:N planejada

O melhor candidato precisa superar a similaridade mínima e manter margem mínima em relação ao
segundo. Abaixo do limiar será `unknown`; margem insuficiente será `ambiguous`. Só embeddings da
mesma versão e dimensão poderão ser comparados.

Para vídeo, nenhuma autorização ocorrerá por um único quadro. A política inicial de três
confirmações em cinco observações será apenas ponto de partida para calibração.
