#!/usr/bin/env python3
"""
Script para alterar a senha de um usuário
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

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
    data_criacao = db.Column(db.DateTime, default=db.func.now())

# Alterar a senha
with app.app_context():
    email = input("Digite o email do usuário: ").strip()
    
    usuario = Usuario.query.filter_by(email=email).first()
    
    if not usuario:
        print(f"❌ Usuário {email} não encontrado!")
    else:
        nova_senha = input("Digite a nova senha: ").strip()
        confirmar_senha = input("Confirme a nova senha: ").strip()
        
        if nova_senha != confirmar_senha:
            print("❌ As senhas não conferem!")
        elif len(nova_senha) < 6:
            print("❌ A senha deve ter pelo menos 6 caracteres!")
        else:
            usuario.senha_hash = generate_password_hash(nova_senha)
            db.session.commit()
            print(f"✅ Senha alterada com sucesso para {email}!")
            print(f"   Nova senha: {nova_senha}")
