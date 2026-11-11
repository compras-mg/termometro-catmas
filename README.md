# Termômetro CATMAS

Página experimental de carga e expectativa de atendimento do CATMAS de Minas Gerais.

Site estático: index.html, style.css, app.js e dados.json.gz. GitHub Pages: branch main, pasta raiz. Os dados comprimidos são abertos pelo navegador com DecompressionStream.

Inclui velocímetro experimental por tipo, bandeira de carga, histórico mensal e consulta por número. A consulta omite posição quando cadastro e histórico divergem. Não há nomes, textos livres ou credenciais.

O modelo ainda não superou a média histórica por tipo. As faixas da bandeira são provisórias. A metodologia e limitações estão descritas na página.

Snapshot: último evento observado em 28/10/2026. Atualização automática Windows às 06:00 e 12:30 (America/Sao_Paulo) ainda em implantação. Não representa tempo real.


## Previsto × realizado

[Abrir acompanhamento](https://compras-mg.github.io/termometro-catmas/acompanhamento.html).
Erro probabilístico Brier por ciclo, tipo e mês; filtros, calibração e exportação CSV.
Previsões retrospectivas são separadas das registradas sem resultado observado.
A primeira carga depende da instalação do atualizador em Windows.

[Instalação e definição da medida](pipeline/ACOMPANHAMENTO.md).
O diretório pipeline contém a atualização incremental; depende dos demais scripts
e do modelo original já instalados no Windows. Não é um pacote completo de extração.

Testes sem Impala ou modelo treinado:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node tests/avaliacao-metricas.test.mjs
```

