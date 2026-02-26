#!/usr/bin/env python3
"""
Script para criar usuário admin no banco de dados
Execute este script UMA VEZ antes de usar a aplicação
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os

# Importar as configurações do app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pcp.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "pcp-secret"

db = SQLAlchemy(app)

# Definir o modelo Usuario
class Usuario(db.Model):
    __tablename__ = "usuario"
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=db.func.now())
    
    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

# Criar o banco de dados e o usuário
with app.app_context():
    # Criar todas as tabelas
    db.create_all()
    
    # Verificar se o usuário já existe
    usuario_existente = Usuario.query.filter_by(email="admin@nexon.com").first()
    
    if usuario_existente:
        print("✅ Usuário admin@nexon.com já existe!")
        print(f"   Nome: {usuario_existente.nome}")
        print(f"   Ativo: {usuario_existente.ativo}")
    else:
        # Criar novo usuário
        novo_usuario = Usuario(
            nome="Administrador",
            email="admin@nexon.com",
            senha_hash=generate_password_hash("admin123"),
            ativo=True
        )
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        print("✅ Usuário criado com sucesso!")
        print("   Email: admin@nexon.com")
        print("   Senha: admin123")
        print("")
        print("Agora você pode fazer login na aplicação! 🎉")

print("\n✅ Script finalizado!")
