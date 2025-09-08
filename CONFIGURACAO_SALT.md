# Configuração da Variável de Ambiente para Anonimização

Este documento explica como configurar e gerenciar a variável de ambiente `ANONYMIZATION_SALT` usada para a anonimização de dados no B3 Portfolio Manager.

## Importância do Salt de Anonimização

O salt é um valor secreto usado no processo de hash para garantir que:

1. Mesmo que dois sistemas usem o mesmo algoritmo, os hashes gerados serão diferentes
2. Dificulta ataques de força bruta e de dicionário contra os hashes
3. Aumenta significativamente a segurança da anonimização

## Configuração da Variável de Ambiente

### Em Ambiente de Desenvolvimento

#### Linux/macOS:
```bash
export ANONYMIZATION_SALT="valor_secreto_complexo_para_desenvolvimento"
```

#### Windows (PowerShell):
```powershell
$env:ANONYMIZATION_SALT="valor_secreto_complexo_para_desenvolvimento"
```

#### Windows (CMD):
```cmd
set ANONYMIZATION_SALT=valor_secreto_complexo_para_desenvolvimento
```

### Em Ambiente de Produção

#### Google Cloud Run:
Configure a variável de ambiente no console do Google Cloud ou via gcloud:

```bash
gcloud run services update seu-servico \
  --set-env-vars ANONYMIZATION_SALT="valor_secreto_complexo_para_producao"
```

#### Docker:
```bash
docker run -e ANONYMIZATION_SALT="valor_secreto_complexo_para_producao" sua-imagem
```

#### Kubernetes:
Adicione ao seu deployment.yaml:
```yaml
env:
  - name: ANONYMIZATION_SALT
    valueFrom:
      secretKeyRef:
        name: app-secrets
        key: anonymization-salt
```

## Recomendações de Segurança

1. **Use um valor complexo**: Recomenda-se um valor com pelo menos 32 caracteres, incluindo letras maiúsculas, minúsculas, números e símbolos
2. **Mantenha o mesmo valor**: Uma vez definido o salt em produção, não o altere, pois isso invalidaria todos os hash_id existentes
3. **Valores diferentes por ambiente**: Use valores diferentes para desenvolvimento, teste e produção
4. **Armazene de forma segura**: Em produção, use Google Secret Manager ou serviço equivalente
5. **Não compartilhe**: Limite o acesso ao valor do salt apenas a administradores de sistema

## Exemplo de Geração de Salt Seguro

Use o seguinte comando para gerar um salt seguro:

```python
import secrets
import string

# Gera um salt aleatório de 64 caracteres
chars = string.ascii_letters + string.digits + string.punctuation
salt = ''.join(secrets.choice(chars) for _ in range(64))
print(salt)
```

## Requisito Obrigatório

A variável de ambiente `ANONYMIZATION_SALT` é **obrigatória** para o funcionamento do sistema.

**IMPORTANTE**: Se esta variável não for definida, a aplicação não iniciará corretamente e a criação de novos usuários falhará com um erro de configuração de segurança. Esta é uma medida de proteção para evitar que o sistema opere em um estado inseguro.

## Migração de Dados

Se você já tem dados no sistema e está implementando o salt via variável de ambiente pela primeira vez:

1. Defina a variável `ANONYMIZATION_SALT` com o mesmo valor que estava hardcoded anteriormente
2. Execute a migração
3. Após confirmar que tudo está funcionando, você pode mudar para um salt mais seguro, mas isso exigirá recalcular todos os hash_id

## Verificação da Configuração

Para verificar se a variável de ambiente está configurada corretamente, você pode inspecionar as variáveis de ambiente do seu sistema ou, durante a execução, observar os logs da aplicação em caso de erro na inicialização.

O script `validar_anonimizacao.py` também pode ser usado para testes relacionados à anonimização.
