#!/usr/bin/env python3
"""
Script para criar usuários especializados com permissões por etapa
"""

import sqlite3
import json
from werkzeug.security import generate_password_hash

# Conectar ao banco
conn = sqlite3.connect('C:\\PCP_WEB\\instance\\pcp.db')
cursor = conn.cursor()

# Usuários especializados
usuarios_especializados = [
    {
        "nome": "Estrutura",
        "email": "estrutura@nexon.com",
        "senha": "senha123",
        "tipo": "ESPECIALISTA",
        "etapas": ["CORTE", "DOBRA", "PINTURA"]
    },
    {
        "nome": "Caldeiraria",
        "email": "caldeiraria@nexon.com",
        "senha": "senha123",
        "tipo": "ESPECIALISTA",
        "etapas": ["CALDEIRARIA"]
    },
    {
        "nome": "Montagem",
        "email": "montagem@nexon.com",
        "senha": "senha123",
        "tipo": "ESPECIALISTA",
        "etapas": ["MONTAGEM"]
    },
    {
        "nome": "Startup",
        "email": "startup@nexon.com",
        "senha": "senha123",
        "tipo": "ESPECIALISTA",
        "etapas": ["START UP"]
    }
]

print("=" * 70)
print("🔧 CRIAR USUÁRIOS ESPECIALIZADOS")
print("=" * 70)

for dados in usuarios_especializados:
    # Verificar se usuário já existe
    cursor.execute("SELECT id FROM usuario WHERE email = ?", (dados["email"],))
    resultado = cursor.fetchone()
    
    if resultado:
        print(f"⚠️ Usuário já existe: {dados['email']}")
    else:
        # Gerar hash da senha
        senha_hash = generate_password_hash(dados["senha"])
        etapas_json = json.dumps(dados["etapas"])
        
        # Inserir usuário
        cursor.execute("""
            INSERT INTO usuario (nome, email, senha_hash, tipo, etapas_permitidas, ativo)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (dados["nome"], dados["email"], senha_hash, dados["tipo"], etapas_json))
        
        print(f"✅ Usuário criado: {dados['email']} ({dados['tipo']})")
        print(f"   Etapas: {', '.join(dados['etapas'])}")

# Salvar alterações
conn.commit()

# Listar todos os usuários
print("\n" + "=" * 70)
print("📋 USUÁRIOS NO BANCO DE DADOS")
print("=" * 70)

cursor.execute("SELECT id, nome, email, tipo, etapas_permitidas FROM usuario ORDER BY tipo, email")
usuarios = cursor.fetchall()

for usuario in usuarios:
    id_user, nome, email, tipo, etapas = usuario
    if etapas:
        etapas_list = json.loads(etapas)
        print(f"ID: {id_user} | {email} ({tipo}) | Etapas: {', '.join(etapas_list)}")
    else:
        print(f"ID: {id_user} | {email} ({tipo})")

conn.close()

print("\n" + "=" * 70)
print("✅ Concluído!")
print("=" * 70)
