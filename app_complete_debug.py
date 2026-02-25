"""
PCP Web Application - Production Control Planning System
Versão: 2.0 (PostgreSQL + SQLite compatible)
Python: 3.14.3+
Framework: Flask 3.0.0
ORM: Flask-SQLAlchemy 3.1.1
"""

from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import calendar
import os
from functools import wraps

# ============ INICIALIZAÇÃO ============
app = Flask(__name__)

ETAPAS_FIXAS = ["CORTE", "DOBRA", "PINTURA", "CALDEIRARIA", "MONTAGEM", "START UP"]

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

# ============ MIDDLEWARE DE AUTENTICACAO ============
@app.after_request
def set_security_headers(response):
    """Adicionar headers de segurança e desabilitar cache"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.before_request
def verificar_autenticacao():
    """Verificar se usuário está autenticado antes de cada requisição"""
    rotas_publicas = ['/login', '/static', '/api', '/apresentacao', '/health']
    
    if any(request.path.startswith(rota) for rota in rotas_publicas):
        return
    
    if 'usuario_id' not in session:
        print(f"[AUTH] Acesso negado para {request.remote_addr} em {request.path}")
        return redirect(url_for("login"))
    else:
        usuario = Usuario.query.get(session.get('usuario_id'))
        if usuario:
            session['usuario_email'] = usuario.email
        print(f"[AUTH] Acesso permitido para usuario em {request.path}")

# ============ DECORATOR DE PERMISSOES ============
def requer_permissao(acao):
    """Decorator para verificar permissão do usuário"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                return redirect(url_for("login"))
            
            usuario = Usuario.query.get(session['usuario_id'])
            
            if not usuario:
                session.clear()
                return redirect(url_for("login"))
            
            if not usuario.tem_permissao(acao):
                print(f"[PERMISSAO] Acesso negado para {usuario.email} em {acao}")
                return render_template("erro_permissao.html", mensagem=f"Você não tem permissão para {acao}"), 403
            
            print(f"[PERMISSAO] Acesso permitido para {usuario.email} em {acao}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============ MODELOS DE DADOS ============

class Usuario(db.Model):
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    tipo = db.Column(db.String(20), default="VISUALIZADOR")
    data_criacao = db.Column(db.DateTime, default=datetime.now)
    
    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def tem_permissao(self, acao, etapa_nome=None):
        """Verifica se o usuario tem permissao para uma acao"""
        permissoes = {
            "ADMIN": ["criar_obra", "editar_obra", "deletar_obra", "criar_op", "editar_op", "deletar_op", "criar_tarefa", "editar_tarefa", "deletar_tarefa", "visualizar"],
            "GERENTE": ["criar_op", "editar_op", "criar_tarefa", "editar_tarefa", "visualizar"],
            "OPERADOR": ["editar_tarefa", "visualizar"],
            "ESPECIALISTA": ["criar_tarefa", "editar_tarefa", "deletar_tarefa", "visualizar"],
            "VISUALIZADOR": ["visualizar"]
        }
        if acao not in permissoes.get(self.tipo, []):
            return False
        if self.tipo == "ESPECIALISTA" and etapa_nome:
            etapas_por_email = {
                "estrutura@nexon.com": ["CORTE", "DOBRA", "PINTURA"],
                "caldeiraria@nexon.com": ["CALDEIRARIA"],
                "montagem@nexon.com": ["MONTAGEM"],
                "startup@nexon.com": ["START UP"]
            }
            etapas_permitidas = etapas_por_email.get(self.email, [])
            return etapa_nome in etapas_permitidas
        return True

class Produto(db.Model):
    __tablename__ = "produto"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    ativo = db.Column(db.Boolean, default=True)

class ObraProduto(db.Model):
    __tablename__ = "obra_produto"
    
    obra_id = db.Column(db.Integer, db.ForeignKey("obra.id"), primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), primary_key=True)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    
    produto = db.relationship("Produto")

class Obra(db.Model):
    __tablename__ = "obra"
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50))
    nome = db.Column(db.String(120))
    cliente = db.Column(db.String(120))
    status = db.Column(db.String(20))
    
    data_inicio = db.Column(db.Date)
    prev_fim = db.Column(db.Date)
    fim_real = db.Column(db.Date)
    
    corte_dobra_inicio = db.Column(db.Date)
    corte_dobra_fim = db.Column(db.Date)
    
    montagem_eletro_inicio = db.Column(db.Date)
    montagem_eletro_fim = db.Column(db.Date)
    
    produtos = db.relationship(
        "ObraProduto",
        backref="obra",
        cascade="all, delete-orphan"
    )
    
    @property
    def percentual_calc(self):
        """Calcula o percentual total da obra baseado nas OPs"""
        if not self.ops:
            return 0.0
        
        total_ops = len(self.ops)
        if total_ops == 0:
            return 0.0
        
        soma_percentuais = sum(op.percentual_calc for op in self.ops)
        percentual_medio = soma_percentuais / total_ops
        return round(percentual_medio, 2)
    
    @property
    def status_calculado(self):
        """Retorna o status calculado baseado no percentual"""
        percentual = self.percentual_calc
        
        if percentual >= 100:
            return "CONCLUIDA"
        
        if percentual > 0:
            return "EM_EXECUCAO"
        
        return "ABERTA"

