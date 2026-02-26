import requests
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv('.env.telegram')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_USER_ID = os.getenv('TELEGRAM_USER_ID')

def enviar_notificacao_telegram(mensagem):
    """
    Envia uma notificação via Telegram
    
    Args:
        mensagem (str): Mensagem a ser enviada
    
    Returns:
        bool: True se enviado com sucesso, False caso contrário
    """
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_USER_ID:
        print("❌ Credenciais do Telegram não configuradas!")
        print("Verifique o arquivo .env.telegram")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    dados = {
        "chat_id": TELEGRAM_USER_ID,
        "text": mensagem,
        "parse_mode": "HTML"
    }
    
    try:
        resposta = requests.post(url, json=dados, timeout=10)
        
        if resposta.status_code == 200:
            print("✅ Notificação enviada com sucesso via Telegram!")
            return True
        else:
            print(f"❌ Erro ao enviar notificação: Status {resposta.status_code}")
            print(f"Resposta: {resposta.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao enviar notificação: {str(e)}")
        return False

def enviar_notificacao_tarefas_atrasadas(tarefas_atrasadas):
    """
    Envia notificação sobre tarefas atrasadas
    
    Args:
        tarefas_atrasadas (list): Lista de dicionários com informações das tarefas
    """
    
    if not tarefas_atrasadas:
        return
    
    # Construir mensagem
    mensagem = "⚠️ <b>TAREFAS ATRASADAS</b> ⚠️\n\n"
    
    for tarefa in tarefas_atrasadas:
        mensagem += f"<b>OP:</b> {tarefa.get('op_numero', 'N/A')}\n"
        mensagem += f"<b>Etapa:</b> {tarefa.get('etapa_nome', 'N/A')}\n"
        mensagem += f"<b>Data Fim:</b> {tarefa.get('data_fim', 'N/A')}\n"
        mensagem += f"<b>Dias Atrasado:</b> {tarefa.get('dias_atrasado', 'N/A')}\n"
        mensagem += "─" * 30 + "\n"
    
    enviar_notificacao_telegram(mensagem)

# Teste rápido
if __name__ == "__main__":
    print("🧪 Testando integração com Telegram...\n")
    
    mensagem_teste = """
🧪 <b>TESTE DE NOTIFICAÇÃO</b> 🧪

Olá! Sua integração com Telegram está funcionando corretamente! ✅

Este é um teste de notificação automática.
    """
    
    enviar_notificacao_telegram(mensagem_teste)
