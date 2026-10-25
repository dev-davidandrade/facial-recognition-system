# Diário de pesquisa

Este arquivo registra hipóteses, decisões e resultados do laboratório. Ele não representa uma
validação para controle de acesso físico. O sistema é uma base de estudo e portfólio destinada a
experimentos locais consentidos.

## 2026-10-23 — Qualidade do cadastro e qualidade da consulta são assimétricas

### Pergunta

Uma referência extremamente nítida prejudica a comparação quando a consulta futura vem de uma
câmera com chuva, reflexo, pouca luz ou movimento?

### Descoberta conceitual

Não há benefício em degradar artificialmente a imagem de cadastro. O SFace compara embeddings, não
pixels equivalentes. Uma referência bem definida oferece uma estimativa mais estável da identidade,
mas não recupera informações que desapareceram na consulta ruim. Portanto:

- cadastro nítido tende a melhorar a estabilidade da referência;
- consulta degradada ainda pode reduzir a similaridade;
- similaridade cosseno não é probabilidade nem “porcentagem de certeza”;
- confiança do detector, qualidade da imagem e similaridade biométrica são variáveis distintas;
- vários quadros consistentes podem compensar falhas ocasionais, mas não tornam útil um quadro sem
  informação facial suficiente.

### Hipóteses testáveis

- **H1:** templates obtidos de quadros mais nítidos aumentam a média da similaridade genuína e
  reduzem sua variância.
- **H2:** uma política de qualidade mais rigorosa no cadastro e mais tolerante na consulta oferece
  melhor compromisso entre cobertura e falsa rejeição que um único limite global.
- **H3:** confirmação temporal reduz decisões instáveis em consultas degradadas sem exigir que todos
  os quadros sejam aceitos.

### Decisão atual

- não criar templates deliberadamente borrados;
- manter múltiplas referências boas com pequenas variações de pose e iluminação;
- tratar `0,50` de similaridade, `60` de nitidez e `3/5` confirmações apenas como baselines;
- descartar amostras ruins individualmente no cadastro, persistindo o lote somente quando restarem
  pelo menos duas válidas;
- não afirmar precisão, robustez à chuva ou adequação a cancelas antes de executar o protocolo.

### Limitação observada

O protótipo ainda usa o mesmo limiar de nitidez na matrícula e na consulta. Separar essas políticas
é uma hipótese de pesquisa, não uma alteração que deva ser feita antes de medir os dados.

### Próximo experimento

Executar `E-001`, descrito em [RESEARCH_METHOD.md](RESEARCH_METHOD.md), comparando limiares de
similaridade e qualidade em capturas separadas por sessão.

## Modelo para novas entradas

```text
Data e identificador:
Pergunta:
Hipótese:
Configuração e versão dos modelos:
Dados e separação das sessões:
Variáveis controladas:
Resultado bruto:
Interpretação:
Ameaças à validade:
Decisão e próximo teste:
```
