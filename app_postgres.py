"""
PCP WEB - Configurado para PostgreSQL
Versão para Railway com PostgreSQL
"""

from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import calendar
import os

app = Flask(__name__)

ETAPAS_FIXAS = ["CORTE", "DOBRA", "PINTURA", "CALDEIRARIA", "MONTAGEM", "START UP"]

# ============================================================
# CONFIGURAÇÃO DE BANCO DE DADOS
# ============================================================

# Usar DATABASE_URL do Railway em produção, SQLite em desenvolvimento
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Produção: PostgreSQL no Railway
    # Converter postgresql:// para postgresql+psycopg2://
    if DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://', 1)
    
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    print("[DB] Usando PostgreSQL (Railway)")
else:
    # Desenvolvimento: SQLite local
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pcp.db"
    print("[DB] Usando SQLite (Local)")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "pcp-secret"
app.config["SESSION_COOKIE_SECURE"] = False  # False para desenvolvimento local
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 24 horas

db = SQLAlchemy(app)


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
    rotas_publicas = ['/login', '/static', '/api', '/apresentacao']
    
    # Permitir acesso a rotas públicas
    if any(request.path.startswith(rota) for rota in rotas_publicas):
        return
    
    # Verificar se usuário está na sessão
    if 'usuario_id' not in session:
        print(f"[AUTH] Acesso negado para {request.remote_addr} em {request.path}")
        return redirect(url_for("login"))
    else:
        # Guardar email na sessão para uso no template de erro
        usuario = Usuario.query.get(session.get('usuario_id'))
        if usuario:
            session['usuario_email'] = usuario.email
        print(f"[AUTH] Acesso permitido para usuario em {request.path}")


# ============ DECORATOR DE PERMISSOES ============
from functools import wraps

