# 🚀 AWS SSH Access Automático

Script Python para automatizar o processo de liberação de acesso SSH em instâncias EC2 da AWS, gerenciando regras de Security Groups de forma interativa.

## 📋 Descrição

Este script automatiza o fluxo completo de configuração de acesso SSH:

1. **Seleciona** o perfil AWS (projeto/conta)
2. **Lista e escolhe** uma instância EC2
3. **Lista e escolhe** um Security Group + porta
4. **Atualiza** automaticamente a regra com seu IP público atual
5. **Exibe** um resumo completo da configuração

## 🎯 Funcionalidades

- ✅ Interface interativa no terminal (menus de seleção)
- ✅ Detecção automática do IP público
- ✅ Suporte a múltiplos perfis AWS
- ✅ Atualização inteligente de regras (remove IP antigo, adiciona novo)
- ✅ Identificação de regras por usuário
- ✅ Resumo detalhado após execução

## 📦 Dependências

O projeto utiliza as seguintes bibliotecas Python:

| Biblioteca | Versão  | Descrição                           |
| ---------- | ------- | ----------------------------------- |
| `boto3`    | 1.37.38 | SDK oficial da AWS para Python      |
| `inquirer` | 3.4.0   | Menus interativos no terminal       |
| `requests` | 2.22.0  | Requisições HTTP (busca IP público) |

## 🔧 Instalação

### 1. Clone ou baixe o projeto

```bash
git clone <seu-repositorio>
cd aws-access
```

### 2. Instale as dependências

```bash
pip3 install --user boto3 inquirer requests
```

### 3. Configure suas credenciais AWS

Certifique-se de ter o arquivo `~/.aws/credentials` configurado:

```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY

[projeto1]
aws_access_key_id = ANOTHER_ACCESS_KEY
aws_secret_access_key = ANOTHER_SECRET_KEY
```

## 🚀 Uso

### Executar o script

```bash
python3 aws_ssh_access.py
```

ou

```bash
chmod +x aws_ssh_access.py
./aws_ssh_access.py
```

### Fluxo de execução

```
🚀 Script de Acesso AWS SSH Automático

? Selecione o projeto (perfil AWS):
  > projeto1
    projeto2
    default

? Selecione a instância EC2:
  > Servidor Web (i-0abc123def456)
    Banco de Dados (i-0xyz789ghi012)



? Selecione o Security Group:
  > sg-0abc12345 - Web Server [Portas: 22]
    sg-0def67890 - Database [Portas: 3306]
    sg-0xyz99999 - MultiApp [Portas: 80-443, 8080]

? Qual porta deseja liberar? (ex: 22)
  (Só será perguntado se o grupo tiver mais de uma porta disponível. Se houver apenas uma, ela será usada automaticamente.)

✅ Acesso liberado!
Conta (perfil AWS): projeto1
Instância EC2: i-0abc123def456
Security Group: sg-web-server (sg-0abc123)
Porta liberada: 22
Seu IP atual: 203.0.113.42/32
Regra atualizada com sucesso.
```

## 📚 Estrutura do Código

### Funções principais

| Função                    | Descrição                                                                                        |
| ------------------------- | ------------------------------------------------------------------------------------------------ |
| `get_public_ip()`         | Obtém o IP público atual via checkip.amazonaws.com                                               |
| `list_aws_profiles()`     | Lista todos os perfis configurados em ~/.aws/credentials                                         |
| `choose_profile()`        | Menu interativo para escolher perfil AWS                                                         |
| `choose_ec2()`            | Lista e permite escolher uma instância EC2                                                       |
| `choose_security_group()` | Lista Security Groups da instância selecionada e pergunta a porta (apenas se houver mais de uma) |
| `update_security_group()` | Cria ou atualiza regra no Security Group                                                         |
| `main()`                  | Orquestra todo o fluxo do script                                                                 |

### Exemplo de uso das funções

```python
# Obter IP público
ip = get_public_ip()
# Retorna: "203.0.113.42"

# Criar sessão AWS
session = boto3.Session(profile_name='projeto1')

# Escolher instância
instance_id = choose_ec2(session)
# Retorna: "i-0abc123def456"
```

## 🔐 Segurança

- ⚠️ **Nunca commite** suas credenciais AWS no repositório
- ✅ As credenciais devem estar **apenas** em `~/.aws/credentials`
- ✅ Use perfis diferentes para projetos diferentes
- ✅ As regras são identificadas por usuário ($USER)

## 🛠️ Requisitos

- **Python:** 3.6+
- **Sistema Operacional:** Linux/macOS/Windows
- **Permissões AWS:**
  - `ec2:DescribeInstances`
  - `ec2:DescribeSecurityGroups`
  - `ec2:AuthorizeSecurityGroupIngress`
  - `ec2:RevokeSecurityGroupIngress`

## 📝 Notas

- O script usa o formato CIDR `/32` (um único IP)
- Regras antigas do mesmo usuário são **removidas** antes de adicionar a nova
- A descrição da regra usa o nome do usuário do sistema (`$USER`)

## 🐛 Troubleshooting

### Erro: "No module named 'boto3'"

```bash
pip3 install --user boto3
```

### Erro: "Unable to locate credentials"

Configure suas credenciais:

```bash
aws configure --profile nome-do-perfil
```

### Erro: "Access Denied"

Verifique se seu usuário IAM tem as permissões necessárias no Security Group.

## 👨‍💻 Autor

**Vitor Reis**

## 📄 Licença

Este projeto está licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para mais detalhes.

MIT License © 2025 Vitor Reis

---

**Dica:** Para facilitar, crie um alias no seu shell:

```bash
# Adicione no ~/.bashrc ou ~/.zshrc
alias aws-ssh='python3 ~/caminho-para-o-arquivo/aws_ssh_access.py'
```

Depois basta rodar: `aws-ssh`
