"""
Configuração para Railway
Adicione este arquivo ao seu app.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

class RailwayConfig:
    """Configuração para Railway"""
    
    # Banco de dados
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///pcp.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
    DEBUG = os.environ.get('FLASK_DEBUG', False)
    
    # AWS S3 (opcional)
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET')
    AWS_S3_REGION = os.environ.get('AWS_S3_REGION', 'us-east-1')
    
    # Telegram (opcional)
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
    
    # WhatsApp (opcional)
    WHATSAPP_API_TOKEN = os.environ.get('WHATSAPP_API_TOKEN')
    WHATSAPP_PHONE_NUMBER = os.environ.get('WHATSAPP_PHONE_NUMBER')
