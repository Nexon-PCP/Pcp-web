#!/usr/bin/env python3
"""
Script para verificar, criar ou resetar usuário admin
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pcp.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "pcp-secret"

db = SQLAlchemy(app)

class Usuario(db.Model):
    __tablename__ = "usuario"
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.now)

print("\n" + "="*50)
print("  GERENCIADOR DE USUÁRIOS - NEXON SISTEMAS")
print("="*50 + "\n")

with app.app_context():
    # Criar tabelas
    db.create_all()
    
    # Listar usuários existentes
    usuarios = Usuario.query.all()
    
    if usuarios:
        print(f"✅ Encontrados {len(usuarios)} usuário(s):\n")
        for u in usuarios:
            print(f"   ID: {u.id}")
            print(f"   Nome: {u.nome}")
            print(f"   Email: {u.email}")
            print(f"   Ativo: {u.ativo}")
            print(f"   Criado em: {u.data_criacao}")
            print()
    else:
        print("❌ Nenhum usuário encontrado!\n")
    
    # Menu
    print("O que deseja fazer?")
    print("1. Criar novo usuário admin")
    print("2. Resetar senha do admin")
    print("3. Sair")
    print()
    
    opcao = input("Digite a opção (1-3): ").strip()
    
    if opcao == "1":
        print("\n--- CRIAR NOVO USUÁRIO ---\n")
        
        # Verificar se já existe
        admin = Usuario.query.filter_by(email="admin@nexon.com").first()
        if admin:
            print("⚠️  Usuário admin@nexon.com já existe!")
            print(f"   Nome: {admin.nome}")
            print(f"   Ativo: {admin.ativo}")
        else:
            novo_usuario = Usuario(
                nome="Administrador",
                email="admin@nexon.com",
                senha_hash=generate_password_hash("admin123"),
                ativo=True
            )
            db.session.add(novo_usuario)
            db.session.commit()
            print("✅ Usuário admin criado com sucesso!")
            print("   Email: admin@nexon.com")
            print("   Senha: admin123")
    
    elif opcao == "2":
        print("\n--- RESETAR SENHA ---\n")
        
        admin = Usuario.query.filter_by(email="admin@nexon.com").first()
        
        if admin:
            admin.senha_hash = generate_password_hash("admin123")
            db.session.commit()
            print("✅ Senha resetada com sucesso!")
            print("   Email: admin@nexon.com")
            print("   Nova senha: admin123")
        else:
            print("❌ Usuário admin@nexon.com não encontrado!")
            print("   Use a opção 1 para criar um novo usuário")
    
    elif opcao == "3":
        print("Saindo...")
    
    else:
        print("❌ Opção inválida!")

print("\n" + "="*50 + "\n")
