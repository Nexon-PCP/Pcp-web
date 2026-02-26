#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para alterar senha de usuários
Uso: 
  python alterar_senha_v2.py email nova_senha
  ou
  python alterar_senha_v2.py
"""

import os
import sys

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar app e models
try:
    from app import app, db, Usuario
except ImportError:
    print("❌ Erro: Não foi possível importar app.py")
    print("   Certifique-se de estar na pasta C:\\PCP_WEB\\")
    sys.exit(1)


def listar_usuarios():
    """Lista todos os usuários do banco"""
    with app.app_context():
        usuarios = Usuario.query.all()
        
        if not usuarios:
            print("❌ Nenhum usuário encontrado no banco de dados!")
            return None
        
        print("\n" + "="*70)
        print("📋 USUÁRIOS DO SISTEMA")
        print("="*70)
        
        for idx, usuario in enumerate(usuarios, 1):
            print(f"{idx}. {usuario.email} ({usuario.tipo})")
        
        print("="*70)
        return usuarios


def alterar_senha_interativo():
    """Altera a senha de um usuário (modo interativo)"""
    
    print("\n" + "="*70)
    print("🔐 ALTERAR SENHA DE USUÁRIO")
    print("="*70)
    
    # Listar usuários
    usuarios = listar_usuarios()
    if not usuarios:
        return
    
    # Pedir escolha
    try:
        escolha = int(input("\n📌 Digite o número do usuário: "))
        if escolha < 1 or escolha > len(usuarios):
            print("❌ Opção inválida!")
            return
        
        usuario = usuarios[escolha - 1]
    except ValueError:
        print("❌ Digite um número válido!")
        return
    
    # Confirmar
    print(f"\n✅ Usuário selecionado: {usuario.email} ({usuario.tipo})")
    confirmar = input("Deseja alterar a senha deste usuário? (s/n): ").lower()
    
    if confirmar != 's':
        print("❌ Operação cancelada!")
        return
    
    # Pedir nova senha
    nova_senha = input("🔑 Digite a nova senha: ")
    
    if len(nova_senha) < 6:
        print("❌ A senha deve ter pelo menos 6 caracteres!")
        return
    
    # Atualizar senha
    with app.app_context():
        usuario = Usuario.query.get(usuario.id)
        usuario.definir_senha(nova_senha)
        db.session.commit()
        
        print("\n✅ Senha alterada com sucesso!")
        print(f"   Email: {usuario.email}")
        print(f"   Tipo: {usuario.tipo}")
        print("="*70)


def alterar_senha_direto(email, nova_senha):
    """Altera a senha de um usuário (modo direto via argumentos)"""
    
    print("\n" + "="*70)
    print("🔐 ALTERAR SENHA DE USUÁRIO")
    print("="*70)
    
    # Validar senha
    if len(nova_senha) < 6:
        print("❌ A senha deve ter pelo menos 6 caracteres!")
        print("="*70)
        return False
    
    # Buscar usuário
    with app.app_context():
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            print(f"❌ Usuário '{email}' não encontrado!")
            print("="*70)
            return False
        
        # Atualizar senha
        usuario.definir_senha(nova_senha)
        db.session.commit()
        
        print(f"✅ Senha alterada com sucesso!")
        print(f"   Email: {usuario.email}")
        print(f"   Tipo: {usuario.tipo}")
        print("="*70)
        return True


if __name__ == "__main__":
    try:
        if len(sys.argv) == 3:
            # Modo direto: python alterar_senha_v2.py email senha
            email = sys.argv[1]
            nova_senha = sys.argv[2]
            alterar_senha_direto(email, nova_senha)
        elif len(sys.argv) == 1:
            # Modo interativo: python alterar_senha_v2.py
            alterar_senha_interativo()
        else:
            print("\n❌ Uso incorreto!")
            print("\nOpções:")
            print("  1. python alterar_senha_v2.py")
            print("     (modo interativo - escolhe usuário no menu)")
            print("\n  2. python alterar_senha_v2.py email@nexon.com novaSenha123")
            print("     (modo direto - altera senha direto)")
            print("\n")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n❌ Operação cancelada pelo usuário!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
