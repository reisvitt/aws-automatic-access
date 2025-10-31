#!/usr/bin/env python3
# coding=utf-8
"""
Script: aws_ssh_access.py
Autor: Vitor Reis
Descrição:
  Automatiza o processo de permitir seu IP atual em um Security Group da AWS
  para acessar uma instância EC2. 
  Fluxo:
    1. Pergunta qual perfil AWS usar (projeto)
    2. Lista as instâncias EC2 e permite escolher uma
    3. Lista Security Groups e permite escolher um + porta
    4. Cria ou atualiza uma regra de IP com seu IP público atual
    5. Mostra um resumo no final
"""

# Bibliotecas padrão
import os
import requests
import configparser

# Bibliotecas externas
import boto3          # SDK oficial da AWS para Python
import inquirer       # Cria menus interativos no terminal

# ---------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------

def get_public_ip():
    """
    Obtém o IP público atual da máquina usando o serviço checkip.amazonaws.com
    Retorna o IP como string (ex: '123.45.67.89')
    """
    return requests.get("https://checkip.amazonaws.com").text.strip()


def list_aws_profiles():
    """
    Lê o arquivo ~/.aws/credentials e retorna uma lista com os perfis disponíveis.
    Exemplo de perfis:
      [cliente1]
      [cliente2]
    """
    config = configparser.ConfigParser()
    config.read(os.path.expanduser("~/.aws/credentials"))
    return config.sections()


def choose_profile(profiles):
    """
    Mostra um menu com todos os perfis AWS disponíveis e retorna o escolhido.
    """
    questions = [
        inquirer.List(
            "profile",
            message="Selecione o projeto (perfil AWS):",
            choices=profiles
        )
    ]
    return inquirer.prompt(questions)["profile"]


def choose_ec2(session):
    """
    Lista todas as instâncias EC2 disponíveis no perfil escolhido
    e permite o usuário selecionar uma delas.
    Retorna o ID da instância selecionada.
    """
    ec2 = session.client("ec2")

    # Busca todas as instâncias
    instances = ec2.describe_instances()
    choices = []
    mapping = {}

    for res in instances["Reservations"]:
        for inst in res["Instances"]:
            # Pega o nome da instância (tag "Name"), se existir
            name = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), inst["InstanceId"])
            # Monta a lista de opções
            choices.append(f"{name} ({inst['InstanceId']})")
            mapping[name] = inst["InstanceId"]

    if not choices:
        raise Exception("Nenhuma instância EC2 encontrada nesse perfil.")

    # Exibe a lista pro usuário escolher
    questions = [
        inquirer.List(
            "instance",
            message="Selecione a instância EC2:",
            choices=choices
        )
    ]
    selected = inquirer.prompt(questions)["instance"]

    # Retorna o ID correspondente ao nome selecionado
    for name, inst_id in mapping.items():
        if name in selected:
            return inst_id


def choose_security_group(session, instance_id):
    """
    Lista apenas os Security Groups associados à instância EC2 selecionada e permite escolher um.
    Também pergunta qual porta liberar (ex: 22 para SSH).
    Retorna o Security Group selecionado e a porta.
    """
    ec2 = session.client("ec2")

    # Busca a instância selecionada
    reservations = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"]
    instance = None
    for res in reservations:
        for inst in res["Instances"]:
            if inst["InstanceId"] == instance_id:
                instance = inst
                break
    if not instance:
        raise Exception("Instância EC2 não encontrada.")

    # Pega os Security Groups associados à instância
    sg_ids = [sg["GroupId"] for sg in instance.get("SecurityGroups", [])]
    if not sg_ids:
        raise Exception("Nenhum Security Group associado à instância.")

    # Busca detalhes dos grupos
    groups = ec2.describe_security_groups(GroupIds=sg_ids)["SecurityGroups"]
    choices = []
    mapping = {}
    for g in groups:
        group_id = g['GroupId']
        desc = g.get('Description', '')
        # Filtra apenas regras de entrada (inbound)
        inbound_perms = [p for p in g.get('IpPermissions', []) if p.get('IpProtocol') != '-1']
        if not inbound_perms:
            continue
        # Monta string de portas
        port_ranges = []
        for p in inbound_perms:
            from_port = p.get('FromPort')
            to_port = p.get('ToPort')
            if from_port is not None and to_port is not None:
                if from_port == to_port:
                    port_ranges.append(str(from_port))
                else:
                    port_ranges.append(f"{from_port}-{to_port}")
        ports_str = ', '.join(port_ranges) if port_ranges else 'N/A'
        label = f"{desc} Portas: {ports_str} ({group_id})"
        choices.append(label)
        mapping[label] = g

    # Pergunta qual grupo selecionar
    questions = [
        inquirer.List(
            "sg",
            message="Selecione o Security Group (apenas inbound):",
            choices=choices
        )
    ]
    selected = inquirer.prompt(questions)["sg"]

    sg = mapping[selected]

    # Descobre as portas disponíveis
    inbound_perms = [p for p in sg.get('IpPermissions', []) if p.get('IpProtocol') != '-1']
    port_set = set()
    for p in inbound_perms:
        from_port = p.get('FromPort')
        to_port = p.get('ToPort')
        if from_port is not None and to_port is not None:
            if from_port == to_port:
                port_set.add(from_port)
            else:
                port_set.update(range(from_port, to_port + 1))

    port_list = sorted(port_set)
    if len(port_list) == 1:
        port = port_list[0]
    else:
        questions = [
            inquirer.List(
                "port",
                message=f"Qual porta deseja liberar? (opções: {', '.join(str(p) for p in port_list)})",
                choices=[str(p) for p in port_list]
            )
        ]
        port = int(inquirer.prompt(questions)["port"])

    return sg, port