class OP(db.Model):
    __tablename__ = "op"
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), nullable=False, unique=True)
    
    obra_id = db.Column(db.Integer, db.ForeignKey("obra.id"), nullable=False)
    produto = db.Column(db.String(120))
    quantidade = db.Column(db.Integer, default=1)
    
    data_emissao = db.Column(db.Date, default=date.today)
    prev_inicio = db.Column(db.Date)
    prev_fim = db.Column(db.Date)
    
    percentual = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default="ABERTA")
    
    obra = db.relationship("Obra", backref=db.backref("ops", lazy=True))
    
    @property
    def percentual_calc(self):
        """Calcula percentual baseado em horas de tarefas CONCLUIDO / horas totais"""
        todas_tarefas = []
        for etapa in self.etapas:
            todas_tarefas.extend(etapa.tarefas)
        
        if not todas_tarefas:
            return 0.0
        
        horas_totais = sum(tarefa.horas_previstas for tarefa in todas_tarefas)
        horas_concluidas = sum(
            tarefa.horas_previstas for tarefa in todas_tarefas 
            if tarefa.status == "CONCLUIDO"
        )
        
        if horas_totais == 0:
            return 0.0
        
        percentual = (horas_concluidas / horas_totais) * 100
        return round(percentual)
    
    @property
    def status_calc(self):
        if self.percentual >= 100:
            return "CONCLUIDA"
        if self.prev_fim and date.today() > self.prev_fim:
            return "ATRASADA"
        if self.percentual > 0:
            return "EM PRODUCAO"
        return "ABERTA"

class Etapa(db.Model):
    __tablename__ = "etapa"
    
    id = db.Column(db.Integer, primary_key=True)
    
    op_id = db.Column(db.Integer, db.ForeignKey("op.id"), nullable=False)
    nome = db.Column(db.String(80), nullable=False)
    
    data_inicio = db.Column(db.DateTime)
    data_fim = db.Column(db.DateTime)
    
    horas_planejadas = db.Column(db.Float, default=0.0)
    responsavel_id = db.Column(db.Integer, db.ForeignKey("operador.id"), nullable=True)
    
    percentual = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default="PLANEJADO")
    
    op = db.relationship("OP", backref=db.backref("etapas", lazy=True, cascade="all,delete"))
    responsavel = db.relationship("Operador", backref=db.backref("etapas_responsavel", lazy=True))
    
    @property
    def horas_realizadas(self):
        """Calcula horas realizadas a partir dos apontamentos"""
        aponts = Apontamento.query.filter_by(etapa_id=self.id).filter_by(status="FINALIZADO").all()
        total = 0
        for ap in aponts:
            if ap.fim and ap.inicio:
                duracao = (ap.fim - ap.inicio).total_seconds() / 3600
                total += duracao
        return round(total, 2)

class Operador(db.Model):
    __tablename__ = "operador"
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    matricula = db.Column(db.String(50))
    ativo = db.Column(db.Boolean, default=True)

class Maquina(db.Model):
    __tablename__ = "maquina"
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    setor = db.Column(db.String(80))
    ativo = db.Column(db.Boolean, default=True)

class Apontamento(db.Model):
    __tablename__ = "apontamento"
    
    id = db.Column(db.Integer, primary_key=True)
    
    obra_id = db.Column(db.Integer, db.ForeignKey("obra.id"), nullable=False)
    op_id = db.Column(db.Integer, db.ForeignKey("op.id"), nullable=False)
    etapa_id = db.Column(db.Integer, db.ForeignKey("etapa.id"), nullable=False)
    
    operador_id = db.Column(db.Integer, db.ForeignKey("operador.id"), nullable=False)
    maquina_id = db.Column(db.Integer, db.ForeignKey("maquina.id"), nullable=True)
    
    inicio = db.Column(db.DateTime, default=datetime.now)
    fim = db.Column(db.DateTime)
    
    qtd_boa = db.Column(db.Integer, default=0)
    qtd_refugo = db.Column(db.Integer, default=0)
    obs = db.Column(db.String(300))
    
    status = db.Column(db.String(30), default="EM_ANDAMENTO")
    
    obra = db.relationship("Obra")
    op = db.relationship("OP")
    etapa = db.relationship("Etapa")
    operador = db.relationship("Operador")
    maquina = db.relationship("Maquina")
    
    @property
    def horas_gastas(self):
        """Calcula horas gastas neste apontamento"""
        if self.fim and self.inicio:
            duracao = (self.fim - self.inicio).total_seconds() / 3600
            return round(duracao, 2)
        return 0.0

