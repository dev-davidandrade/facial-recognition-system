# Base bibliográfica inicial

Esta revisão é incremental. Cada fonte deve sustentar uma afirmação específica; valores publicados
não são transferidos automaticamente para o nosso ambiente.

## SFace

Zhong et al. apresentam uma função de perda que controla as distâncias intra e interclasse em uma
hiperesfera e avaliam modelos em benchmarks públicos. Isso fundamenta o uso de embeddings e
similaridade, mas não transforma similaridade cosseno em probabilidade de identidade e não valida o
nosso limiar local. Fonte primária: [IEEE, DOI 10.1109/TIP.2020.3048632](https://doi.org/10.1109/TIP.2020.3048632).

## YuNet

Wu, Peng e Yu descrevem o YuNet como detector leve voltado a dispositivos de borda e apresentam o
compromisso entre tamanho, velocidade e detecção. As latências publicadas dependem do hardware e da
resolução e não devem ser atribuídas ao nosso computador sem medição. Fonte primária:
[Machine Intelligence Research, DOI 10.1007/s11633-023-1423-y](https://doi.org/10.1007/s11633-023-1423-y).

## Implementação de referência do OpenCV

O tutorial oficial do OpenCV publica limiares diferentes para conjuntos como LFW, CALFW, CPLFW,
AgeDB-30 e CFP-FP. Essa variação reforça que não existe um valor universal para SFace e que o nosso
`0,50` precisa de calibração representativa. Fonte técnica primária:
[OpenCV — DNN-based Face Detection and Recognition](https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html).

O repositório oficial também registra versões, benchmarks e a origem do YuNet utilizado:
[OpenCV Zoo — YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet).

## Pendências da revisão

- qualidade facial e relação entre qualidade e utilidade biométrica;
- reconhecimento sob chuva, vidro, reflexo e pouca luz;
- fusão temporal de escores e seleção de quadros;
- métricas e protocolos de avaliação biométrica;
- vieses demográficos, privacidade e ataques de apresentação.

As referências em formato BibTeX ficam em [references.bib](references.bib).