def update_security_group(session, sg, port, user_name):
    """
    Adiciona ou atualiza a regra no Security Group selecionado.
    Se já existir uma regra com a descrição do usuário (ex: "Vitor Reis"),
    remove a antiga e adiciona a nova com o IP atual.
    """
    ec2 = session.client("ec2")

    # Monta o IP atual no formato CIDR (x.x.x.x/32)
    ip = get_public_ip() + "/32"
    desc = user_name
    exists = False

    # Verifica se já existe uma regra com a descrição do usuário
    for perm in sg["IpPermissions"]:
        if perm.get("FromPort") == port:
            for ip_range in perm.get("IpRanges", []):
                if ip_range.get("Description") == desc:
                    # Remove a regra antiga antes de criar a nova
                    ec2.revoke_security_group_ingress(
                        GroupId=sg["GroupId"],
                        IpProtocol="tcp",
                        FromPort=port,
                        ToPort=port,
                        CidrIp=ip_range["CidrIp"]
                    )
                    exists = True

    # Cria a nova regra com o IP atual usando IpPermissions
    ec2.authorize_security_group_ingress(
        GroupId=sg["GroupId"],
        IpPermissions=[{
            "IpProtocol": "tcp",
            "FromPort": port,
            "ToPort": port,
            "IpRanges": [{"CidrIp": ip, "Description": desc}]
        }]
    )

    return ip, exists


# ---------------------------------------------------
# Função principal
# ---------------------------------------------------

def main():
    """
    Fluxo principal do script:
      - seleciona perfil AWS
      - seleciona instância EC2
      - seleciona security group e porta
      - atualiza o IP no grupo
      - exibe resumo
    """
    print("🚀 Script de Acesso AWS SSH Automático\n")

    # Passo 1 - Escolher o perfil AWS (projeto)
    profiles = list_aws_profiles()
    profile = choose_profile(profiles)

    # Cria uma sessão boto3 com o perfil selecionado
    session = boto3.Session(profile_name=profile)

    # Passo 2 - Escolher a instância EC2
    instance_id = choose_ec2(session)

    # Passo 3 - Escolher o Security Group e porta
    sg, port = choose_security_group(session, instance_id)

    # Nome do usuário (usado na descrição da regra)
    user_name = os.getenv("USER") or "AWS-ACCESS"

    # Passo 4 - Atualiza ou cria a regra no grupo
    ip, updated = update_security_group(session, sg, port, user_name)

    # Passo 5 - Exibe resumo final
    print("\n✅ Acesso liberado!")
    print(f"Conta (perfil AWS): {profile}")
    print(f"Instância EC2: {instance_id}")
    print(f"Security Group: {sg['GroupName']} ({sg['GroupId']})")
    print(f"Porta liberada: {port}")
    print(f"Seu IP atual: {ip}")
    print(f"Regra {'atualizada' if updated else 'criada'} com sucesso.\n")


# ---------------------------------------------------
# Execução
# ---------------------------------------------------

if __name__ == "__main__":
    main()