class CronogramaItem(db.Model):
    __tablename__ = "cronograma_item"
    
    id = db.Column(db.Integer, primary_key=True)
    obra_id = db.Column(db.Integer, db.ForeignKey("obra.id"), nullable=False)
    
    titulo = db.Column(db.String(160), nullable=False)
    responsavel = db.Column(db.String(120))
    
    inicio_prev = db.Column(db.Date)
    fim_prev = db.Column(db.Date)
    
    status = db.Column(db.String(30), default="PLANEJADO")
    obs = db.Column(db.String(300))
    
    obra = db.relationship("Obra", backref=db.backref("cronograma", lazy=True, cascade="all,delete"))

class ModeloOP(db.Model):
    __tablename__ = "modelo_op"
    
    id = db.Column(db.Integer, primary_key=True)
    produto = db.Column(db.String(120), nullable=False)
    nome = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.String(500))
    
    dados = db.Column(db.JSON, nullable=False)
    
    data_criacao = db.Column(db.DateTime, default=datetime.now)

class Tarefa(db.Model):
    __tablename__ = "tarefa"
    
    id = db.Column(db.Integer, primary_key=True)
    
    etapa_id = db.Column(db.Integer, db.ForeignKey("etapa.id"), nullable=False)
    responsavel_id = db.Column(db.Integer, db.ForeignKey("operador.id"), nullable=True)
    
    numero = db.Column(db.String(10))
    titulo = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.String(500))
    
    horas_previstas = db.Column(db.Float, default=0.0)
    horas_realizadas = db.Column(db.Float, default=0.0)
    
    data_inicio_prev = db.Column(db.Date)
    data_fim_prev = db.Column(db.Date)
    
    data_inicio_real = db.Column(db.DateTime)
    data_fim_real = db.Column(db.DateTime)
    
    status = db.Column(db.String(30), default="PLANEJADO")
    
    peso_percentual = db.Column(db.Float, default=0.0)
    justificativa_pausa = db.Column(db.String(500))
    
    etapa = db.relationship("Etapa", backref=db.backref("tarefas", lazy=True, cascade="all,delete"))
    responsavel = db.relationship("Operador", backref=db.backref("tarefas", lazy=True))
    
    @property
    def status_calculado(self):
        """Retorna o status calculado baseado na data de fim"""
        if self.status == "CONCLUIDO":
            return "CONCLUIDO"
        
        if self.status == "EM_EXECUCAO":
            return "EM_EXECUCAO"
        
        if self.status == "PAUSADO":
            return "PAUSADO"
        
        if self.data_fim_prev:
            if date.today() > self.data_fim_prev:
                return "ATRASADA"
        
        return "PLANEJADO"
    
    @property
    def percentual(self):
        """Retorna o percentual de conclusão da tarefa"""
        if self.status == "CONCLUIDO":
            return 100.0
        if self.status == "PAUSADO":
            return 0.0
        if self.status == "EM_EXECUCAO":
            return 50.0
        return 0.0

