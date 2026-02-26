#!/usr/bin/env python3
"""
Script de migração FINAL - Recupera dados do banco antigo
Adiciona coluna 'tipo' e cria os 4 usuários padrão
"""

import sqlite3
import shutil
import os
from datetime import datetime

def migrar_banco_final():
    """Migra dados do banco antigo para o novo com coluna 'tipo'"""
    
    banco_antigo = 'pcp_antigo.db'
    banco_novo = 'pcp.db'
    
    # Verificar se o banco antigo existe
    if not os.path.exists(banco_antigo):
        print("❌ Erro: Arquivo 'pcp_antigo.db' não encontrado!")
        print("   Você precisa fazer backup do banco antigo como 'pcp_antigo.db'")
        return False
    
    try:
        print("🔍 Analisando banco antigo...")
        
        # Conectar ao banco antigo
        conexao_antiga = sqlite3.connect(banco_antigo)
        cursor_antiga = conexao_antiga.cursor()
        
        # Verificar se tabela usuario existe
        cursor_antiga.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
        if not cursor_antiga.fetchone():
            print("❌ Erro: Tabela 'usuario' não encontrada no banco antigo!")
            conexao_antiga.close()
            return False
        
        print("✅ Banco antigo encontrado")
        
        # Contar usuários antigos
        cursor_antiga.execute("SELECT COUNT(*) FROM usuario")
        total_usuarios_antigos = cursor_antiga.fetchone()[0]
        print(f"📊 Usuários no banco antigo: {total_usuarios_antigos}")
        
        # Fazer backup do banco novo (se existir)
        if os.path.exists(banco_novo):
            backup_name = f"pcp_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy(banco_novo, backup_name)
            print(f"✅ Backup do banco novo criado: {backup_name}")
        
        # Copiar banco antigo para novo
        print("⚙️ Copiando banco antigo...")
        shutil.copy(banco_antigo, banco_novo)
        
        # Conectar ao banco novo
        conexao_nova = sqlite3.connect(banco_novo)
        cursor_nova = conexao_nova.cursor()
        
        # Verificar se coluna 'tipo' existe
        cursor_nova.execute("PRAGMA table_info(usuario)")
        colunas = cursor_nova.fetchall()
        nomes_colunas = [col[1] for col in colunas]
        
        if 'tipo' not in nomes_colunas:
            print("⚙️ Adicionando coluna 'tipo'...")
            cursor_nova.execute("""
                ALTER TABLE usuario 
                ADD COLUMN tipo VARCHAR(20) DEFAULT 'VISUALIZADOR'
            """)
            conexao_nova.commit()
            print("✅ Coluna 'tipo' adicionada")
        
        # Atualizar o admin para ADMIN
        print("⚙️ Atualizando usuário admin...")
        cursor_nova.execute("""
            UPDATE usuario 
            SET tipo = 'ADMIN' 
            WHERE email = 'admin@nexon.com'
        """)
        conexao_nova.commit()
        print("✅ Admin definido como ADMIN")
        
        # Criar outros usuários
        from werkzeug.security import generate_password_hash
        
        usuarios_novos = [
            {"nome": "Gerente", "email": "gerente@nexon.com", "senha": "senha123", "tipo": "GERENTE"},
            {"nome": "Operador", "email": "operador@nexon.com", "senha": "senha123", "tipo": "OPERADOR"},
            {"nome": "Visualizador", "email": "visualizador@nexon.com", "senha": "senha123", "tipo": "VISUALIZADOR"}
        ]
        
        print("⚙️ Criando novos usuários...")
        
        for dados in usuarios_novos:
            # Verificar se já existe
            cursor_nova.execute("SELECT id FROM usuario WHERE email = ?", (dados["email"],))
            if cursor_nova.fetchone():
                print(f"⚠️ Usuário já existe: {dados['email']}")
                continue
            
            # Criar novo usuário
            senha_hash = generate_password_hash(dados["senha"])
            cursor_nova.execute("""
                INSERT INTO usuario (nome, email, senha_hash, ativo, tipo, data_criacao)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (dados["nome"], dados["email"], senha_hash, True, dados["tipo"], datetime.now()))
            
            print(f"✅ Usuário criado: {dados['email']} ({dados['tipo']})")
        
        conexao_nova.commit()
        
        # Listar todos os usuários
        print("\n📋 Usuários no banco novo:")
        cursor_nova.execute("SELECT id, nome, email, tipo FROM usuario")
        usuarios = cursor_nova.fetchall()
        
        for usuario in usuarios:
            print(f"   - {usuario[1]} ({usuario[2]}) - Tipo: {usuario[3]}")
        
        # Verificar outras tabelas
        print("\n📊 Tabelas no banco:")
        cursor_nova.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = cursor_nova.fetchall()
        
        for tabela in tabelas:
            cursor_nova.execute(f"SELECT COUNT(*) FROM {tabela[0]}")
            count = cursor_nova.fetchone()[0]
            print(f"   - {tabela[0]}: {count} registros")
        
        conexao_nova.close()
        conexao_antiga.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("🔧 MIGRAÇÃO FINAL - RECUPERAR DADOS DO BANCO ANTIGO")
    print("=" * 70)
    print()
    
    sucesso = migrar_banco_final()
    
    print()
    print("=" * 70)
    
    if sucesso:
        print("✅ Migração concluída com sucesso!")
        print()
        print("📝 Próximas etapas:")
        print("   1. Feche esta janela")
        print("   2. Reinicie a aplicação: python app.py")
        print("   3. Faça login com admin@nexon.com / senha123")
        print()
    else:
        print("❌ Erro na migração!")
        print()
        print("📝 Dicas:")
        print("   1. Verifique se você está na pasta C:\\PCP_WEB\\")
        print("   2. Verifique se o arquivo pcp_antigo.db existe")
        print("   3. Feche a aplicação (Ctrl+C) antes de rodar este script")
        print()
