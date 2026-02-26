#!/usr/bin/env python3
"""
Script para testar se o scheduler está rodando
"""

import sys
import os
import time
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar o app
from app import app, scheduler

print("\n" + "="*60)
print("🧪 TESTE DO SCHEDULER")
print("="*60 + "\n")

print(f"⏰ Hora atual: {datetime.now().strftime('%H:%M:%S')}")
print(f"🔄 Scheduler rodando? {scheduler.running}")
print(f"📋 Jobs agendados: {len(scheduler.get_jobs())}")

if scheduler.get_jobs():
    print("\n📌 Jobs:")
    for job in scheduler.get_jobs():
        print(f"   - {job.name}")
        print(f"     ID: {job.id}")
        print(f"     Próxima execução: {job.next_run_time}")
else:
    print("\n❌ Nenhum job agendado!")

print("\n" + "="*60)
print("🔍 Aguardando 6 minutos para verificar se roda...")
print("="*60 + "\n")

# Aguardar e monitorar
for i in range(6):
    print(f"⏳ {i+1}/6 minutos... ({datetime.now().strftime('%H:%M:%S')})")
    time.sleep(60)

print("\n✅ Teste concluído!")
print("Se você recebeu uma notificação no Telegram, o scheduler está funcionando! 🎉\n")
