from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import calendar
import os

app = Flask(__name__)

ETAPAS_FIXAS = ["CORTE", "DOBRA", "PINTURA", "CALDEIRARIA", "MONTAGEM", "START UP"]

# ============ CONFIGURAÇÃO DO BANCO DE DADOS ============
# Usar DATABASE_URL do Railway se disponível, senão usar SQLite local
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Railway usa postgresql://, mas SQLAlchemy precisa de postgresql+psycopg2://
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pcp.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', 'pcp-secret')
app.config["SESSION_COOKIE_SECURE"] = os.environ.get('FLASK_ENV') == 'production'
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 24 horas

db = SQLAlchemy(app)

# ============ CRIAR TABELAS ============
def criar_tabelas():
    """Criar todas as tabelas no banco de dados"""
    with app.app_context():
        try:
            db.create_all()
            print("[DB] Tabelas criadas com sucesso!")
        except Exception as e:
            print(f"[DB] Erro ao criar tabelas: {e}")

# ============ ROTAS BÁSICAS ============
@app.route("/")
def index():
    """Página inicial"""
    return jsonify({"status": "ok", "message": "PCP Web API - Servidor rodando com sucesso!"})

@app.route("/health")
def health():
    """Health check para Railway"""
    return jsonify({"status": "healthy"}), 200

@app.route("/api/dashboard")
def api_dashboard():
    """API para dashboard"""
    return jsonify({
        "total_obras": 0,
        "total_ops": 0,
        "total_apontamentos": 0,
        "maquinas_producao": []
    })

# ============ INICIALIZAR APLICAÇÃO ============
if __name__ == "__main__":
    # Criar tabelas ao iniciar
    criar_tabelas()
    
    # Iniciar servidor
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
