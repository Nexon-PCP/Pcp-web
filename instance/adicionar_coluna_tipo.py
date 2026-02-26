#!/usr/bin/env python3
"""
Script SIMPLES - Apenas adiciona a coluna 'tipo' ao banco existente
SEM deletar nada, SEM copiar nada
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

def adicionar_coluna_tipo():
    """Adiciona coluna 'tipo' ao banco existente"""
    
    banco = 'pcp.db'
    
    # Verificar se o banco existe
    if not os.path.exists(banco):
        print("❌ Erro: Arquivo 'pcp.db' não encontrado!")
        return False
    
    try:
        print("🔍 Conectando ao banco...")
        conexao = sqlite3.connect(banco)
        cursor = conexao.cursor()
        
        # Verificar se tabela usuario existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuario'")
        if not cursor.fetchone():
            print("❌ Erro: Tabela 'usuario' não encontrada!")
            conexao.close()
            return False
        
        print("✅ Tabela 'usuario' encontrada")
        
        # Verificar se coluna 'tipo' já existe
        cursor.execute("PRAGMA table_info(usuario)")
        colunas = cursor.fetchall()
        nomes_colunas = [col[1] for col in colunas]
        
        if 'tipo' in nomes_colunas:
            print("✅ Coluna 'tipo' já existe!")
            
            # Contar usuários
            cursor.execute("SELECT COUNT(*) FROM usuario")
            total = cursor.fetchone()[0]
            print(f"📊 Total de usuários: {total}")
            
            conexao.close()
            return True
        
        print("⚙️ Adicionando coluna 'tipo'...")
        
        # Adicionar coluna
        cursor.execute("""
            ALTER TABLE usuario 
            ADD COLUMN tipo VARCHAR(20) DEFAULT 'VISUALIZADOR'
        """)
        
        conexao.commit()
        print("✅ Coluna 'tipo' adicionada!")
        
        # Atualizar admin para ADMIN
        print("⚙️ Atualizando admin para ADMIN...")
        cursor.execute("""
            UPDATE usuario 
            SET tipo = 'ADMIN' 
            WHERE email = 'admin@nexon.com'
        """)
        conexao.commit()
        print("✅ Admin atualizado!")
        
        # Criar novos usuários
        print("⚙️ Criando novos usuários...")
        
        usuarios_novos = [
            {"nome": "Gerente", "email": "gerente@nexon.com", "senha": "senha123", "tipo": "GERENTE"},
            {"nome": "Operador", "email": "operador@nexon.com", "senha": "senha123", "tipo": "OPERADOR"},
            {"nome": "Visualizador", "email": "visualizador@nexon.com", "senha": "senha123", "tipo": "VISUALIZADOR"}
        ]
        
        for dados in usuarios_novos:
            # Verificar se já existe
            cursor.execute("SELECT id FROM usuario WHERE email = ?", (dados["email"],))
            if cursor.fetchone():
                print(f"⚠️ Usuário já existe: {dados['email']}")
                continue
            
            # Criar novo
            senha_hash = generate_password_hash(dados["senha"])
            cursor.execute("""
                INSERT INTO usuario (nome, email, senha_hash, ativo, tipo)
                VALUES (?, ?, ?, ?, ?)
            """, (dados["nome"], dados["email"], senha_hash, True, dados["tipo"]))
            
            print(f"✅ Usuário criado: {dados['email']} ({dados['tipo']})")
        
        conexao.commit()
        
        # Listar usuários
        print("\n📋 Usuários no banco:")
        cursor.execute("SELECT id, nome, email, tipo FROM usuario")
        usuarios = cursor.fetchall()
        
        for usuario in usuarios:
            print(f"   - {usuario[1]} ({usuario[2]}) - Tipo: {usuario[3]}")
        
        # Contar dados
        print("\n📊 Dados no banco:")
        cursor.execute("SELECT COUNT(*) FROM obra")
        print(f"   - Obras: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM op")
        print(f"   - OPs: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM etapa")
        print(f"   - Etapas: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM tarefa")
        print(f"   - Tarefas: {cursor.fetchone()[0]}")
        
        conexao.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("🔧 ADICIONAR COLUNA 'TIPO' AO BANCO EXISTENTE")
    print("=" * 70)
    print()
    
    sucesso = adicionar_coluna_tipo()
    
    print()
    print("=" * 70)
    
    if sucesso:
        print("✅ Sucesso!")
        print()
        print("📝 Próximas etapas:")
        print("   1. Feche esta janela")
        print("   2. Reinicie a aplicação: python app.py")
        print("   3. Faça login com admin@nexon.com / senha123")
        print()
    else:
        print("❌ Erro!")
        print()
