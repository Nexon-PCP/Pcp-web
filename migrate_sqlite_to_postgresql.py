"""
Script para migrar dados do SQLite para PostgreSQL
Execute este script após fazer deploy no Railway
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
import sys

def migrate_sqlite_to_postgresql():
    """Migra dados do SQLite para PostgreSQL"""
    
    # Conectar ao SQLite local
    print("📂 Conectando ao SQLite local...")
    try:
        sqlite_conn = sqlite3.connect('pcp.db')
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.row_factory = sqlite3.Row
        print("✅ SQLite conectado!")
    except Exception as e:
        print(f"❌ Erro ao conectar SQLite: {e}")
        return False
    
    # Conectar ao PostgreSQL (Railway)
    print("🌐 Conectando ao PostgreSQL no Railway...")
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ Erro: DATABASE_URL não configurada!")
        print("   Certifique-se de que PostgreSQL foi adicionado ao Railway")
        return False
    
    # Converter postgresql:// para postgresql+psycopg2://
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    
    try:
        pg_conn = psycopg2.connect(database_url)
        pg_cursor = pg_conn.cursor()
        print("✅ PostgreSQL conectado!")
    except Exception as e:
        print(f"❌ Erro ao conectar PostgreSQL: {e}")
        return False
    
    # Tabelas a migrar
    tables = [
        'usuario',
        'operador',
        'produto',
        'maquina',
        'projeto_produto',
        'obra',
        'obra_produto',
        'modelo_op',
        'op',
        'etapa',
        'tarefa',
        'apontamento',
        'cronograma_item',
        'pendencia_material'
    ]
    
    print("\n📊 Iniciando migração de dados...\n")
    
    migrated_count = 0
    
    for table in tables:
        try:
            # Contar registros no SQLite
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = sqlite_cursor.fetchone()[0]
            
            if count == 0:
                print(f"⏭️  {table}: 0 registros (pulando)")
                continue
            
            # Buscar dados do SQLite
            sqlite_cursor.execute(f"SELECT * FROM {table}")
            rows = sqlite_cursor.fetchall()
            
            # Buscar nomes das colunas
            columns = [description[0] for description in sqlite_cursor.description]
            
            # Limpar tabela no PostgreSQL
            pg_cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
            
            # Inserir dados no PostgreSQL
            if rows:
                placeholders = ','.join(['%s'] * len(columns))
                insert_query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                
                for row in rows:
                    values = [row[col] for col in columns]
                    try:
                        pg_cursor.execute(insert_query, values)
                    except Exception as e:
                        print(f"   ⚠️  Erro ao inserir linha: {e}")
                        continue
            
            pg_conn.commit()
            print(f"✅ {table}: {count} registros migrados")
            migrated_count += count
            
        except Exception as e:
            print(f"❌ Erro ao migrar {table}: {e}")
            pg_conn.rollback()
            continue
    
    # Fechar conexões
    sqlite_conn.close()
    pg_conn.close()
    
    print(f"\n🎉 Migração concluída!")
    print(f"   Total de registros migrados: {migrated_count}")
    print(f"\n✅ Seus dados estão agora no PostgreSQL do Railway!")
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("  MIGRAÇÃO SQLITE → POSTGRESQL")
    print("=" * 60)
    print()
    
    success = migrate_sqlite_to_postgresql()
    
    if success:
        print("\n✅ Tudo pronto! Você pode acessar seu sistema no Railway.")
        sys.exit(0)
    else:
        print("\n❌ Migração falhou. Verifique os erros acima.")
        sys.exit(1)
