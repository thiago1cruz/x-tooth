# X-TOOTH

Ferramenta de auxílio ao diagnóstico de lesões endo-periodontais em radiografias periapicais. Este repositório contém o componente de treinamento e seleção de modelo: comparação de arquiteturas de redes neurais profundas (transfer learning) para a classificação multiclasse das lesões.

Trabalho de Conclusão de Curso — Bacharelado em Ciência da Computação, IFMA Campus Caxias.
Autor: **Thiago da Cruz de Araujo**

A descrição completa da metodologia, das decisões experimentais e dos resultados está no texto do TCC.

## Dataset

Base pública de 544 radiografias periapicais em 5 classes, distribuída no Kaggle:
[`muhammadsajad/periapical-xrays`](https://www.kaggle.com/datasets/muhammadsajad/periapical-xrays)

O dataset não é redistribuído neste repositório — o script o baixa automaticamente via `kagglehub`.

## Estrutura

```
x-tooth/
└── training/   # treinamento e seleção de modelo
    ├── xtooth_v4_colab.py
    └── requirements.txt
```

## Como executar

1. Abra o [Google Colab](https://colab.research.google.com) e selecione um runtime com GPU.
2. Cole o conteúdo de `training/xtooth_v4_colab.py` em uma célula e execute.
3. Ao final, um `.zip` com todos os resultados (logs, métricas, gráficos, modelo treinado) é baixado automaticamente.

## Saídas

```
results/xtooth_v4_<timestamp>/
├── logs/            # log de execução, ambiente, índices da partição
├── data_dictionary/ # dicionário de dados e distribuição de classes
├── cv/              # validação cruzada e comparação de modelos
├── hpo/             # otimização de hiperparâmetros (Optuna)
├── final/           # modelo final, matriz de confusão, ROC, relatórios
├── gradcam/         # mapas de explicabilidade (Grad-CAM)
├── errors/          # predições e tabela de erros do teste
└── final_report.json
```

## Licença

MIT — ver [LICENSE](LICENSE).

## Como citar

```
ARAUJO, Thiago da Cruz de. X-TOOTH: protocolo experimental para classificação de
lesões endo-periodontais em radiografias periapicais. 2026.
Disponível em: https://github.com/thiago1cruz/x-tooth.
```
