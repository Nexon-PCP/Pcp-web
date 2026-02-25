"""
PCP Web Application - Minimal Version
Versão: 1.0 (PostgreSQL + SQLite compatible)
Python: 3.14.3+
Framework: Flask 3.0.0
ORM: Flask-SQLAlchemy 3.1.1
"""

from datetime import date, datetime, timedelta
from flask import Flask, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os

# ============ INICIALIZAÇÃO ============
app = Flask(__name__)

# ============ CONFIGURAÇÃO DO BANCO DE DADOS ============
database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pcp.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', 'pcp-secret-dev')
app.config["SESSION_COOKIE_SECURE"] = os.environ.get('FLASK_ENV') == 'production'
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 86400

db = SQLAlchemy(app)

# ============ CRIAR TABELAS NA PRIMEIRA EXECUÇÃO ============
with app.app_context():
    try:
        db.create_all()
        print("[DB] Tabelas criadas com sucesso!")
    except Exception as e:
        print(f"[DB] Erro ao criar tabelas: {e}")
        pass

# ============ MODELOS DE DADOS ============

class Usuario(db.Model):
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(50), default='VISUALIZADOR')
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.now)
    
    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

class Obra(db.Model):
    __tablename__ = 'obra'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    cliente = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), default='Aberta')
    data_inicio = db.Column(db.Date)
    data_fim = db.Column(db.Date)
    data_criacao = db.Column(db.DateTime, default=datetime.now)

# ============ ROTAS ============

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Testar conexão com banco de dados
        db.session.execute('SELECT 1')
        db.session.commit()
        database_type = 'PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite'
        return jsonify({
            'status': 'healthy',
            'database': database_type,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/apresentacao', methods=['GET'])
def apresentacao():
    """API endpoint para apresentação"""
    try:
        obras_count = Obra.query.count()
        usuarios_count = Usuario.query.count()
        
        return jsonify({
            'status': 'ok',
            'mensagem': 'PCP Web Application - Versão 1.0',
            'obras': obras_count,
            'usuarios': usuarios_count,
            'database': 'PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        if not email or not senha:
            return jsonify({'error': 'Email e senha são obrigatórios'}), 400
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and usuario.verificar_senha(senha):
            session['usuario_id'] = usuario.id
            session['usuario_email'] = usuario.email
            return redirect(url_for('obras'))
        else:
            return jsonify({'error': 'Email ou senha inválidos'}), 401
    
    # GET request - retornar formulário HTML simples
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login - PCP</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; }
            form { max-width: 300px; margin: 0 auto; }
            input { width: 100%; padding: 10px; margin: 10px 0; }
            button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>PCP - Login</h1>
        <form method="post">
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="senha" placeholder="Senha" required>
            <button type="submit">Entrar</button>
        </form>
        <p><a href="/api/apresentacao">API Status</a></p>
    </body>
    </html>
    ''', 200

@app.route('/obras', methods=['GET'])
def obras():
    """Página de obras"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    try:
        obras = Obra.query.all()
        
        # Retornar JSON
        return jsonify({
            'status': 'ok',
            'total': len(obras),
            'obras': [
                {
                    'id': obra.id,
                    'codigo': obra.codigo,
                    'nome': obra.nome,
                    'cliente': obra.cliente,
                    'status': obra.status,
                    'data_inicio': obra.data_inicio.isoformat() if obra.data_inicio else None,
                    'data_fim': obra.data_fim.isoformat() if obra.data_fim else None
                }
                for obra in obras
            ]
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Dashboard"""
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    try:
        obras_count = Obra.query.count()
        usuarios_count = Usuario.query.count()
        
        return jsonify({
            'status': 'ok',
            'obras': obras_count,
            'usuarios': usuarios_count,
            'usuario_email': session.get('usuario_email')
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/logout', methods=['GET'])
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))

# ============ ERROR HANDLERS ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Rota não encontrada'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Erro interno do servidor'}), 500

# ============ INICIAR APLICAÇÃO ============

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
