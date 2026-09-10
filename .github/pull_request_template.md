## 🎯 Objetivo

<!-- Explique por que este PR foi criado e qual seu propósito central.

Exemplos:

- Implementação do módulo de chat via WebSocket
- Correção do escalonamento entre grupos de atendimento
- Refatoração da lógica de triagem automatizada -->



<!-- ## #️⃣ Issues relacionadas (opcional)

Vincule tarefas do Jira ou issues do GitHub:

```
resolves PRO4-42
resolves <https://github.com/><org>/<repo>/issues/<issue_number>
```

---

## 🐛 Causa do bug (opcional — apenas fix)

Descreva a causa técnica raiz.

--- -->

## 📋 Changelog

<!-- Lista técnica das mudanças:

- arquivos alterados
- comportamento modificado
- regras adicionadas
- refatorações feitas -->



## 🧪 Como testar 

<!-- Passo a passo claro para o revisor validar: -->

1. 
2. 
3. 

---

<!-- ## 👀 Observações (opcional)

- decisões de arquitetura
- limitações conhecidas
- tradeoffs
- próximos passos

--- -->

<!-- ## Exemplo de PR Completo

```markdown
## 🎯 Objetivo

Implementar o módulo de chat em tempo real utilizando WebSocket Gateway
(Socket.IO) com persistência de mensagens no MongoDB.

## #️⃣ Issues relacionadas

resolves PRO4-42

## 📋 Changelog

- Criado `chat/chat.module.ts` com imports de Mongoose e JWT
- Criado `chat/chat.gateway.ts` com eventos: `joinRoom`, `sendMessage`,
  `typing`, `leaveRoom`
- Criado `chat/chat.service.ts` com lógica de persistência de mensagens
- Criado `chat/schemas/message.schema.ts` (Mongoose schema)
- Criado `chat/dto/send-message.dto.ts` com validação via class-validator
- Configurado `RedisIoAdapter` no `main.ts` para sincronização entre instâncias
- Criado `auth/ws-jwt.guard.ts` para autenticação JWT no WebSocket

## 🧪 Como testar

1. Subir o backend: `npm run start:dev`
2. Subir Redis e MongoDB via Docker: `docker-compose up -d`
3. Conectar ao WebSocket via Postman ou cliente Socket.IO:
   - URL: `ws://localhost:3000/chat`
   - Auth: `{ "token": "<jwt_token>" }`
4. Emitir evento `joinRoom` com `{ "ticketId": "1" }`
5. Emitir evento `sendMessage` com `{ "ticketId": "1", "content": "Olá" }`
6. Verificar que o evento `newMessage` é recebido
7. Verificar que a mensagem foi salva no MongoDB (collection `messages`)

## 👀 Observações

- O Redis Adapter já está configurado, mas em dev com uma instância o
  fallback in-memory também funciona.
- O indicador de "digitando..." tem debounce de 2s no client-side.
- Próximo passo: implementar notificações push (US-2.5).
``` -->