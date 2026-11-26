# Especificação de Comissionamento — Dom Rock

## base-rh — Base de RH
Lista com todos os funcionários da empresa no período analisado. Campos:
a) Date_Ref – data competência do processamento
b) Cod_Marca – código da marca
c) Descr_Marca – descrição da marca
d) Cod_Loja – código da loja
e) Descr_Loja - nome loja
f) Matricula – código do funcionário
g) Data Admiss – data de admissão do funcionário
h) Data_Demiss – data de demissão do funcionário
i) Cod_Cargo – código do cargo
j) Descr_Cargo – nome do cargo

## base-vendas — Base de Vendas
Resumo das vendas do mês. Campos:
a) Date_Ref – data competência
b) Cod_Marca – código da marca
c) Descr_Marca – descrição da marca
d) Cod_Loja – código da loja
e) Descr_Loja - nome loja
f) Matricula – código do funcionário
g) Vlr _Venda – Valor das vendas individuais

## base-comissionamento — Base de Comissionamento
Percentual de comissionamento por cargo e marca. Campos:
a) Cod_Marca – código da marca
b) Descr_Marca – descrição da marca
c) Cod_Cargo – código do cargo
d) Descri_Cargo – nome do cargo
e) %_Comiss - % de comissionamento por cargo e por marca

## 1 — Competência
O processamento deve ser realizado respeitando a data de competência de cada base: Ex: Base RH mês1 com base de Vendas mês1.

## 2 — Vendas individuais
Relacionar a “Base de Vendas” com a “Base de RH” considerando a matrícula de cada funcionário – objetivo: obter as vendas individuais por funcionário.

## 3 — Vendas consolidadas
Relacionar a “Base de Vendas” com a “Base de RH” considerando o cod_loja – objetivo: obter as vendas consolidadas por loja.

## 4 — Consolidação mensal
Consolidar as vendas mensais dos funcionários por Matrícula e consolidar as vendas das lojas pelo Cod_Loja.

## 5a — Geral
Aplicar o respectivo % de comissionamento do arquivo “Base de Comissionamento” a cada funcionário considerando: a Matrícula, o Cod_Marca e o Cod_Cargo.

## 5b — Gerente
Para o código de cargo Gerente (150) a aplicação do % de comissionamento se dará pela venda total da loja apurada pela soma de todos os funcionários existente em cada loja, inclusive o gerente.

## 5c — Admissão
Caso algum funcionário seja admitido no mês de competência (Data_Admiss) o seu comissionamento será calculado proporcionalmente aos dias trabalhados, sendo que para os gerentes se aplica a mesma regra, porém a proporcionalidade do valor de comissionamento se dará em cima da venda total da loja. Ex: Admitido no dia 10 de outubro. Comissionamento = Vlr Apurado de comissionamento dividido por 31 (qtde dias do mês de outubro) e multiplicado por 21 (31-10=dias efetivamente trabalhados).

## 5d — Demissão
Caso algum funcionário seja demitido no mês de competência (Data_Demiss) o seu comissionamento será calculado proporcionalmente aos dias trabalhados, sendo que para os gerentes se aplica a mesma regra, porém a proporcionalidade do valor de comissionamento se dará tbm pela venda total da loja. Ex: demitido no dia 10 de novembro. Comissionamento = Vlr Apurado de comissionamento dividido por 30 (qtde dias do mês de novembro) e multiplicado por 10 (dias efetivamente trabalhados).

## 5e — Afastamento menor que 15 dias
Funcionário afastado por atestado por um período menor que 15 dias terá direito a receber comissionamento proporcional as suas vendas no período trabalhado ou um valor fixo de R$3.500, dos 2 o maior. Para os gerentes se aplica a mesma regra, porém a proporcionalidade do valor de comissionamento se dará pela vlr de venda total da loja. Ex: funcionário afastado por 10 dias – venda de R$20.000 mil no mês. Sua base de comissionamento adicional será de R$10.000, ou seja 20.000 dividido por 20 (qtde de dias trabalhado) x 10 dias de afastamento.

## 5f — Afastamento maior que 15 dias
Funcionário afastado por um período maior que 15 dias terá direito a receber comissionamento proporcional as suas vendas somente por 15 dias de afastamento ou um valor fixo de R$3.500 dos 2 o maior. O restante dos dias não terá direito a nenhuma remuneração. Para os gerentes, se aplica a mesma regra, porém a proporcionalidade se dará pel valor total de venda da loja. Ex: funcionário afastado por 20 dias – venda de R$8.000 mil no mês. Sua base de comissionamento adicional será de R$12.000, ou seja 8.000 dividido por 10 (30dias -20dias = qtde de dias trabalhado) x 15 dias de afastamento por lei.

## 5g — Férias
Funcionários em férias não terão direito a remuneração nos dias de gozo de férias, sendo que para os gerentes se aplica a mesma regra, porém a proporcionalidade do valor de comissionamento se dará pela valor da venda total da loja.

## 2h — Campanha agosto marca 10 cargo 300
Somente para este mês, o % de comissionamento da marca 10 no cargo 300 subiu para 1,75%.

## 3g — Campanha setembro marca 20 na marca 10
Somente para este mês, o % de comissionamento da marca 20 será aplicada em todos os cargos da marca 10.

## 4g — Campanha outubro marca 30
Os funcionários da marca 30 tiveram um acréscimo de 0,5% no % de comissionamento já existente para todas as vendas realizadas no mês. Este bônus não se aplica aos cargos de gerente.

## 6f — Campanha dezembro marcas 40 50 e 60
Todas as vendas das marcas 40, 50 e 60 terão um acréscimo no % de comissionamento de +1%. Valido para todos os cargos, com exceção dos gerentes (150).

## 6g — Campanha dezembro marca 30
Todas as vendas da marca 30 terão um acréscimo de +0,5% no seu comissionamento. Valido para todos os cargos, com exceção dos gerentes (150).
