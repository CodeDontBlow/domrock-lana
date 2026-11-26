# Glossário de Cargos, Marcas e Planilhas do Dataset Dom Rock

## cargo-100 — Cargo 100: Vendedor Loja

O código de cargo 100 corresponde à função de Vendedor Loja no catálogo de cargos da organização. Os profissionais alocados sob esta categoria atuam diretamente no atendimento presencial ao consumidor e na comercialização de mercadorias no salão de vendas das lojas físicas da rede. A apuração de sua remuneração variável fundamenta-se nas transações individuais de vendas associadas à sua matrícula cadastral e às marcas comercializadas no período de competência.

## cargo-150 — Cargo 150: Gerente (Gerente de Loja e Gerente Quiosque)

O código de cargo 150 abrange as funções de liderança de unidades comerciais, englobando tanto o Gerente de Loja quanto o Gerente Quiosque. Conforme as diretrizes corporativas da organização, ambos os perfis compartilham a mesma regra de negócio e os mesmos critérios de elegibilidade para comissionamento, diferenciando-se operacionalmente pelo volume médio de vendas de cada ponto de atendimento. O cálculo da remuneração variável para o cargo 150 incide sobre o faturamento total consolidado da respectiva unidade física, apurado a partir do somatório das vendas realizadas por todos os colaboradores da equipe e pelo próprio gestor.

## cargo-200 — Cargo 200: Vendedor Balcão

O código de cargo 200 identifica a ocupação de Vendedor Balcão nas unidades de varejo da empresa. Os colaboradores enquadrados nesta categoria exercem atividades de atendimento especializado, suporte comercial direto e efetivação de pedidos no balcão de vendas das unidades físicas. Sua remuneração variável é calculada aplicando-se as alíquotas contratuais sobre as vendas individuais diretas registradas para cada marca ao longo da competência mensal.

## cargo-300 — Cargo 300: Assistente de Vendas

O código de cargo 300 refere-se à função de Assistente de Vendas no quadro funcional da empresa. Esta categoria engloba colaboradores responsáveis pelo apoio às rotinas operacionais e comerciais das unidades, fornecendo suporte auxiliar aos clientes e aos vendedores titulares no salão ou no balcão. A participação dessa função nas campanhas e na apuração de comissões obedece aos percentuais e metas fixados especificamente para a função nas matrizes de parâmetros vigentes.

## marca-10 — Marca 10: PRETO

O código numérico 10 identifica a marca PRETO no catálogo de produtos e divisões de negócio da empresa. Nas bases transacionais de vendas e nas tabelas de recursos humanos, esse código funciona como chave de agrupamento primária das mercadorias vendidas, permitindo categorizar o faturamento das unidades físicas e direcionar as alíquotas de comissionamento padrão ou os eventuais acréscimos promocionais instituídos para essa linha de produtos.

## marca-20 — Marca 20: BRANCO

O código numérico 20 designa a marca BRANCO no portfólio comercial da companhia. Representa uma família de mercadorias específica comercializada nos pontos de atendimento físicos, servindo de indexador nas bases operacionais para mensurar o volume financeiro transacionado e para determinar os índices contratuais de incentivo aplicáveis aos cargos elegíveis em cada período apurado.

## marca-30 — Marca 30: AZUL

O código numérico 30 corresponde à marca AZUL na estrutura mercadológica da empresa. Essa identificação é utilizada de modo sistemático nas movimentações de faturamento e nas matrizes de parâmetros para individualizar os itens vendidos, viabilizando o cálculo parametrizado das comissões devidas às equipes e o acompanhamento analítico do desempenho de mercado dessa linha de artigos.

## marca-40 — Marca 40: VERMELHO

O código numérico 40 representa a marca VERMELHO no ecossistema comercial da organização. Este identificador associa os registros transacionais das lojas a esse departamento de produtos, possibilitando a aplicação de filtros de elegibilidade em campanhas de incentivo temporário e o cômputo exato das parcelas de remuneração variável calculadas para os vendedores participantes.

## marca-50 — Marca 50: AMARELO

O código numérico 50 refere-se à marca AMARELO dentro do catálogo de marcas operadas pela rede varejista. Atua como classificador padronizado nos registros de vendas e nos parâmetros de remuneração, permitindo o acompanhamento de metas financeiras e a correta aplicação das alíquotas de comissão vigentes sobre as transações faturadas sob essa denominação.

## marca-60 — Marca 60: CINZA

O código numérico 60 caracteriza a marca CINZA no portfólio de produtos comercializados pela organização. O código atua como atributo categórico em todo o ciclo de processamento de dados, desde o registro da transação individual no ponto de venda até a apuração dos valores consolidados de comissionamento nos relatórios de fechamento mensal.

## planilha-base-commiss-final — Planilha BASE_COMMISS_FINAL (Base de Comissionamento)

A planilha BASE_COMMISS_FINAL armazena a matriz padrão de parâmetros de comissionamento da organização por combinação de marca e cargo profissional. A coluna Cod_Marca registra o identificador numérico da marca de produtos, acompanhada pela coluna Descr_Marca, que informa a denominação textual correspondente. A coluna Cod_Cargo indica o código numérico da função, enquanto Descri_Cargo traz a nomenclatura formal do cargo. A coluna %_Comiss estipula a taxa percentual de comissão padrão contratualmente prevista para os ocupantes daquele cargo sobre as vendas líquidas da respectiva marca, servindo como base standard de cálculo antes da aplicação de eventuais regras promocionais de campanha.

## planilha-base-rh — Planilha BASE RH (Cadastro e Headcount de Funcionários)

As planilhas da família BASE RH consolidam o cadastro de pessoal e o headcount de colaboradores para as competências mensais de julho a dezembro de 2025. A coluna Data_Ref indica o mês de competência do processamento. As colunas Cod_Marca e Descri_Marca identificam o código e a descrição da marca prioritária associada ao colaborador. As colunas Cod_Loja e Descr_Loja detalham o identificador e a denominação da unidade física de lotação. A coluna Matricula representa o identificador cadastral individual de cada funcionário. As colunas Data_Admiss e Data_Demiss indicam as datas de admissão e de rescisão contratual, sendo empregadas para calcular a proporcionalidade de dias efetivamente trabalhados no mês de entrada ou saída. As colunas Cod_Cargo e Descri_Cargo definem o código e a função exercida. No arquivo de setembro de 2025, a coluna adicional VENDAS R$ registra o volume monetário total faturado pelo colaborador para fins de conciliação interna.

## planilha-base-vendas — Planilha BASE_VENDAS (Registro de Transações Comerciais)

As planilhas da família BASE_VENDAS compilam todas as transações de venda realizadas pela rede física ao longo das competências mensais de julho a dezembro de 2025. A coluna Date_Ref estabelece a data ou período de competência em que o negócio foi efetuado. As colunas Cod_Marca e Descr_Marca indicam o código e a descrição da marca da mercadoria transacionada. As colunas Cod_Loja e Descr_Loja registram o identificador e o nome da loja ou quiosque onde a operação foi concluída. A coluna Matricula informa a identificação do vendedor responsável pelo atendimento, conectando o registro de venda ao respectivo funcionário na base de recursos humanos. A coluna Vlr _Venda registra o montante monetário de cada operação individual, fornecendo a base financeira necessária para a apuração da comissão individual dos vendedores ou para a composição do faturamento global da loja para comissionamento dos gerentes.
