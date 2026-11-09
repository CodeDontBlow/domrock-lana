# A6-77 — Apuração completa (regras 5c a 5g)

As regras vêm do item 5 do `Especificacao.pdf` e dos cenários da US 21
(`domrock-camplana/docs/backlogs/sprint-3/gherkin.md#us21`). Onde o texto da especificação
deixa dúvida, seguimos a leitura do Synapse (`projetos_ref/synapse/docs/decisoes/dec-090.md`),
que trata a mesma especificação. Este documento explica as decisões e onde cada parte está no
código.

## Onde está

- `app/simulacao/regras_base.py`: uma função por regra; o resultado é um ajuste por matrícula e
  competência (`AjusteMatricula`: fator, `zera`, `aplica_piso` e o texto de cada regra).
- `app/simulacao/service.py` (`_aplicar_regras_base`): aplica o mesmo ajuste à comissão atual
  (`comissao`) e à comissão com campanha (`comissao_simulada`), **depois** do código gerado e das
  asserções dele. O código gerado pela IA não muda e o prompt avisa para não aplicar essas regras.
- `app/simulacao/por_pessoa.py`: monta `apuracao_por_pessoa` no resultado.

## As regras

| Regra | Fator sobre a comissão do mês | Exemplo da especificação |
| :-- | :-- | :-- |
| 5c Admissão no mês | `(dias_mes - dia_admissao) / dias_mes` | admitido em 10/10: 3.100 ÷ 31 × 21 = 2.100 |
| 5d Demissão no mês | `dia_demissao / dias_mes` | demitido em 10/11: 3.000 ÷ 30 × 10 = 1.000 |
| 5c + 5d no mesmo mês | `(dia_demissao - dia_admissao) / dias_mes` | — |
| 5g Férias | `(dias_mes - dias_de_ferias) / dias_mes` | 10 dias em outubro: 21/31 |
| 5e Afastamento até 15 dias | `(trabalhados + remunerados) / trabalhados` | 10 de 30 dias: base 20.000 → 30.000 (10.000 adicionais) |
| 5f Afastamento acima de 15 dias | igual, só os 15 primeiros dias remunerados | 20 de 30 dias: base 8.000 → 20.000 (12.000 adicionais) |

- **Ordem:** comissão × fator de vínculo × fator de férias × fator de afastamento, arredondada
  com duas casas (meia para par). Só depois entra o piso.
- **Piso de R$ 3.500 (5e e 5f):** quando há dia de afastamento remunerado, a pessoa recebe o maior
  valor entre a comissão já projetada (dias trabalhados mais os remunerados) e R$ 3.500. É a
  leitura do Synapse: o fixo concorre com a comissão total do mês, não só com a parte adicional.
  Afastado o mês inteiro: comissão 0 e, com dias remunerados, recebe o piso.
- **Gerente (cargo 150):** a comissão dele já vem da venda total da loja (5b), então o fator
  incide sobre essa venda, como a especificação pede.
- **Datas:** `data_inicio` e `data_fim` das intercorrências são inclusivas. Um evento que atravessa
  meses conta, em cada competência, só os dias que caem nela. Os 15 dias remunerados contam a
  partir do início do evento (ex.: 18/08 a 08/09: 14 dias remunerados em agosto e 1 em setembro).
- **Tipos de intercorrência** (`evento_rh`): `licenca_maternidade` segue o afastamento (dec-090);
  `demissao` corrige a data de demissão do RH só em memória (ex.: MATRIC-62); `cobertura_loja`
  ainda não entra.

## Limites conhecidos

- **Admissão no dia 1:** pela fórmula literal (31 − 1 = 30), quem foi admitido no dia 1 recebe
  30/31 do mês. Em out/2025 são 8 pessoas. Seguimos a especificação e o Synapse.
- As intercorrências chegam vazias por padrão (`BasesSimulacao.intercorrencias`). Carregá-las do
  banco, só as aprovadas, é a tarefa A6-108. Até lá, só a 5c e a 5d mudam números reais: em
  nov/2025, 15 admissões levam a comissão atual de R$ 480.263,24 para R$ 477.643,36 e o custo
  da Black Friday +1% de R$ 23.736,10 para R$ 23.569,11.

## Resultado por pessoa (`apuracao_por_pessoa`, aditivo no resultado 2.3)

Uma linha por matrícula e competência, ordenada por matrícula. Exemplo com o cenário 5c da
US 21 (comissão de R$ 3.100 sem proporção, admissão em 10/10), fora do período da campanha:

```json
{
  "matricula": "MATRIC-30", "competencia": "2025-10", "cod_loja": "5", "cod_marca": "10",
  "cod_cargo": "100", "base_calculo": 155000.0, "pct_comiss": 2.0,
  "detalhamento": [
    {"regra": "5a", "descricao": "5a — % da base: 2%"},
    {"regra": "5c", "descricao": "5c — admissão em 10/10: 21 de 31 dias"}
  ],
  "comissao_atual": 2100.0, "comissao_com_campanha": 2100.0
}
```

- `base_calculo` e `pct_comiss` são os da 5a/5b, antes dos ajustes.
- `comissao_atual` e `comissao_com_campanha` são finais. A soma de cada coluna bate com
  `totais.baseline` e `totais.simulado`.
- `regra` vale `5a`, `5b`, `5c`, `5d`, `5e`, `5f`, `5g` ou `piso`. A entrada `piso` diz qual dos
  dois valores venceu, calculado sobre a comissão com campanha.
- O campo não vai para a LLM (`CAMPOS_EXPLICACAO`).
