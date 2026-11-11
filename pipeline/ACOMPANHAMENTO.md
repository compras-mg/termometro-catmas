# Acompanhamento das probabilidades CATMAS

O atualizador passa a publicar `dados.json.gz` e `acompanhamento.json.gz` no
mesmo commit. A página `acompanhamento.html` calcula Brier, previsto × realizado,
calibração por faixa e recortes por tipo e mês de entrada. Cada linha representa
um ciclo de uma demanda; reenvios após resposta são ciclos separados.

## Instalar no Windows

1. Extraia o ZIP de atualização em uma pasta separada, por exemplo
   `Downloads/CATMAS-Termometro-acompanhamento`.
2. Execute com o Python existente do uv:

```powershell
& "$env:USERPROFILE\.local\bin\uv.exe" run --python 3.12 --no-project --script "$env:USERPROFILE\Downloads\CATMAS-Termometro-acompanhamento\INSTALAR-ACOMPANHAMENTO.py"
```

O instalador verifica os arquivos e o modelo instalados contra o manifesto
anterior recebido, adquire a mesma trava da extração, cria backup e altera
somente `atualizar.py`, `acompanhamento.py` e `integridade.json`. Em falha de
gravação restaura os arquivos. Se a instalação já tiver mudanças diferentes,
interrompe sem sobrescrevê-las. O parâmetro `--destino` permite outro diretório.
Não altera tarefas, variáveis, consultas SQL ou modelo, nem faz extrações.

3. Execute a atualização normal:

```powershell
Set-Location "$env:USERPROFILE\OneDrive - CAMG\Documentos\CATMAS-Termometro"
& "$env:USERPROFILE\.local\bin\uv.exe" run --python 3.12 --script .\atualizar.py --publicar
```

A tarefa existente usa o mesmo atualizador e passa a gerar o acompanhamento.
Os arquivos de interface e demais arquivos do repositório não são substituídos
pelo publicador. O modelo `modelo.joblib` já instalado é necessário e não está
incluído neste pacote. Carregue somente o modelo original de origem confiável.

## Definição da medida

Erro por ciclo: `(p - y) ** 2`, onde `p` está entre 0 e 1 e `y` é 1 para
resposta no prazo, 0 para resposta fora do prazo ou aberto já atrasado. Brier
é a média desses erros nos ciclos avaliáveis; não é percentual de acertos.
Uma previsão de 0,85 gera 0,0225 se `y=1` e 0,7225 se `y=0`.

Pendentes, retiradas, respostas inferidas na geração de código e inconsistências
de pausa ficam fora das médias. A apuração usa `preparar_indicadores.resultado`,
com suas regras existentes de calendário e pausas. Não recalcula prazos no
navegador. A referência é o corte observado da extração, não o relógio do PC.
O denominador de previsto e realizado é sempre o mesmo conjunto avaliável.
Períodos recentes têm viés de maturação: respostas rápidas aparecem antes dos
atrasos. O painel mostra pendentes/excluídos para explicitar essa limitação.

## Origem e congelamento

Os atributos vêm de `atributos_na_entrada.jsonl`, projetados exclusivamente nos
campos exigidos pelo modelo. Resultados, pausas futuras e identificação não são
passados à inferência. A probabilidade por ciclo não é copiada do cartão atual,
que simula uma primeira entrada na data de referência.

A retrospectiva usa o modelo atual e somente entradas desde 01/01/2026,
após o treino e calibração documentados. Ela não afirma que as previsões foram
emitidas no passado. O hash do modelo é verificado; um modelo novo exige
revisão explícita do corte de avaliação para evitar vazamento de treino.

`registrada_sem_resultado` significa que o resultado era indeterminado na
extração da primeira publicação. Não é garantia de previsão em tempo real:
registro pode ocorrer depois da entrada e a origem pode estar atrasada.
`registrada_em` é UTC; datas de negócio preservam o formato e fuso não confirmado
da origem. O painel não inventa uma conversão entre esses relógios.

O arquivo publicado funciona como registro persistente. Antes de publicar, o
atualizador lê a versão mais recente do GitHub e mantém probabilidade, versão
do modelo, hash dos atributos e data da primeira publicação. A identidade usa
demanda, evento de entrada e instante de entrada; não depende apenas do número
de sequência do ciclo. Alterações da apuração são sinalizadas. Ciclos que somem
da extração são preservados, mas excluídos das médias até reaparecerem.
Novos eventos de entrada corrigidos podem aparecer como nova identidade, com
a anterior marcada ausente. Não há exclusão silenciosa do registro anterior.

Sem push confirmado não há previsão registrada no acompanhamento remoto.
O push nunca usa force: concorrência rejeita o envio. O lote local permanece
para diagnóstico; executar novamente faz uma extração nova e reconcilia com
a versão remota. A primeira execução pode levar mais tempo para pontuar todos
os ciclos desde 2026. Não há retreinamento.

## Validação e limites da entrega

Testes cobrem scores binários, pendentes, exclusões, congelamento, revisão,
ausência de ciclos, corte pós-treino, separação de atributos, duplicidade,
referência regressiva, filtros, CSV e publicação conjunta. O modelo treinado e
a conexão ao Impala ficam no Windows; a primeira carga real desta versão deve
ser executada lá. Nenhum dado sintético deve ser publicado como resultado real.

Referência: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html
