# Esclarecimentos da Dom Rock sobre Regras de Negócio e Operação

## atualizacao-mensal-bases — Atualização mensal das bases de dados

As bases de dados do sistema, compreendendo o cadastro de funcionários da organização e as movimentações transacionais de vendas, passam por atualizações com periodicidade ordinariamente mensal. No ambiente operacional ou em etapas de homologação, esse fornecimento ocorre por meio de rotinas periódicas de integração sistêmica ou mediante o carregamento manual de um novo arquivo consolidado referente ao mês de competência da apuração.

## correcao-dados-pre-processamento — Correção de dados operacionais antes do processamento

O sistema deve disponibilizar aos usuários uma funcionalidade ágil e direta para efetuar correções pontuais em registros das bases antes da execução do processamento de comissionamento. Esse recurso viabiliza o ajuste de inconsistências cadastrais ou alocações divergentes, a exemplo de vendedores vinculados temporariamente a lojas incorretas, além de refletir situações de afastamento laboral, tais como concessão de férias, licenças médicas ou licença-maternidade.

## alteracao-base-comissao-aprovacao — Alteração da base de comissão padrão por pipeline de aprovação

A tabela de comissionamento padrão disponibilizada no sistema é regida por governança estrita e não pode ser modificada de maneira direta pelos usuários. Qualquer proposta de alteração nos parâmetros ou alíquotas da base standard deve tramitar obrigatoriamente por um pipeline formal de aprovação, respeitando a cadeia hierárquica estabelecida pela organização para validar, homologar e formalizar a nova regra de negócio.

## rastreabilidade-auditoria — Rastreabilidade de alterações para auditoria

Todas as alterações efetuadas nas bases de dados, regras de remuneração variável e aprovações concedidas no fluxo de trabalho devem ser integralmente registradas e mantidas pelo sistema. O histórico dessas operações fornece trilhas completas de auditoria e evidências comprobatórias necessárias para atender a eventuais ciclos de conformidade, fiscalização e governança corporativa da empresa.

## foco-apuracao-comissionamento — Prioridade no resultado da apuração de comissionamento

A finalidade central do processamento e da apresentação de relatórios e dados no sistema é entregar informações precisas sobre os resultados consolidados da apuração de comissionamento de cada competência mensal. A geração de métricas ou dados analíticos adicionais sobre variações ocorridas na base original constitui um recurso facultativo de valor agregado, mas não um requisito obrigatório para a conclusão da apuração.

## perfis-acesso-dupla-custodia — Perfis de acesso e aprovação por outro administrador

O controle de acesso ao sistema divide-se entre um perfil de usuário geral e perfis administrativos com alçadas de decisão específicas. O perfil geral possui acesso para consulta e operação, porém sem autonomia para alterar regras de cálculo ou modificar dados de comissionamento. Para aprovação de alterações em regras vigentes, exige-se o princípio da dupla custódia: nenhum usuário, mesmo possuindo privilégios de administrador, possui permissão para aprovar ou aplicar alterações de forma unilateral sem a concordância expressa de outro administrador.

## solicitacao-parametros-faltantes — Interação e solicitação de parâmetros faltantes

O fluxo interativo de configuração de campanhas e alterações de regras de negócio fundamenta-se em diretrizes bem mapeadas e parâmetros pré-estabelecidos. Caso o comando emitido pelo usuário não contenha todas as variáveis mandatórias necessárias para a execução da regra, o sistema deve pausar o fluxo de processamento e solicitar objetivamente os parâmetros faltantes ao usuário, assegurando a completude dos dados antes da homologação.

## exemplo-comando-completo — Exemplo de comando completo de campanha de vendas

Um comando completo de incentivo comercial deve delimitar o horizonte temporal de vigência, a alteração percentual de remuneração, o contexto da campanha e o público-alvo abrangido, incluindo exceções de elegibilidade. Um exemplo funcional completo consiste na determinação de que todas as vendas efetuadas em determinado intervalo de datas recebam um acréscimo percentual de um por cento na comissão, sendo a bonificação válida para todas as marcas comercializadas e para todos os cargos da organização, com exceção expressa dos gerentes.

## cargo-150-gerente — Unificação das funções de gerência sob o cargo 150

Na modelagem de dados e nas regras de apuração de vendas, o código de cargo 150 abrange indistintamente tanto a função de gerente de loja quanto a de gerente de quiosque. A regra de negócio e o percentual de incentivo aplicam-se igualmente a ambas as descrições, recaindo sobre o faturamento global da unidade física. As distinções de volume comercial ocorrem naturalmente pelo porte das operações de loja e quiosque, devendo o sistema utilizar unicamente o identificador numérico 150 como referência de cargo.
