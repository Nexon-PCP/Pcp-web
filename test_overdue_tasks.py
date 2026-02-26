#!/usr/bin/env python3
"""
Script de teste para verificar tarefas atrasadas e enviar notificações Telegram
Executa a verificação AGORA, sem esperar 5 minutos!
"""

import os
import sys
from datetime import date, datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv('.env.telegram')

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar o app e modelos
from app import app, db, Tarefa
from telegram_notifications import enviar_notificacao_telegram

def testar_tarefas_atrasadas():
    """Testa a verificação de tarefas atrasadas"""
    
    print("\n" + "="*60)
    print("🧪 TESTE DE TAREFAS ATRASADAS")
    print("="*60 + "\n")
    
    with app.app_context():
        hoje = date.today()
        
        # Buscar tarefas atrasadas (excluindo finalizadas e concluídas)
        tarefas_atrasadas = Tarefa.query.filter(
            Tarefa.data_fim_prev < hoje,
            Tarefa.status != "FINALIZADO",
            Tarefa.status != "CONCLUIDO"
        ).all()
        
        print(f"📅 Data de hoje: {hoje.strftime('%d/%m/%Y')}")
        print(f"🔍 Tarefas atrasadas encontradas: {len(tarefas_atrasadas)}\n")
        
        if not tarefas_atrasadas:
            print("✅ Nenhuma tarefa atrasada encontrada!")
            print("\n💡 Dica: Crie uma tarefa com data fim anterior a hoje para testar!\n")
            return
        
        # Enviar notificações
        print("📤 Enviando notificações...\n")
        
        for i, tarefa in enumerate(tarefas_atrasadas, 1):
            dias_atrasada = (hoje - tarefa.data_fim_prev).days
            
            print(f"📋 Tarefa {i}:")
            print(f"   Título: {tarefa.titulo}")
            print(f"   Data Fim: {tarefa.data_fim_prev.strftime('%d/%m/%Y')}")
            print(f"   Dias Atrasada: {dias_atrasada}")
            print(f"   Status: {tarefa.status}")
            
            mensagem = f"""⚠️ <b>TAREFA ATRASADA!</b> ⚠️

📋 <b>Tarefa:</b> {tarefa.titulo}
👤 <b>Responsável:</b> {tarefa.responsavel.nome if tarefa.responsavel else 'Não atribuído'}
📅 <b>Data Fim:</b> {tarefa.data_fim_prev.strftime('%d/%m/%Y')}
⏰ <b>Dias Atrasada:</b> {dias_atrasada}
📊 <b>Status:</b> {tarefa.status}
🔧 <b>OP:</b> {tarefa.etapa.op.numero if tarefa.etapa and tarefa.etapa.op else 'N/A'}
🏗️ <b>Etapa:</b> {tarefa.etapa.nome if tarefa.etapa else 'N/A'}
⏱️ <b>Horas Previstas:</b> {tarefa.horas_previstas} h

⚠️ <b>Ação Necessária!</b>"""
            
            if enviar_notificacao_telegram(mensagem):
                print(f"   ✅ Notificação enviada!\n")
            else:
                print(f"   ❌ Erro ao enviar notificação!\n")
        
        print("="*60)
        print("✅ Teste concluído!")
        print("="*60 + "\n")

if __name__ == "__main__":
    testar_tarefas_atrasadas()