class PendenciaMaterial(db.Model):
    __tablename__ = "pendencia_material"
    
    id = db.Column(db.Integer, primary_key=True)
    
    obra_id = db.Column(db.Integer, db.ForeignKey("obra.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    
    descricao = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(30), default="PENDENTE")
    
    data_criacao = db.Column(db.DateTime, default=datetime.now)
    data_atualizacao = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    obra = db.relationship("Obra", backref=db.backref("pendencias_materiais", lazy=True, cascade="all,delete"))
    produto = db.relationship("Produto", backref=db.backref("pendencias_materiais", lazy=True))

class ProjetoProduto(db.Model):
    __tablename__ = "projeto_produto"
    
    id = db.Column(db.Integer, primary_key=True)
    
    obra_id = db.Column(db.Integer, db.ForeignKey("obra.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    
    link = db.Column(db.String(500), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    
    data_criacao = db.Column(db.DateTime, default=datetime.now)
    data_atualizacao = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    obra = db.relationship("Obra", backref=db.backref("projetos", lazy=True, cascade="all,delete"))
    produto = db.relationship("Produto", backref=db.backref("projetos", lazy=True))

# ============ FUNÇÕES AUXILIARES ============

def parse_date(s):
    """Parse string para date"""
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()

def calcular_data_fim(data_inicio, horas_previstas, horas_por_dia=9):
    """Calcula a data de fim baseada na data de inicio e horas previstas"""
    if not data_inicio or not horas_previstas or horas_previstas <= 0:
        return data_inicio
    
    horas_restantes = float(horas_previstas)
    data_atual = data_inicio
    
    while horas_restantes > 0:
        if data_atual.weekday() < 5:
            horas_restantes -= horas_por_dia
        
        if horas_restantes > 0:
            data_atual += timedelta(days=1)
    
    return data_atual

# ============ ROTAS PRINCIPAIS ============

@app.route("/")
def index():
    """Página inicial"""
    if 'usuario_id' in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/health")
def health():
    """Health check para Railway"""
    return jsonify({"status": "healthy", "database": "PostgreSQL" if "postgresql" in app.config["SQLALCHEMY_DATABASE_URI"] else "SQLite"}), 200

@app.route("/login", methods=["GET", "POST"])
def login():
    """Página de login"""
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and usuario.verificar_senha(senha) and usuario.ativo:
            session['usuario_id'] = usuario.id
            session['usuario_email'] = usuario.email
            session['usuario_tipo'] = usuario.tipo
            session.permanent = True
            print(f"[LOGIN] Usuário {email} logado com sucesso")
            return redirect(url_for("dashboard"))
        else:
            print(f"[LOGIN] Falha de login para {email}")
            return render_template("login.html", erro="Email ou senha inválidos")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Fazer logout"""
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@requer_permissao("visualizar")
def dashboard():
    """Dashboard principal"""
    obras = Obra.query.all()
    ops = OP.query.all()
    maquinas = Maquina.query.all()
    
    return render_template(
        "dashboard.html",
        obras=obras,
        ops=ops,
        maquinas=maquinas
    )

# ============ ROTAS DE API ============

@app.route("/api/apresentacao")
def api_apresentacao():
    """API de apresentação do sistema"""
    return jsonify({
        "status": "ok",
        "message": "PCP Web API - Servidor rodando com sucesso!",
        "database": "PostgreSQL" if "postgresql" in app.config["SQLALCHEMY_DATABASE_URI"] else "SQLite",
        "version": "2.0"
    })

@app.route("/api/dashboard")
def api_dashboard():
    """API para dashboard"""
    try:
        obras = Obra.query.all()
        ops = OP.query.all()
        maquinas = Maquina.query.all()
        
        return jsonify({
            "total_obras": len(obras),
            "total_ops": len(ops),
            "maquinas_producao": [{"id": m.id, "nome": m.nome, "status": m.ativo} for m in maquinas]
        })
    except Exception as e:
        print(f"[API] Erro em /api/dashboard: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route("/api/obras")
def api_obras():
    """API para listar obras"""
    try:
        obras = Obra.query.all()
        return jsonify([{
            "id": obra.id,
            "nome": obra.nome,
            "cliente": obra.cliente,
            "status": obra.status
        } for obra in obras])
    except Exception as e:
        print(f"[API] Erro em /api/obras: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route("/api/ops")
def api_ops():
    """API para listar OPs"""
    try:
        ops = OP.query.all()
        return jsonify([{
            "id": op.id,
            "numero": op.numero,
            "produto": op.produto,
            "quantidade": op.quantidade,
            "status": op.status,
            "percentual": op.percentual
        } for op in ops])
    except Exception as e:
        print(f"[API] Erro em /api/ops: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route("/api/ops/<int:op_id>")
def api_op_detalhes(op_id):
    """API para detalhes de uma OP"""
    try:
        op = OP.query.get_or_404(op_id)
        return jsonify({
            "id": op.id,
            "numero": op.numero,
            "produto": op.produto,
            "quantidade": op.quantidade,
            "status": op.status,
            "percentual": op.percentual,
            "etapas": [{
                "id": etapa.id,
                "nome": etapa.nome,
                "status": etapa.status,
                "percentual": etapa.percentual,
                "tarefas": [{
                    "id": tarefa.id,
                    "titulo": tarefa.titulo,
                    "status": tarefa.status,
                    "horas_previstas": tarefa.horas_previstas,
                    "horas_realizadas": tarefa.horas_realizadas
                } for tarefa in etapa.tarefas]
            } for etapa in op.etapas]
        })
    except Exception as e:
        print(f"[API] Erro em /api/ops/{op_id}: {e}")
        return jsonify({"erro": str(e)}), 500

# ============ CRIAR TABELAS ============

def criar_tabelas():
    """Criar todas as tabelas no banco de dados"""
    with app.app_context():
        try:
            db.create_all()
            print("[DB] Tabelas criadas com sucesso!")
        except Exception as e:
            print(f"[DB] Erro ao criar tabelas: {e}")

# ============ INICIALIZAR APLICAÇÃO ============

if __name__ == "__main__":
    criar_tabelas()
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