def requer_permissao(acao):
    """Decorator para verificar permissão do usuário"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar se usuário está autenticado
            if 'usuario_id' not in session:
                return redirect(url_for("login"))
            
            # Obter usuário
            usuario = Usuario.query.get(session['usuario_id'])
            
            if not usuario:
                session.clear()
                return redirect(url_for("login"))
            
            # Verificar permissão
            if not usuario.tem_permissao(acao):
                print(f"[PERMISSAO] Acesso negado para {usuario.email} em {acao}")
                return render_template("erro_permissao.html", mensagem=f"Você não tem permissão para {acao}"), 403
            
            print(f"[PERMISSAO] Acesso permitido para {usuario.email} em {acao}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============ MODELOS ============
class ObraProduto(db.Model):
    __tablename__ = "obra_produto"

    obra_id = db.Column(db.Integer, db.ForeignKey("obra.id"), primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), primary_key=True)

    quantidade = db.Column(db.Integer, nullable=False, default=1)

    produto = db.relationship("Produto")


class Produto(db.Model):
    __tablename__ = "produto"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    ativo = db.Column(db.Boolean, default=True)


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

    # Datas para Corte/Dobra
    corte_dobra_inicio = db.Column(db.Date)
    corte_dobra_fim = db.Column(db.Date)

    # Datas para Montagem Eletromecanica
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
        
        # Somar percentuais calculados de todas as OPs (nao o valor armazenado)
        soma_percentuais = sum(op.percentual_calc for op in self.ops)
        percentual_medio = soma_percentuais / total_ops
        return round(percentual_medio, 2)
    
    @property
    def status_calculado(self):
        """Retorna o status calculado baseado no percentual"""
        percentual = self.percentual_calc
        
        # Se 100% concluido
        if percentual >= 100:
            return "CONCLUIDA"
        
        # Se em execucao (entre 0% e 100%)
        if percentual > 0:
            return "EM_EXECUCAO"
        
        # Se nao iniciado
        return "ABERTA"


class Usuario(db.Model):
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    tipo = db.Column(db.String(20), default="VISUALIZADOR")  # ADMIN, GERENTE, OPERADOR, VISUALIZADOR, ESPECIALISTA

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


class OP(db.Model):
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
        # Buscar todas as tarefas da OP através de suas etapas
        todas_tarefas = []
        for etapa in self.etapas:
            todas_tarefas.extend(etapa.tarefas)
        
        # Se não há tarefas, retornar 0
        if not todas_tarefas:
            return 0.0
        
        # Somar horas previstas totais e horas de tarefas concluídas
        horas_totais = sum(tarefa.horas_previstas for tarefa in todas_tarefas)
        horas_concluidas = sum(
            tarefa.horas_previstas for tarefa in todas_tarefas 
            if tarefa.status == "CONCLUIDO"
        )
        
        # Se não há horas previstas, retornar 0
        if horas_totais == 0:
            return 0.0
        
        # Calcular percentual: horas de tarefas concluídas / horas totais * 100
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
    id = db.Column(db.Integer, primary_key=True)

    op_id = db.Column(db.Integer, db.ForeignKey("op.id"), nullable=False)
    nome = db.Column(db.String(80), nullable=False)

    data_inicio = db.Column(db.DateTime)
    data_fim = db.Column(db.DateTime)
    
    # NOVOS CAMPOS PARA GESTÃO DE TEMPO
    horas_planejadas = db.Column(db.Float, default=0.0)
    responsavel_id = db.Column(db.Integer, db.ForeignKey("operador.id"), nullable=True)

    percentual = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default="PLANEJADO")  # PLANEJADO / EXECUCAO / CONCLUIDO

    op = db.relationship("OP", backref=db.backref("etapas", lazy=True, cascade="all,delete"))
    responsavel = db.relationship("Operador", backref=db.backref("etapas_responsavel", lazy=True))
    
    @property
    def horas_realizadas(self):
        """Calcula horas realizadas a partir dos apontamentos"""
        aponts = Apontamento.query.filter_by(etapa_id=self.id).filter_by(status="FINALIZADO").all()
        total = 0
        for ap in aponts:
            if ap.fim and ap.inicio:
                duracao = (ap.fim - ap.inicio).total_seconds() / 3600  # converte para horas
                total += duracao
        return round(total, 2)


class Operador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    matricula = db.Column(db.String(50))
    ativo = db.Column(db.Boolean, default=True)


class Maquina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    setor = db.Column(db.String(80))
    ativo = db.Column(db.Boolean, default=True)


class Apontamento(db.Model):
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

    status = db.Column(db.String(30), default="EM_ANDAMENTO")  # EM_ANDAMENTO / FINALIZADO

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
    id = db.Column(db.Integer, primary_key=True)
    obra_id = db.Column(db.Integer, db.ForeignKey("obra.id"), nullable=False)

    titulo = db.Column(db.String(160), nullable=False)
    responsavel = db.Column(db.String(120))

    inicio_prev = db.Column(db.Date)
    fim_prev = db.Column(db.Date)

    status = db.Column(db.String(30), default="PLANEJADO")  # PLANEJADO / EM_EXECUCAO / CONCLUIDO / ATRASADO
    obs = db.Column(db.String(300))

    obra = db.relationship("Obra", backref=db.backref("cronograma", lazy=True, cascade="all,delete"))


# MODELO PARA TEMPLATES DE OP POR PRODUTO
class ModeloOP(db.Model):
    __tablename__ = "modelo_op"
    
    id = db.Column(db.Integer, primary_key=True)
    produto = db.Column(db.String(120), nullable=False)
    nome = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.String(500))
    
    # Armazenar estrutura de etapas e tarefas em JSON
    dados = db.Column(db.JSON, nullable=False)
    
    data_criacao = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<ModeloOP {self.produto} - {self.nome}>'


# NOVO MODELO PARA TAREFAS (opcional, para rastreamento mais detalhado)
class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    etapa_id = db.Column(db.Integer, db.ForeignKey("etapa.id"), nullable=False)
    responsavel_id = db.Column(db.Integer, db.ForeignKey("operador.id"), nullable=True)
    
    numero = db.Column(db.String(10))  # Numero da tarefa (ex: 1.1, 1.2, 2.1...)
    titulo = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.String(500))
    
    horas_previstas = db.Column(db.Float, default=0.0)
    horas_realizadas = db.Column(db.Float, default=0.0)
    
    data_inicio_prev = db.Column(db.Date)
    data_fim_prev = db.Column(db.Date)
    
    data_inicio_real = db.Column(db.DateTime)
    data_fim_real = db.Column(db.DateTime)
    
    status = db.Column(db.String(30), default="PLANEJADO")  # PLANEJADO / EM_EXECUCAO / PAUSADO / CONCLUIDO
    
    peso_percentual = db.Column(db.Float, default=0.0)  # Peso do percentual da tarefa na OP
    justificativa_pausa = db.Column(db.String(500))  # Justificativa de pausa
    
    etapa = db.relationship("Etapa", backref=db.backref("tarefas", lazy=True, cascade="all,delete"))
    responsavel = db.relationship("Operador", backref=db.backref("tarefas", lazy=True))
    
    @property
    def status_calculado(self):
        """Retorna o status calculado baseado na data de fim"""
        # Se a tarefa foi concluída, mantém o status CONCLUIDO
        if self.status == "CONCLUIDO":
            return "CONCLUIDO"
        
        # Se a tarefa está em execução, mantém o status EM_EXECUCAO
        if self.status == "EM_EXECUCAO":
            return "EM_EXECUCAO"
        
        # Se a tarefa está pausada, mantém o status PAUSADO
        if self.status == "PAUSADO":
            return "PAUSADO"
        
        # Se tem data de fim prevista, verifica se está atrasada
        if self.data_fim_prev:
            from datetime import date
            if date.today() > self.data_fim_prev:
                return "ATRASADA"
        
        # Caso contrário, retorna PLANEJADO
        return "PLANEJADO"
    
    @property
    def percentual(self):
        """Retorna o percentual de conclusão da tarefa"""
        if self.status == "CONCLUIDO":
            return 100.0
        if self.status == "PAUSADO":
            return 0.0
        if self.status == "EM_EXECUCAO":
            return 50.0  # Em execução = 50%
        return 0.0  # Planejado = 0%


class PendenciaMaterial(db.Model):
    __tablename__ = "pendencia_material"
    
    id = db.Column(db.Integer, primary_key=True)
    
    obra_id = db.Column(db.Integer, db.ForeignKey("obra.id"), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey("produto.id"), nullable=False)
    
    descricao = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(30), default="PENDENTE")  # PENDENTE / RECEBIDO / CANCELADO
    
    data_criacao = db.Column(db.DateTime, default=datetime.now)
    data_atualizacao = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    obra = db.relationship("Obra", backref=db.backref("pendencias_materiais", lazy=True, cascade="all,delete"))
    produto = db.relationship("Produto", backref=db.backref("pendencias_materiais", lazy=True))
    
    def __repr__(self):
        return f'<PendenciaMaterial {self.obra.nome} - {self.produto.nome}>'


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
    
    def __repr__(self):
        return f'<ProjetoProduto {self.obra.nome} - {self.produto.nome}>'


# ============================================================
# HEALTH CHECK ENDPOINT
# ============================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint para Railway"""
    try:
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# ============================================================
# PLACEHOLDER PARA ROTAS
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Rota de login - Implementar conforme original"""
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and usuario.verificar_senha(senha):
            session['usuario_id'] = usuario.id
            session['usuario_email'] = usuario.email
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', erro='Email ou senha inválidos'), 401
    
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    """Rota do dashboard - Implementar conforme original"""
    return render_template('dashboard.html')


@app.route('/logout')
def logout():
    """Fazer logout"""
    session.clear()
    return redirect(url_for('login'))


# ============================================================
# INICIAR APLICAÇÃO
# ============================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("[APP] Aplicação iniciada com sucesso!")
    
    app.run(debug=False, host='0.0.0.0', port=5000)
