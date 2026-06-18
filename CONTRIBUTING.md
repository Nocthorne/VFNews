# Contribuindo com o VFNews

Obrigado pelo interesse em contribuir! Este é um projeto pessoal/acadêmico, mas aberto a sugestões, correções e melhorias.

## Como contribuir

1. Faça um fork do repositório
2. Crie uma branch a partir da `main`:
   ```bash
   git checkout -b feat/nome-da-sua-feature
   ```
3. Faça suas alterações seguindo o padrão de commits do projeto (veja abaixo)
4. Garanta que a aplicação continua rodando localmente (`python app.py`)
5. Abra um Pull Request descrevendo **o que** foi alterado e **por quê**

## Padrão de commits

Este projeto segue [Conventional Commits](https://www.conventionalcommits.org/pt-br/):

| Prefixo | Quando usar |
|---|---|
| `feat:` | Nova funcionalidade |
| `fix:` | Correção de bug |
| `refactor:` | Mudança de código que não altera comportamento |
| `docs:` | Alterações em documentação |
| `test:` | Adição ou ajuste de testes |
| `chore:` | Tarefas de manutenção (dependências, configs, etc.) |

Exemplo:
```
fix: corrige importação ausente do módulo database
```

## Reportando bugs

Abra uma [issue](../../issues/new) descrevendo:
- O que você esperava que acontecesse
- O que de fato aconteceu
- Passos para reproduzir
- Logs relevantes (sem incluir chaves de API ou dados sensíveis)

## Código de conduta

Seja respeitoso. Críticas técnicas são bem-vindas; ataques pessoais não.
