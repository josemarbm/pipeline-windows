# Documentação dos Scripts de Pipeline

Este diretório contém os scripts responsáveis por automatizar e padronizar o processo de criação de *releases* e *hotfixes* utilizando branches do Git e abrindo Pull Requests automaticamente pelo GitHub.

## Pré-requisitos

Para que os scripts funcionem corretamente, você deve ter as seguintes ferramentas instaladas e configuradas:

- **Git**: Ferramenta de controle de versão (deve estar configurada com acesso ao repositório).
- **GitHub CLI (`gh`)**: Utilitário de linha de comando oficial do GitHub. 
  - Você precisa estar autenticado no `gh` antes de rodar os scripts. Caso não esteja, execute `gh auth login`.

Ambos os scripts utilizam o formato de versão em tags contendo duas partes separadas por ponto: `MINOR.PATCH` (por exemplo, `1.2` ou `2.0`).

---

## 1. `create_hotfix.sh`

Este script automatiza o processo de iniciar uma correção urgente (hotfix) que precisa ir direto para o ambiente de produção, derivando sempre da branch `main`.

**Como funciona o fluxo do script:**
1. **Validações Iniciais:** Verifica se o `gh` está instalado e se seu status de autenticação está válido.
2. **Checagem do Git:** Confirma se você está na branch `main` e se o repositório de trabalho está limpo (sem mudanças não comitadas).
3. **Atualização:** Faz um `git pull origin main` e busca as tags mais atuais (`git fetch --prune --tags`).
4. **Cálculo da Versão:** Identifica a tag mais recente no repositório. O padrão calculado para hotfix é **incrementar a parte `PATCH`** da versão. Por exemplo, se a última tag é `1.2`, a nova versão planejada será `1.3`.
5. **Entrada do Usuário:** 
   - Solicita o nome da nova branch. É exigido que o nome comece obrigatoriamente com o prefixo `hotfix/`.
   - Solicita confirmação `(Y/n)` antes de prosseguir com a criação de fato.
6. **Ações no Git/GitHub:**
   - Cria uma nova branch (`git checkout -b`) a partir da `main`.
   - Produz um commit vazio como marcador, com a mensagem: `"Hotfix - <VERSAO>"`.
   - Faz o push da branch para a origem remota.
   - Usa a CLI do GitHub para abrir automaticamente um Pull Request, visando unir (`merge`) a branch atual na `main`.

**Uso:**
```bash
./scripts/create_hotfix.sh
```

---

## 2. `create_release.sh`

Este script serve para iniciar o processo de uma nova entrega planejada (release). O objetivo é pegar tudo o que está homologado no ambiente de desenvolvimento e preparar para a ramificação principal.

**Como funciona o fluxo do script:**
1. **Validações Iniciais:** Da mesma forma, verifica o `gh` e a autenticação ativa.
2. **Checagem do Git:** Exige que a sua branch atual seja a `develop` e que a área de trabalho não tenha nenhuma alteração pendente (working tree limpa).
3. **Atualização:** Atualiza a sua `develop` local com o repósitório remoto (`git pull origin develop`) e atualiza as tags ativas.
4. **Cálculo da Versão:** Busca a última tag criada. O padrão de release altera significativamente a versão do software **incrementando a parte `MINOR` e zerando a parte `PATCH`**. Por exemplo, se a última release era `1.2`, a nova vira `2.0`.
5. **Confirmação:** Informa a qual era a última versão, informa a nova versão gerada e pede confirmação para continuar `(Y/n)`.
6. **Ações no Git/GitHub:**
   - Cria uma nova branch a partir de `develop` automaticamente nomeada como `release/<NOVA_VERSAO>`.
   - Envia (*push*) a nova branch.
   - Emite um comando no GitHub CLI para criar o Pull Request da recém-criada `release/<NOVA_VERSAO>`, apontando também para a branch `main`.

**Uso:**
```bash
./scripts/create_release.sh
```
