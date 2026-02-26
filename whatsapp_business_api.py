"""
WhatsApp Business API Notifier - Envia notificações via WhatsApp Business API
Versão Oficial e Confiável
"""

import requests
import json
import os
from datetime import date, datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv(".env.whatsapp")


class WhatsAppBusinessNotifier:
    """Classe para enviar notificações via WhatsApp Business API"""
    
    def __init__(self):
        """Inicializa o notificador"""
        self.api_token = os.getenv("WHATSAPP_API_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.business_account_id = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
        self.recipient_phone = os.getenv("WHATSAPP_RECIPIENT_PHONE", "+55 11 99999-9999")
        self.api_url = f"https://graph.instagram.com/v18.0/{self.phone_number_id}/messages"
        
        if not all([self.api_token, self.phone_number_id, self.business_account_id]):
            print("❌ Credenciais do WhatsApp Business não configuradas!")
            print("   Verifique o arquivo .env.whatsapp")
            return
        
        print("✅ WhatsApp Business Notifier Inicializado!")
        print(f"   Telefone ID: {self.phone_number_id}")
        print(f"   Conta Business ID: {self.business_account_id}")
    
    def send_message(self, message, recipient_phone=None):
        """
        Envia uma mensagem via WhatsApp Business API
        
        Args:
            message: Texto da mensagem
            recipient_phone: Número de telefone do destinatário (com código do país)
        
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            if not recipient_phone:
                recipient_phone = self.recipient_phone
            
            # Remover caracteres especiais do número
            recipient_phone_clean = recipient_phone.replace(" ", "").replace("-", "").replace("+", "")
            
            # Preparar payload
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone_clean,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            # Headers
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            print(f"\n📤 Enviando mensagem para {recipient_phone}...")
            print(f"   URL: {self.api_url}")
            
            # Enviar requisição
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            # Verificar resposta
            if response.status_code == 200:
                print(f"✅ Mensagem enviada com sucesso!")
                return True
            else:
                print(f"❌ Erro ao enviar mensagem:")
                print(f"   Status: {response.status_code}")
                print(f"   Resposta: {response.text}")
                return False
        
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem: {str(e)}")
            return False
    
    def send_template_message(self, template_name, language="pt_BR", parameters=None, recipient_phone=None):
        """
        Envia uma mensagem de template via WhatsApp Business API
        
        Args:
            template_name: Nome do template
            language: Idioma do template (padrão: pt_BR)
            parameters: Parâmetros do template (lista)
            recipient_phone: Número de telefone do destinatário
        
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            if not recipient_phone:
                recipient_phone = self.recipient_phone
            
            # Remover caracteres especiais do número
            recipient_phone_clean = recipient_phone.replace(" ", "").replace("-", "").replace("+", "")
            
            # Preparar payload
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone_clean,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": language
                    }
                }
            }
            
            # Adicionar parâmetros se fornecidos
            if parameters:
                payload["template"]["components"] = [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": str(p)} for p in parameters]
                    }
                ]
            
            # Headers
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json"
            }
            
            print(f"\n📤 Enviando template '{template_name}' para {recipient_phone}...")
            
            # Enviar requisição
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            # Verificar resposta
            if response.status_code == 200:
                print(f"✅ Template enviado com sucesso!")
                return True
            else:
                print(f"❌ Erro ao enviar template:")
                print(f"   Status: {response.status_code}")
                print(f"   Resposta: {response.text}")
                return False
        
        except Exception as e:
            print(f"❌ Erro ao enviar template: {str(e)}")
            return False


# Função para enviar notificação de tarefa atrasada
def enviar_notificacao_tarefa_atrasada(tarefa):
    """
    Envia notificação de tarefa atrasada via WhatsApp
    
    Args:
        tarefa: Objeto Tarefa do banco de dados
    """
    try:
        notifier = WhatsAppBusinessNotifier()
        
        dias_atrasada = (date.today() - tarefa.data_fim_prev).days
        
        mensagem = f"""🚨 TAREFA ATRASADA!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Tarefa: {tarefa.titulo}
👤 Responsável: {tarefa.responsavel.nome if tarefa.responsavel else 'Não atribuído'}
📅 Data Fim: {tarefa.data_fim_prev.strftime('%d/%m/%Y')}
⏰ Dias Atrasada: {dias_atrasada}
📊 Status: {tarefa.status}
🔧 OP: {tarefa.etapa.op.numero if tarefa.etapa and tarefa.etapa.op else 'N/A'}
🏗️ Etapa: {tarefa.etapa.nome if tarefa.etapa else 'N/A'}
⏱️ Horas Previstas: {tarefa.horas_previstas} h

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Ação Necessária!"""
        
        return notifier.send_message(mensagem)
    
    except Exception as e:
        print(f"❌ Erro ao enviar notificação: {str(e)}")
        return False


# Teste
if __name__ == "__main__":
    notifier = WhatsAppBusinessNotifier()
    
    # Testar envio de mensagem
    mensagem_teste = """✅ Teste de Notificação

Olá! Esta é uma mensagem de teste da API do WhatsApp Business.

Se você recebeu esta mensagem, a configuração está funcionando! 🎉"""
    
    notifier.send_message(mensagem_teste)
