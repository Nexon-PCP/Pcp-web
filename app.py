from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import calendar

app = Flask(__name__)

ETAPAS_FIXAS = ["CORTE", "DOBRA", "PINTURA", "CALDEIRARIA", "MONTAGEM", "START UP"]

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///pcp.db"
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
        """Calcula percentual baseado em tarefas CONCLUIDO / total de tarefas"""
        # Buscar todas as tarefas da OP através de suas etapas
        todas_tarefas = []
        for etapa in self.etapas:
            todas_tarefas.extend(etapa.tarefas)
        
        # Se não há tarefas, retornar 0
        if not todas_tarefas:
            return 0.0
        
        # Contar tarefas com status CONCLUIDO
        tarefas_concluidas = sum(
            1 for tarefa in todas_tarefas 
            if tarefa.status == "CONCLUIDO"
        )
        
        # Calcular percentual: tarefas concluídas / total de tarefas * 100
        percentual = (tarefas_concluidas / len(todas_tarefas)) * 100
        return round(percentual, 2)

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


# ---------------- FUNÇÕES ----------------

def parse_date(s):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


def calcular_data_fim(data_inicio, horas_previstas, horas_por_dia=9):
    """
    Calcula a data de fim baseada na data de inicio e horas previstas.
    Considera apenas dias uteis (segunda a sexta) com 9 horas por dia.
    """
    if not data_inicio or not horas_previstas or horas_previstas <= 0:
        return data_inicio
    
    horas_restantes = float(horas_previstas)
    data_atual = data_inicio
    
    while horas_restantes > 0:
        if data_atual.weekday() < 5:  # Segunda a sexta (0-4)
            horas_restantes -= horas_por_dia
        
        if horas_restantes > 0:
            data_atual += timedelta(days=1)
    
    return data_atual


# ---------------- ROTAS ----------------

@app.route("/")
def home():
    return redirect(url_for("dashboard"))

@app.route("/api/obra/<int:obra_id>/produtos")
def api_produtos_obra(obra_id):
    obra = Obra.query.get_or_404(obra_id)

    # Formatar datas corretamente
    data_inicio_str = None
    prev_fim_str = None
    
    if obra.data_inicio:
        # Se for datetime, pegar apenas a data
        if hasattr(obra.data_inicio, 'date'):
            data_inicio_str = obra.data_inicio.date().strftime('%d/%m/%Y')
        else:
            data_inicio_str = obra.data_inicio.strftime('%d/%m/%Y')
    
    if obra.prev_fim:
        # Se for datetime, pegar apenas a data
        if hasattr(obra.prev_fim, 'date'):
            prev_fim_str = obra.prev_fim.date().strftime('%d/%m/%Y')
        else:
            prev_fim_str = obra.prev_fim.strftime('%d/%m/%Y')
    
    return {
        "produtos": [
            {
                "id": item.produto.id,
                "nome": item.produto.nome,
                "quantidade": item.quantidade
            }
            for item in obra.produtos
        ],
        "obra": {
            "data_inicio": data_inicio_str,
            "prev_fim": prev_fim_str
        }
    }
@app.route("/ops/<int:op_id>/imprimir")
def imprimir_op(op_id):
    from datetime import datetime
    op = OP.query.get_or_404(op_id)
    return render_template("op_impressao.html", op=op, now=datetime.now())


@app.route("/dashboard")
def dashboard():
    obras_total = Obra.query.count()
    ops_total = OP.query.count()

    ops = OP.query.all()
    abertas = sum(1 for o in ops if o.status == "ABERTA")
    em_prod = sum(1 for o in ops if o.status == "EM_EXECUCAO")
    atrasadas = sum(1 for o in ops if o.status == "ATRASADA")
    concluidas = sum(1 for o in ops if o.status == "CONCLUIDA")
    
    obras = Obra.query.all()
    obras_abertas = sum(1 for o in obras if o.status == "ATIVA")
    obras_em_exec = sum(1 for o in obras if o.status == "EM_EXECUCAO")
    obras_concluidas = sum(1 for o in obras if o.status == "CONCLUIDA")
    obras_atrasadas = sum(1 for o in obras if o.status == "ATRASADA")

    ap_total = Apontamento.query.count()
    ap_and = Apontamento.query.filter_by(status="EM_ANDAMENTO").count()
    ap_fin = Apontamento.query.filter_by(status="FINALIZADO").count()

    return render_template(
        "dashboard.html",
        obras_total=obras_total,
        ops_total=ops_total,
        abertas=abertas,
        em_prod=em_prod,
        atrasadas=atrasadas,
        concluidas=concluidas,
        obras_abertas=obras_abertas,
        obras_em_exec=obras_em_exec,
        obras_concluidas=obras_concluidas,
        obras_atrasadas=obras_atrasadas,
        ap_total=ap_total,
        ap_and=ap_and,
        ap_fin=ap_fin,
    )


# --------- CADASTROS ---------

@app.route("/cadastros")
def cadastros():
    operadores = Operador.query.order_by(Operador.nome.asc()).all()
    maquinas = Maquina.query.order_by(Maquina.nome.asc()).all()
    produtos = Produto.query.order_by(Produto.nome.asc()).all()
    return render_template("cadastros.html", operadores=operadores, maquinas=maquinas, produtos=produtos)

@app.route("/produtos")
def listar_produtos():
    produtos = Produto.query.order_by(Produto.nome.asc()).all()
    return render_template("produtos.html", produtos=produtos)

@app.route("/produtos/novo", methods=["POST"])
def produto_novo():
    nome = request.form["nome"].strip()
    if nome:
        db.session.add(Produto(nome=nome))
        db.session.commit()
    return redirect(url_for("listar_produtos"))

@app.route("/cadastros/produtos")
def cad_produtos():
    produtos = Produto.query.order_by(Produto.nome.asc()).all()
    return render_template("cadastros.html", produtos=produtos)

@app.route("/cadastros/produtos/novo", methods=["POST"])
def cad_produtos_novo():
    nome = request.form["nome"].strip()
    if nome:
        if not Produto.query.filter_by(nome=nome).first():
            db.session.add(Produto(nome=nome))
            db.session.commit()
    return redirect(url_for("cad_produtos"))



@app.route("/cadastros/operador", methods=["POST"])
def add_operador():
    nome = request.form["nome"].strip()
    matricula = request.form.get("matricula", "").strip() or None
    if nome:
        if not Operador.query.filter_by(nome=nome).first():
            db.session.add(Operador(nome=nome, matricula=matricula))
            db.session.commit()
    return redirect(url_for("cadastros"))


@app.route("/cadastros/maquina", methods=["POST"])
def add_maquina():
    nome = request.form["nome"].strip()
    setor = request.form.get("setor", "").strip() or None
    if nome:
        if not Maquina.query.filter_by(nome=nome).first():
            db.session.add(Maquina(nome=nome, setor=setor))
            db.session.commit()
    return redirect(url_for("cadastros"))


# --------- OBRAS ---------

@app.route("/obras")
def obras():
    query = Obra.query
    
    # Filtro por cliente
    cliente = request.args.get('cliente', '').strip()
    if cliente:
        query = query.filter(Obra.cliente.ilike(f'%{cliente}%'))
    
    # Filtro por data de início
    data_inicio_de = request.args.get('data_inicio_de', '').strip()
    if data_inicio_de:
        try:
            data_inicio_de = datetime.strptime(data_inicio_de, '%Y-%m-%d').date()
            query = query.filter(Obra.data_inicio >= data_inicio_de)
        except:
            pass
    
    data_inicio_ate = request.args.get('data_inicio_ate', '').strip()
    if data_inicio_ate:
        try:
            data_inicio_ate = datetime.strptime(data_inicio_ate, '%Y-%m-%d').date()
            query = query.filter(Obra.data_inicio <= data_inicio_ate)
        except:
            pass
    
    # Filtro por data de fim
    data_fim_de = request.args.get('data_fim_de', '').strip()
    if data_fim_de:
        try:
            data_fim_de = datetime.strptime(data_fim_de, '%Y-%m-%d').date()
            query = query.filter(Obra.prev_fim >= data_fim_de)
        except:
            pass
    
    data_fim_ate = request.args.get('data_fim_ate', '').strip()
    if data_fim_ate:
        try:
            data_fim_ate = datetime.strptime(data_fim_ate, '%Y-%m-%d').date()
            query = query.filter(Obra.prev_fim <= data_fim_ate)
        except:
            pass
    
    
    # Filtro por status
    status = request.args.get('status', '').strip()
    if status:
        query = query.filter(Obra.status == status)
    
    # Ordenação
    ordem = request.args.get('ordem', 'desc').strip().lower()
    coluna_ordem = request.args.get('coluna_ordem', 'corte_dobra_inicio').strip().lower()
    
    # Mapear coluna para atributo do modelo
    colunas_validas = {
        'corte_dobra_inicio': Obra.corte_dobra_inicio,
        'corte_dobra_fim': Obra.corte_dobra_fim,
        'montagem_eletro_inicio': Obra.montagem_eletro_inicio,
        'montagem_eletro_fim': Obra.montagem_eletro_fim,
    }
    
    coluna = colunas_validas.get(coluna_ordem, Obra.corte_dobra_inicio)
    
    if ordem == 'asc':
        obras = query.order_by(coluna.asc()).all()
    else:
        obras = query.order_by(coluna.desc()).all()
    
    return render_template("obras.html", obras=obras, ordem_atual=ordem, coluna_ordem=coluna_ordem)


@app.route("/obras/nova", methods=["GET"])
@requer_permissao("criar_obra")
def obra_nova():
    """Exibe o formulário para criar nova obra"""
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome.asc()).all()
    return render_template("obra_form.html", produtos=produtos)


@app.route("/obras", methods=["POST"])
@requer_permissao("criar_obra")
def obra_criar():
    """Processa o formulário de criação de obra"""
    codigo = request.form["codigo"].strip()
    nome = request.form.get("nome", "").strip() or None
    cliente = request.form.get("cliente", "").strip() or None
    status = request.form.get("status", "ATIVA").strip()
    corte_dobra_inicio = parse_date(request.form.get("corte_dobra_inicio"))
    corte_dobra_fim = parse_date(request.form.get("corte_dobra_fim"))
    montagem_eletro_inicio = parse_date(request.form.get("montagem_eletro_inicio"))
    montagem_eletro_fim = parse_date(request.form.get("montagem_eletro_fim"))

    obra = Obra(
        codigo=codigo,
        nome=nome,
        cliente=cliente,
        status=status,
        corte_dobra_inicio=corte_dobra_inicio,
        corte_dobra_fim=corte_dobra_fim,
        montagem_eletro_inicio=montagem_eletro_inicio,
        montagem_eletro_fim=montagem_eletro_fim,
    )

    db.session.add(obra)
    db.session.commit()

    # Processar produtos selecionados
    produtos_ids = request.form.getlist("produtos_ids")
    for produto_id in produtos_ids:
        qtd = int(request.form.get(f"qtd_{produto_id}", 1) or 1)
        db.session.add(ObraProduto(obra_id=obra.id, produto_id=int(produto_id), quantidade=qtd))
    
    db.session.commit()

    return redirect(url_for("obras"))


@app.route("/obras/<int:obra_id>")
def detalhe_obra(obra_id):
    obra = Obra.query.get_or_404(obra_id)
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome.asc()).all()
    return render_template("obra_detail.html", obra=obra, produtos=produtos)


@app.route("/obras/<int:obra_id>/produto/adicionar", methods=["POST"])
@requer_permissao("editar_obra")
def obra_produto_adicionar(obra_id):
    obra = Obra.query.get_or_404(obra_id)
    produto_id = int(request.form["produto_id"])
    quantidade = int(request.form.get("quantidade", 1) or 1)

    # Verificar se já existe
    existe = ObraProduto.query.filter_by(obra_id=obra_id, produto_id=produto_id).first()
    if existe:
        existe.quantidade = quantidade
    else:
        db.session.add(ObraProduto(obra_id=obra_id, produto_id=produto_id, quantidade=quantidade))

    db.session.commit()
    return redirect(url_for("detalhe_obra", obra_id=obra_id))


@app.route("/obras/<int:obra_id>/produto/<int:produto_id>/remover", methods=["POST"])
@requer_permissao("editar_obra")
def obra_produto_remover(obra_id, produto_id):
    op = ObraProduto.query.filter_by(obra_id=obra_id, produto_id=produto_id).first_or_404()
    db.session.delete(op)
    db.session.commit()
    return redirect(url_for("detalhe_obra", obra_id=obra_id))


@app.route("/obras/<int:obra_id>/atualizar-datas", methods=["POST"])
@requer_permissao("editar_obra")
def obra_atualizar_datas(obra_id):
    """Atualiza as datas de uma obra"""
    obra = Obra.query.get_or_404(obra_id)
    
    obra.corte_dobra_inicio = parse_date(request.form.get("corte_dobra_inicio"))
    obra.corte_dobra_fim = parse_date(request.form.get("corte_dobra_fim"))
    obra.montagem_eletro_inicio = parse_date(request.form.get("montagem_eletro_inicio"))
    obra.montagem_eletro_fim = parse_date(request.form.get("montagem_eletro_fim"))
    
    db.session.commit()
    return redirect(url_for("detalhe_obra", obra_id=obra_id))


@app.route("/obras/<int:obra_id>/excluir", methods=["POST"])
@requer_permissao("deletar_obra")
def obra_excluir(obra_id):
    """Exclui uma obra"""
    obra = Obra.query.get_or_404(obra_id)
    db.session.delete(obra)
    db.session.commit()
    return redirect(url_for("obras"))


# --------- OPS ---------

@app.route("/ops")
def ops():
    query = OP.query
    
    # Filtro por cliente
    cliente = request.args.get('cliente', '').strip()
    if cliente:
        query = query.join(Obra).filter(Obra.cliente.ilike(f'%{cliente}%'))
    
    # Filtro por data de início
    data_inicio_de = request.args.get('data_inicio_de', '').strip()
    if data_inicio_de:
        try:
            data_inicio_de = datetime.strptime(data_inicio_de, '%Y-%m-%d').date()
            query = query.filter(OP.prev_inicio >= data_inicio_de)
        except:
            pass
    
    data_inicio_ate = request.args.get('data_inicio_ate', '').strip()
    if data_inicio_ate:
        try:
            data_inicio_ate = datetime.strptime(data_inicio_ate, '%Y-%m-%d').date()
            query = query.filter(OP.prev_inicio <= data_inicio_ate)
        except:
            pass
    
    # Filtro por data de fim
    data_fim_de = request.args.get('data_fim_de', '').strip()
    if data_fim_de:
        try:
            data_fim_de = datetime.strptime(data_fim_de, '%Y-%m-%d').date()
            query = query.filter(OP.prev_fim >= data_fim_de)
        except:
            pass
    
    data_fim_ate = request.args.get('data_fim_ate', '').strip()
    if data_fim_ate:
        try:
            data_fim_ate = datetime.strptime(data_fim_ate, '%Y-%m-%d').date()
            query = query.filter(OP.prev_fim <= data_fim_ate)
        except:
            pass
    
    # Filtro por status
    status = request.args.get('status', '').strip()
    if status:
        query = query.filter(OP.status == status)
    
    # Ordenação
    ordem = request.args.get('ordem', 'desc').strip().lower()
    coluna_ordem = request.args.get('coluna_ordem', 'id').strip().lower()
    
    # Mapear coluna para atributo do modelo
    colunas_validas = {
        'numero': OP.numero,
        'produto': OP.produto,
        'quantidade': OP.quantidade,
        'percentual': OP.percentual,
        'status': OP.status,
        'prev_inicio': OP.prev_inicio,
        'prev_fim': OP.prev_fim,
        'corte_dobra_inicio': Obra.corte_dobra_inicio,
        'corte_dobra_fim': Obra.corte_dobra_fim,
        'montagem_eletro_inicio': Obra.montagem_eletro_inicio,
        'montagem_eletro_fim': Obra.montagem_eletro_fim,
    }
    
    coluna = colunas_validas.get(coluna_ordem, OP.id)
    
    # Se ordenar por colunas de Obra, fazer join
    if coluna_ordem in ['corte_dobra_inicio', 'corte_dobra_fim', 'montagem_eletro_inicio', 'montagem_eletro_fim']:
        query = query.join(Obra, OP.obra_id == Obra.id)
    
    if ordem == 'asc':
        ops = query.order_by(coluna.asc()).all()
    else:
        ops = query.order_by(coluna.desc()).all()
    
    return render_template("ops.html", ops=ops, ordem_atual=ordem, coluna_ordem=coluna_ordem)


@app.route("/ops/nova")
@requer_permissao("criar_op")
def op_nova():
    obras = Obra.query.order_by(Obra.codigo.asc()).all()
    return render_template("op_form.html", obras=obras)


@app.route("/api/obra/<int:obra_id>")
def api_obra(obra_id):
    """API para puxar dados da obra e seus produtos"""
    obra = Obra.query.get(obra_id)
    if not obra:
        return {"erro": "Obra não encontrada"}, 404
    
    # Buscar produtos com OP CRIADA nesta obra (qualquer status)
    ops_criadas = OP.query.filter(
        OP.obra_id == obra_id
    ).all()
    
    produtos_com_op = set([op.produto for op in ops_criadas])
    
    produtos = []
    if obra.produtos:
        for item in obra.produtos:
            # Filtrar produtos que JA TEM OP CRIADA
            if item.produto.nome not in produtos_com_op:
                produtos.append({
                    "id": item.produto.id,
                    "nome": item.produto.nome,
                    "quantidade": item.quantidade
                })
    
    return {
        "corte_dobra_inicio": obra.corte_dobra_inicio.strftime('%Y-%m-%d') if obra.corte_dobra_inicio else None,
        "corte_dobra_fim": obra.corte_dobra_fim.strftime('%Y-%m-%d') if obra.corte_dobra_fim else None,
        "montagem_eletro_inicio": obra.montagem_eletro_inicio.strftime('%Y-%m-%d') if obra.montagem_eletro_inicio else None,
        "montagem_eletro_fim": obra.montagem_eletro_fim.strftime('%Y-%m-%d') if obra.montagem_eletro_fim else None,
        "produtos": produtos,
        "produtos_com_op": list(produtos_com_op)
    }


@app.route("/ops", methods=["POST"])
@requer_permissao("criar_op")
def op_criar():
    obra_id = int(request.form["obra_id"])
    
    # Gerar numero automatico de OP
    ultima_op = OP.query.order_by(OP.id.desc()).first()
    proximo_numero = 1 if not ultima_op else int(ultima_op.numero) + 1
    numero = f"{proximo_numero:02d}"
    produto = request.form["produto"].strip()
    quantidade = int(request.form.get("quantidade", 1) or 1)
    prev_inicio = parse_date(request.form.get("prev_inicio"))
    prev_fim = parse_date(request.form.get("prev_fim"))

    op = OP(
        numero=numero,
        obra_id=obra_id,
        produto=produto,
        quantidade=quantidade,
        prev_inicio=prev_inicio,
        prev_fim=prev_fim,
    )

    db.session.add(op)
    db.session.commit()

    # Criar etapas padrão
    for etapa_nome in ETAPAS_FIXAS:
        etapa = Etapa(op_id=op.id, nome=etapa_nome, status="PLANEJADO")
        db.session.add(etapa)

    db.session.commit()

    return redirect(url_for("ops"))


@app.route("/ops/<int:op_id>")
def detalhe_op(op_id):
    op = OP.query.get_or_404(op_id)
    operadores = Operador.query.filter_by(ativo=True).order_by(Operador.nome.asc()).all()
    return render_template("op_detail.html", op=op, operadores=operadores)


@app.route("/ops/<int:op_id>/excluir", methods=["POST"])
@requer_permissao("deletar_op")
def excluir_op(op_id):
    op = OP.query.get_or_404(op_id)
    db.session.delete(op)
    db.session.commit()
    return redirect(url_for("ops"))



@app.route("/op/<int:op_id>/salvar-modelo", methods=["POST"])
def salvar_modelo_op(op_id):
    """Salva a estrutura de etapas e tarefas como modelo reutilizável"""
    op = OP.query.get_or_404(op_id)
    produto = op.produto
    
    # Coletar dados das etapas e tarefas (sem datas)
    dados_etapas = []
    for etapa in op.etapas:
        etapa_data = {
            'nome': etapa.nome,
            'tarefas': []
        }
        for tarefa in etapa.tarefas:
            tarefa_data = {
                'titulo': tarefa.titulo,
                'descricao': tarefa.descricao,
                'horas_previstas': tarefa.horas_previstas,
                'responsavel_id': tarefa.responsavel_id,
                'data_inicio_prev': tarefa.data_inicio_prev.isoformat() if tarefa.data_inicio_prev else None,
                'data_fim_prev': tarefa.data_fim_prev.isoformat() if tarefa.data_fim_prev else None
            }
            etapa_data['tarefas'].append(tarefa_data)
        dados_etapas.append(etapa_data)
    
    # Criar modelo
    modelo = ModeloOP(
        produto=produto,
        nome=f"Modelo - {op.numero}",
        descricao=f"Modelo baseado na OP {op.numero}",
        dados={'etapas': dados_etapas}
    )
    
    db.session.add(modelo)
    db.session.commit()
    
    return redirect(url_for("detalhe_op", op_id=op_id))


@app.route("/op/<int:op_id>/carregar-modelo", methods=["GET", "POST"])
@requer_permissao("editar_op")
def carregar_modelo_op(op_id):
    """Carrega um modelo e preenche as etapas e tarefas da OP"""
    op = OP.query.get_or_404(op_id)
    
    if request.method == "GET":
        modelos = ModeloOP.query.filter_by(produto=op.produto).all()
        return render_template("carregar_modelo.html", op=op, modelos=modelos)
    
    modelo_id = int(request.form.get("modelo_id"))
    modelo = ModeloOP.query.get_or_404(modelo_id)
    
    for etapa in op.etapas:
        db.session.delete(etapa)
    db.session.commit()
    
    etapas_criadas = {}
    
    for etapa_data in modelo.dados.get('etapas', []):
        etapa = Etapa(
            op_id=op.id,
            nome=etapa_data['nome'],
            percentual=0.0,
            status="PLANEJADO"
        )
        db.session.add(etapa)
        db.session.flush()
        etapas_criadas[etapa_data['nome']] = etapa
        
        for tarefa_data in etapa_data.get('tarefas', []):
            data_inicio = None
            data_fim = None
            if tarefa_data.get('data_inicio_prev'):
                try:
                    data_inicio = datetime.strptime(tarefa_data['data_inicio_prev'], '%Y-%m-%d').date()
                except:
                    pass
            if tarefa_data.get('data_fim_prev'):
                try:
                    data_fim = datetime.strptime(tarefa_data['data_fim_prev'], '%Y-%m-%d').date()
                except:
                    pass
            
            tarefa = Tarefa(
                etapa_id=etapa.id,
                numero=None,
                titulo=tarefa_data['titulo'],
                descricao=tarefa_data.get('descricao', ''),
                horas_previstas=tarefa_data.get('horas_previstas', 0.0),
                responsavel_id=tarefa_data.get('responsavel_id'),
                data_inicio_prev=data_inicio,
                data_fim_prev=data_fim,
                status="PLANEJADO"
            )
            db.session.add(tarefa)
    
    db.session.flush()
    
    # Calcular datas de inicio automaticamente usando data da OP
    from datetime import timedelta
    data_op = op.prev_inicio if op.prev_inicio else date.today()
    
    for etapa in op.etapas:
        if not etapa.tarefas:
            continue
        
        data_inicio_etapa = None
        
        if etapa.nome in ["CORTE", "DOBRA", "PINTURA", "CALDEIRARIA"]:
            # Data de inicio = Data da OP
            data_inicio_etapa = data_op
        
        elif etapa.nome == "MONTAGEM":
            # Data de inicio = Data da OP
            data_inicio_etapa = data_op
        
        elif etapa.nome == "START UP":
            # Data de inicio = Data da OP + 1 dia
            data_inicio_etapa = data_op + timedelta(days=1)
        
        if data_inicio_etapa:
            for tarefa in etapa.tarefas:
                tarefa.data_inicio_prev = data_inicio_etapa
                if tarefa.horas_previstas > 0:
                    tarefa.data_fim_prev = calcular_data_fim(data_inicio_etapa, tarefa.horas_previstas, 9)
    
    db.session.flush()
    
    op_num = str(int(op.numero)) if op.numero else '1'
    tarefa_idx = 1
    for etapa in op.etapas:
        for tarefa in etapa.tarefas:
            tarefa.numero = f"{op_num}.{tarefa_idx}"
            tarefa_idx += 1
    
    db.session.commit()
    return redirect(url_for("detalhe_op", op_id=op_id))

@app.route("/ops/<int:op_id>/sincronizar-etapas", methods=["POST"])
@requer_permissao("editar_op")
def sincronizar_etapas(op_id):
    """Sincroniza as etapas de uma OP com a lista de ETAPAS_FIXAS e sincroniza datas"""
    op = OP.query.get_or_404(op_id)
    
    # Buscar etapas existentes
    etapas_existentes = [e.nome for e in op.etapas]
    
    # Adicionar etapas faltantes
    for etapa_nome in ETAPAS_FIXAS:
        if etapa_nome not in etapas_existentes:
            etapa = Etapa(op_id=op.id, nome=etapa_nome, status="PLANEJADO")
            db.session.add(etapa)
    
    db.session.commit()
    
    # Sincronizar datas das tarefas
    from datetime import timedelta
    
    for etapa in op.etapas:
        if not etapa.tarefas:
            continue
        
        data_inicio_etapa = None
        
        if etapa.nome in ["CORTE", "DOBRA", "PINTURA", "CALDEIRARIA"]:
            # Data de inicio = Data Inicio de CORTE ou DOBRA
            for etapa_ref in op.etapas:
                if etapa_ref.nome in ["CORTE", "DOBRA"]:
                    tarefa_ref = etapa_ref.tarefas[0] if etapa_ref.tarefas else None
                    if tarefa_ref and tarefa_ref.data_inicio_prev:
                        data_inicio_etapa = tarefa_ref.data_inicio_prev
                        break
        
        elif etapa.nome == "MONTAGEM":
            # Data de inicio = Data Montagem Inicio da Obra
            if op.obra and op.obra.montagem_eletro_inicio:
                data_inicio_etapa = op.obra.montagem_eletro_inicio
        
        elif etapa.nome == "START UP":
            # Data de inicio = Data Fim de MONTAGEM + 1 dia
            for etapa_ref in op.etapas:
                if etapa_ref.nome == "MONTAGEM":
                    tarefa_ref = etapa_ref.tarefas[0] if etapa_ref.tarefas else None
                    if tarefa_ref and tarefa_ref.data_fim_prev:
                        data_inicio_etapa = tarefa_ref.data_fim_prev + timedelta(days=1)
                        break
        
        # Aplicar a data de inicio calculada para todas as tarefas da etapa
        if data_inicio_etapa:
            for tarefa in etapa.tarefas:
                tarefa.data_inicio_prev = data_inicio_etapa
                # Recalcular data fim se houver horas previstas
                if tarefa.horas_previstas > 0:
                    tarefa.data_fim_prev = calcular_data_fim(data_inicio_etapa, tarefa.horas_previstas, 9)
    
    db.session.commit()
    return redirect(url_for("detalhe_op", op_id=op_id))


@app.route("/etapas/<int:etapa_id>/atualizar", methods=["POST"])
def etapa_atualizar(etapa_id):
    etapa = Etapa.query.get_or_404(etapa_id)

    percentual = float(request.form.get("percentual", 0) or 0)
    horas_planejadas = float(request.form.get("horas_planejadas", 0) or 0)
    responsavel_id = request.form.get("responsavel_id")

    etapa.percentual = percentual
    etapa.horas_planejadas = horas_planejadas
    etapa.responsavel_id = int(responsavel_id) if responsavel_id else None

    acao = request.form.get("acao")
    if acao == "iniciar":
        etapa.data_inicio = datetime.now()
        etapa.status = "EXECUCAO"
    elif acao == "concluir":
        etapa.data_fim = datetime.now()
        etapa.status = "CONCLUIDO"

    db.session.commit()
    return redirect(url_for("detalhe_op", op_id=etapa.op_id))


# --------- TAREFAS ---------

@app.route("/tarefas/nova", methods=["POST"])
@requer_permissao("criar_tarefa")
def tarefa_nova():
    etapa_id = int(request.form["etapa_id"])
    etapa = Etapa.query.get_or_404(etapa_id)
    
    # Verificar se usuario ESPECIALISTA tem permissao para esta etapa
    if session.get('usuario_tipo') == 'ESPECIALISTA':
        usuario = Usuario.query.get(session.get('usuario_id'))
        if usuario and not usuario.tem_permissao("criar_tarefa", etapa.nome):
            return render_template('erro_permissao.html', mensagem=f"Você não tem permissão para criar tarefas na etapa {etapa.nome}"), 403
    
    titulo = request.form.get("titulo", "").strip()
    responsavel_id = request.form.get("responsavel_id")
    horas_previstas = float(request.form.get("horas_previstas", 0) or 0)
    data_inicio_str = request.form.get("data_inicio_prev", "")
    
    data_inicio = None
    data_fim = None
    
    # Se nao foi informada data de inicio, carregar automaticamente
    if not data_inicio_str:
        op = etapa.op
        
        if etapa.nome in ["CORTE", "DOBRA", "PINTURA", "CALDEIRARIA"]:
            # Carregar data de inicio de CORTE E DOBRA
            etapa_corte_dobra = Etapa.query.filter(
                Etapa.op_id == op.id,
                Etapa.nome.in_(["CORTE", "DOBRA"])
            ).first()
            if etapa_corte_dobra:
                tarefa_corte_dobra = Tarefa.query.filter(
                    Tarefa.etapa_id == etapa_corte_dobra.id
                ).first()
                if tarefa_corte_dobra and tarefa_corte_dobra.data_inicio_prev:
                    data_inicio = tarefa_corte_dobra.data_inicio_prev
        
        elif etapa.nome == "MONTAGEM":
            # Carregar data de inicio de MONTAGEM
            etapa_montagem = Etapa.query.filter(
                Etapa.op_id == op.id,
                Etapa.nome == "MONTAGEM"
            ).first()
            if etapa_montagem:
                tarefa_montagem = Tarefa.query.filter(
                    Tarefa.etapa_id == etapa_montagem.id
                ).first()
                if tarefa_montagem and tarefa_montagem.data_inicio_prev:
                    data_inicio = tarefa_montagem.data_inicio_prev
        
        elif etapa.nome == "START UP":
            # Carregar um dia depois de MONTAGEM FIM
            etapa_montagem = Etapa.query.filter(
                Etapa.op_id == op.id,
                Etapa.nome == "MONTAGEM"
            ).first()
            if etapa_montagem:
                tarefa_montagem = Tarefa.query.filter(
                    Tarefa.etapa_id == etapa_montagem.id
                ).first()
                if tarefa_montagem and tarefa_montagem.data_fim_prev:
                    from datetime import timedelta
                    data_inicio = tarefa_montagem.data_fim_prev + timedelta(days=1)
    
    # Se foi informada data de inicio, usar ela
    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
        except Exception as e:
            print(f"Erro ao parsear data: {e}")
            pass
    
    # Calcular data fim se houver data inicio
    if data_inicio and horas_previstas > 0:
        data_fim = calcular_data_fim(data_inicio, horas_previstas, 9)
    
    if titulo:
        # Gerar numero automatico de Tarefa (ex: 1.1, 1.2, 1.3...)
        op = etapa.op
        todas_tarefas_op = Tarefa.query.join(Etapa).filter(Etapa.op_id == op.id).all()
        proximo_subtarefa = len(todas_tarefas_op) + 1
        numero_tarefa = f"{op.numero}.{proximo_subtarefa}"
        
        tarefa = Tarefa(
            etapa_id=etapa_id,
            numero=numero_tarefa,
            titulo=titulo,
            responsavel_id=int(responsavel_id) if responsavel_id else None,
            horas_previstas=horas_previstas,
            data_inicio_prev=data_inicio,
            data_fim_prev=data_fim,
            status="PLANEJADO"
        )
        db.session.add(tarefa)
        db.session.commit()
    
    return redirect(url_for("detalhe_op", op_id=etapa.op_id))



@app.route("/tarefas/<int:tarefa_id>/atualizar-data", methods=["POST"])
def atualizar_data_tarefa(tarefa_id):
    """Atualiza a data de início e calcula automaticamente a data de fim"""
    tarefa = Tarefa.query.get_or_404(tarefa_id)
    
    # Verificar se usuario ESPECIALISTA tem permissao para esta etapa
    if session.get('usuario_tipo') == 'ESPECIALISTA':
        usuario = Usuario.query.get(session.get('usuario_id'))
        if usuario and not usuario.tem_permissao("editar_tarefa", tarefa.etapa.nome):
            return render_template('erro_permissao.html', mensagem=f"Você não tem permissão para alterar datas de tarefas na etapa {tarefa.etapa.nome}"), 403
    
    data_inicio_str = request.form.get("data_inicio_prev", "")
    
    if data_inicio_str:
        try:
            # Converter de YYYY-MM-DD para date
            data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
            tarefa.data_inicio_prev = data_inicio
            
            # Calcular data de fim automaticamente
            if tarefa.horas_previstas > 0:
                tarefa.data_fim_prev = calcular_data_fim(data_inicio, tarefa.horas_previstas, 9)
            
            db.session.commit()
        except Exception as e:
            print(f"Erro ao atualizar data: {e}")
    
    return redirect(url_for("detalhe_op", op_id=tarefa.etapa.op_id))

@app.route("/tarefas/<int:tarefa_id>/atualizar", methods=["POST"])
@requer_permissao("editar_tarefa")
def tarefa_atualizar(tarefa_id):
    tarefa = Tarefa.query.get_or_404(tarefa_id)
    
    # Verificar se usuario ESPECIALISTA tem permissao para esta etapa
    if session.get('usuario_tipo') == 'ESPECIALISTA':
        usuario = Usuario.query.get(session.get('usuario_id'))
        if usuario and not usuario.tem_permissao("editar_tarefa", tarefa.etapa.nome):
            return render_template('erro_permissao.html', mensagem=f"Você não tem permissão para atualizar tarefas na etapa {tarefa.etapa.nome}"), 403
    
    tarefa.horas_realizadas = float(request.form.get("horas_realizadas", 0) or 0)
    acao = request.form.get("acao")
    
    if acao == "iniciar":
        tarefa.data_inicio_real = datetime.now()
        tarefa.status = "EM_EXECUCAO"
        
        # Atualizar status da etapa para EM_EXECUCAO
        etapa = tarefa.etapa
        if etapa.status != "EM_EXECUCAO":
            etapa.status = "EM_EXECUCAO"
        
        # Atualizar status da OP para EM_EXECUCAO
        op = etapa.op
        if op.status != "EM_EXECUCAO":
            op.status = "EM_EXECUCAO"
            
            # Atualizar status da Obra para EM_EXECUCAO quando primeira OP inicia
            obra = op.obra
            if obra.status != "EM_EXECUCAO":
                obra.status = "EM_EXECUCAO"
            
    elif acao == "concluir":
        tarefa.data_fim_real = datetime.now()
        tarefa.status = "CONCLUIDO"
        db.session.flush()
        
        op = tarefa.etapa.op
        total_tarefas = Tarefa.query.join(Etapa).filter(Etapa.op_id == op.id).count()
        tarefas_concluidas = Tarefa.query.join(Etapa).filter(
            Etapa.op_id == op.id,
            Tarefa.status == "CONCLUIDO"
        ).count()
        
        if total_tarefas > 0:
            op.percentual = (tarefas_concluidas / total_tarefas) * 100
        
        if tarefas_concluidas == total_tarefas and total_tarefas > 0:
            op.status = "CONCLUIDA"
    
    db.session.commit()
    return redirect(url_for("detalhe_op", op_id=tarefa.etapa.op_id))


@app.route("/tarefas/<int:tarefa_id>/pausar", methods=["POST"])
@requer_permissao("editar_tarefa")
def tarefa_pausar(tarefa_id):
    tarefa = Tarefa.query.get_or_404(tarefa_id)
    
    # Verificar se usuario ESPECIALISTA tem permissao para esta etapa
    if session.get('usuario_tipo') == 'ESPECIALISTA':
        usuario = Usuario.query.get(session.get('usuario_id'))
        if usuario and not usuario.tem_permissao("editar_tarefa", tarefa.etapa.nome):
            return render_template('erro_permissao.html', mensagem=f"Você não tem permissão para pausar tarefas na etapa {tarefa.etapa.nome}"), 403
    
    justificativa = request.form.get("justificativa", "")
    tarefa.status = "PAUSADO"
    tarefa.justificativa_pausa = justificativa
    
    db.session.commit()
    return redirect(url_for("detalhe_op", op_id=tarefa.etapa.op_id))


@app.route("/tarefas/<int:tarefa_id>/concluir", methods=["POST"])
@requer_permissao("editar_tarefa")
def tarefa_concluir(tarefa_id):
    tarefa = Tarefa.query.get_or_404(tarefa_id)
    
    # Verificar se usuario ESPECIALISTA tem permissao para esta etapa
    if session.get('usuario_tipo') == 'ESPECIALISTA':
        usuario = Usuario.query.get(session.get('usuario_id'))
        if usuario and not usuario.tem_permissao("editar_tarefa", tarefa.etapa.nome):
            return render_template('erro_permissao.html', mensagem=f"Você não tem permissão para concluir tarefas na etapa {tarefa.etapa.nome}"), 403
    
    tarefa.data_fim_real = datetime.now()
    tarefa.status = "CONCLUIDO"
    
    db.session.commit()
    
    # Atualizar status da OP se todas as tarefas estão concluídas
    op = tarefa.etapa.op
    todas_tarefas = Tarefa.query.join(Etapa).filter(Etapa.op_id == op.id).all()
    todas_concluidas = all(t.status == "CONCLUIDO" for t in todas_tarefas)
    
    if todas_concluidas:
        op.status = "CONCLUIDA"
        op.percentual = 100.0
        db.session.commit()
        
        # Atualizar status da Obra se todas as OPs estão concluídas
        obra = op.obra
        todas_ops = OP.query.filter_by(obra_id=obra.id).all()
        todas_ops_concluidas = all(o.status == "CONCLUIDA" for o in todas_ops)
        
        if todas_ops_concluidas:
            obra.status = "CONCLUIDA"
            db.session.commit()
    
    return redirect(url_for("detalhe_op", op_id=tarefa.etapa.op_id))


@app.route("/tarefas/<int:tarefa_id>/excluir", methods=["POST"])
@requer_permissao("deletar_tarefa")
def tarefa_excluir(tarefa_id):
    tarefa = Tarefa.query.get_or_404(tarefa_id)
    
    # Verificar se usuario ESPECIALISTA tem permissao para esta etapa
    if session.get('usuario_tipo') == 'ESPECIALISTA':
        usuario = Usuario.query.get(session.get('usuario_id'))
        if usuario and not usuario.tem_permissao("deletar_tarefa", tarefa.etapa.nome):
            return render_template('erro_permissao.html', mensagem=f"Você não tem permissão para deletar tarefas na etapa {tarefa.etapa.nome}"), 403
    op_id = tarefa.etapa.op_id
    db.session.delete(tarefa)
    db.session.commit()
    return redirect(url_for("detalhe_op", op_id=op_id))


# --------- APONTAMENTOS ---------

@app.route("/apontamentos")
def apontamentos():
    obras = Obra.query.order_by(Obra.codigo.asc()).all()
    ops = OP.query.order_by(OP.id.desc()).all()
    operadores = Operador.query.filter_by(ativo=True).order_by(Operador.nome.asc()).all()
    maquinas = Maquina.query.filter_by(ativo=True).order_by(Maquina.nome.asc()).all()
    aponts = Apontamento.query.order_by(Apontamento.id.desc()).limit(50).all()

    return render_template(
        "apontamentos.html",
        obras=obras,
        ops=ops,
        operadores=operadores,
        maquinas=maquinas,
        aponts=aponts,
    )


@app.route("/apontamentos/novo", methods=["POST"])
def apontamento_novo():
    obra_id = int(request.form["obra_id"])
    op_id = int(request.form["op_id"])
    etapa_id = int(request.form["etapa_id"])
    operador_id = int(request.form["operador_id"])

    maquina_id = request.form.get("maquina_id")
    maquina_id = int(maquina_id) if maquina_id else None

    qtd_boa = int(request.form.get("qtd_boa", 0) or 0)
    qtd_refugo = int(request.form.get("qtd_refugo", 0) or 0)
    obs = request.form.get("obs", "").strip() or None

    ap = Apontamento(
        obra_id=obra_id,
        op_id=op_id,
        etapa_id=etapa_id,
        operador_id=operador_id,
        maquina_id=maquina_id,
        inicio=datetime.now(),
        qtd_boa=qtd_boa,
        qtd_refugo=qtd_refugo,
        obs=obs,
        status="EM_ANDAMENTO",
    )

    db.session.add(ap)
    db.session.commit()
    return redirect(url_for("apontamentos"))


@app.route("/apontamentos/<int:ap_id>/finalizar", methods=["POST"])
def apontamento_finalizar(ap_id):
    ap = Apontamento.query.get_or_404(ap_id)
    ap.fim = datetime.now()
    ap.status = "FINALIZADO"
    db.session.commit()
    return redirect(url_for("apontamentos"))


# --------- CRONOGRAMA ---------

@app.route("/cronograma")
def cronograma():
    obras = Obra.query.order_by(Obra.codigo.asc()).all()
    obra_id = request.args.get("obra_id", type=int)

    itens = []
    obra_sel = None
    if obra_id:
        obra_sel = Obra.query.get(obra_id)
        if obra_sel:
            itens = CronogramaItem.query.filter_by(obra_id=obra_id).order_by(CronogramaItem.id.desc()).all()

    return render_template("cronograma.html", obras=obras, obra_sel=obra_sel, itens=itens)


@app.route("/cronograma/novo", methods=["POST"])
def cronograma_novo():
    obra_id = int(request.form["obra_id"])
    titulo = request.form["titulo"].strip()
    responsavel = request.form.get("responsavel", "").strip() or None
    inicio_prev = parse_date(request.form.get("inicio_prev"))
    fim_prev = parse_date(request.form.get("fim_prev"))

    item = CronogramaItem(
        obra_id=obra_id,
        titulo=titulo,
        responsavel=responsavel,
        inicio_prev=inicio_prev,
        fim_prev=fim_prev,
        status="PLANEJADO",
    )
    db.session.add(item)
    db.session.commit()

    return redirect(url_for("cronograma", obra_id=obra_id))


# --------- RELATÓRIOS ---------

@app.route("/relatorios")
def relatorios():
    total_ops = OP.query.count()
    total_obras = Obra.query.count()
    ops_atrasadas = [op for op in OP.query.all() if op.status == "ATRASADA"]
    apont_finalizados = Apontamento.query.filter_by(status="FINALIZADO").count()

    return render_template(
        "relatorios.html",
        total_ops=total_ops,
        total_obras=total_obras,
        ops_atrasadas=ops_atrasadas,
        apont_finalizados=apont_finalizados,
    )


@app.route("/relatorios/tempo")
def rel_tempo():
    """Relatório de gestão de tempo por etapa"""
    etapas = Etapa.query.all()
    
    relatorio = []
    for etapa in etapas:
        relatorio.append({
            "etapa": etapa,
            "horas_planejadas": etapa.horas_planejadas,
            "horas_realizadas": etapa.horas_realizadas,
            "diferenca": etapa.horas_planejadas - etapa.horas_realizadas,
            "percentual_utilizacao": (etapa.horas_realizadas / etapa.horas_planejadas * 100) if etapa.horas_planejadas > 0 else 0
        })
    
    return render_template("rel_tempo.html", relatorio=relatorio)


@app.route("/relatorios/operador")
def rel_operador():
    """Relatório de horas por operador e etapa"""
    operadores = Operador.query.filter_by(ativo=True).order_by(Operador.nome.asc()).all()
    
    relatorio = []
    for operador in operadores:
        aponts = Apontamento.query.filter_by(operador_id=operador.id).filter_by(status="FINALIZADO").all()
        
        for apont in aponts:
            relatorio.append({
                "operador": operador.nome,
                "etapa": apont.etapa.nome,
                "op": apont.op.numero,
                "horas_gastas": apont.horas_gastas,
                "data": apont.fim.strftime("%d/%m/%Y") if apont.fim else "-"
            })
    
    return render_template("rel_operador.html", relatorio=relatorio)


@app.route("/relatorios/tarefas")
def rel_tarefas():
    """Relatório de tarefas com horas planejadas vs realizadas"""
    tarefas = Tarefa.query.all()

    total_prev = sum(t.horas_previstas for t in tarefas)
    total_real = sum(t.horas_realizadas for t in tarefas)

    return render_template(
        "rel_tarefas.html",
        tarefas=tarefas,
        total_prev=total_prev,
        total_real=total_real
    )


@app.route("/relatorios/semanal")
def rel_semanal():
    """Relatório semanal de alocação de horas por responsável"""
    
    # Parâmetros de filtro
    responsavel_id = request.args.get("responsavel_id", type=int)
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    
    # Se não especificar datas, usar últimas 8 semanas
    if not data_fim:
        data_fim = date.today()
    else:
        data_fim = parse_date(data_fim)
    
    if not data_inicio:
        data_inicio = data_fim - timedelta(days=56)  # 8 semanas
    else:
        data_inicio = parse_date(data_inicio)
    
    # Buscar operadores
    operadores = Operador.query.filter_by(ativo=True).order_by(Operador.nome.asc()).all()
    
    # Se filtrar por responsável específico
    if responsavel_id:
        operadores = [op for op in operadores if op.id == responsavel_id]
    
    # Gerar lista de semanas
    semanas = []
    data_atual = data_inicio
    while data_atual <= data_fim:
        # Encontrar início da semana (segunda-feira)
        inicio_semana = data_atual - timedelta(days=data_atual.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        
        # Evitar duplicatas
        if not semanas or semanas[-1][0] != inicio_semana:
            semanas.append((inicio_semana, fim_semana))
        
        data_atual += timedelta(days=7)
    
    # Construir relatório
    relatorio = []
    
    for operador in operadores:
        dados_semanas = []
        total_planejado = 0
        total_realizado = 0
        
        for inicio_semana, fim_semana in semanas:
            # Etapas alocadas nesta semana
            etapas = Etapa.query.filter_by(responsavel_id=operador.id).all()
            
            # Filtrar por data de criação/modificação (aproximado)
            horas_plan_semana = 0
            horas_real_semana = 0
            
            for etapa in etapas:
                # Se a etapa foi criada nesta semana ou está ativa
                if etapa.op.data_emissao:
                    data_etapa = etapa.op.data_emissao
                    if inicio_semana.date() <= data_etapa <= fim_semana.date():
                        horas_plan_semana += etapa.horas_planejadas
                        horas_real_semana += etapa.horas_realizadas
            
            # Apontamentos nesta semana
            apontos = Apontamento.query.filter_by(
                operador_id=operador.id,
                status="FINALIZADO"
            ).all()
            
            for apont in apontos:
                if apont.fim and inicio_semana <= apont.fim.date() <= fim_semana:
                    horas_real_semana += apont.horas_gastas
            
            dados_semanas.append({
                "semana_inicio": inicio_semana,
                "semana_fim": fim_semana,
                "horas_planejadas": horas_plan_semana,
                "horas_realizadas": horas_real_semana,
                "diferenca": horas_plan_semana - horas_real_semana,
                "percentual": (horas_real_semana / horas_plan_semana * 100) if horas_plan_semana > 0 else 0
            })
            
            total_planejado += horas_plan_semana
            total_realizado += horas_real_semana
        
        # Só adicionar se tiver dados
        if any(d["horas_planejadas"] > 0 or d["horas_realizadas"] > 0 for d in dados_semanas):
            relatorio.append({
                "operador": operador,
                "dados_semanas": dados_semanas,
                "total_planejado": total_planejado,
                "total_realizado": total_realizado,
                "total_diferenca": total_planejado - total_realizado,
                "total_percentual": (total_realizado / total_planejado * 100) if total_planejado > 0 else 0
            })
    
    return render_template(
        "rel_semanal.html",
        relatorio=relatorio,
        semanas=semanas,
        operadores=operadores,
        responsavel_id=responsavel_id,
        data_inicio=data_inicio.strftime("%Y-%m-%d"),
        data_fim=data_fim.strftime("%Y-%m-%d"),
        todos_operadores=Operador.query.filter_by(ativo=True).order_by(Operador.nome.asc()).all()
    )


@app.route("/relatorios/tarefas-por-produto")
def rel_tarefas_por_produto():
    """Relatório de tarefas agrupadas por produto com total de horas previstas"""
    
    # Buscar todas as obras
    obras = Obra.query.order_by(Obra.codigo.asc()).all()
    
    relatorio = []
    
    for obra in obras:
        # Buscar produtos desta obra
        produtos_obra = ObraProduto.query.filter_by(obra_id=obra.id).all()
        
        dados_produtos = []
        total_horas_obra = 0
        
        for op_prod in produtos_obra:
            produto = op_prod.produto
            
            # Buscar OPs que usam este produto
            ops_produto = OP.query.filter_by(obra_id=obra.id, produto=produto.nome).all()
            
            horas_previstas_produto = 0
            tarefas_produto = []
            
            for op in ops_produto:
                # Buscar etapas desta OP
                etapas = Etapa.query.filter_by(op_id=op.id).all()
                
                for etapa in etapas:
                    # Buscar tarefas desta etapa
                    tarefas = Tarefa.query.filter_by(etapa_id=etapa.id).all()
                    
                    for tarefa in tarefas:
                        horas_previstas_produto += tarefa.horas_previstas
                        tarefas_produto.append({
                            'titulo': tarefa.titulo,
                            'etapa': etapa.nome,
                            'op_numero': op.numero,
                            'horas_previstas': tarefa.horas_previstas,
                            'responsavel': tarefa.responsavel.nome if tarefa.responsavel else '-',
                            'status': tarefa.status
                        })
            
            if tarefas_produto:
                dados_produtos.append({
                    'produto': produto.nome,
                    'quantidade': op_prod.quantidade,
                    'horas_previstas': horas_previstas_produto,
                    'tarefas': tarefas_produto
                })
                total_horas_obra += horas_previstas_produto
        
        if dados_produtos:
            relatorio.append({
                'obra': obra,
                'produtos': dados_produtos,
                'total_horas': total_horas_obra
            })
    
    # Total geral
    total_geral = sum(r['total_horas'] for r in relatorio)
    
    return render_template(
        "rel_tarefas_por_produto.html",
        relatorio=relatorio,
        total_geral=total_geral
    )


@app.route("/relatorios/gantt")
def rel_gantt():
    """Gráfico de Gantt com OPs e Etapas"""
    
    # Parâmetros de filtro
    obra_id = request.args.get("obra_id", type=int)
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    
    # Se não especificar datas, usar últimas 3 meses até 3 meses no futuro
    if not data_fim:
        data_fim = date.today() + timedelta(days=90)
    else:
        data_fim = parse_date(data_fim)
    
    if not data_inicio:
        data_inicio = date.today() - timedelta(days=90)
    else:
        data_inicio = parse_date(data_inicio)
    
    # Buscar obras
    obras = Obra.query.order_by(Obra.codigo.asc()).all()
    
    # Buscar OPs
    query = OP.query
    if obra_id:
        query = query.filter_by(obra_id=obra_id)
    
    ops = query.order_by(OP.id.desc()).all()
    
    # Preparar dados para o Gantt
    gantt_data = []
    
    for op in ops:
        # Usar prev_inicio e prev_fim da OP, ou calcular a partir das etapas
        op_inicio = op.prev_inicio
        op_fim = op.prev_fim
        
        # Se não tiver datas previstas, calcular a partir das etapas
        if not op_inicio or not op_fim:
            etapas_com_data = [e for e in op.etapas if e.data_inicio and e.data_fim]
            if etapas_com_data:
                op_inicio = min(e.data_inicio.date() for e in etapas_com_data)
                op_fim = max(e.data_fim.date() for e in etapas_com_data)
        
        # Se ainda não tiver datas, usar data de emissão
        if not op_inicio:
            op_inicio = op.data_emissao
        if not op_fim:
            op_fim = op.data_emissao + timedelta(days=30)
        
        # Filtrar por período
        if op_fim < data_inicio or op_inicio > data_fim:
            continue
        
        # Preparar etapas
        etapas_gantt = []
        for etapa in op.etapas:
            etapa_inicio = etapa.data_inicio
            etapa_fim = etapa.data_fim
            
            # Se não tiver datas, usar a OP como referência
            if not etapa_inicio:
                etapa_inicio = op_inicio
            if not etapa_fim:
                etapa_fim = op_fim
            
            if isinstance(etapa_inicio, datetime):
                etapa_inicio = etapa_inicio.date()
            if isinstance(etapa_fim, datetime):
                etapa_fim = etapa_fim.date()
            
            etapas_gantt.append({
                'id': f"etapa_{etapa.id}",
                'nome': etapa.nome,
                'inicio': etapa_inicio.isoformat(),
                'fim': etapa_fim.isoformat(),
                'percentual': etapa.percentual or 0,
                'status': etapa.status,
                'responsavel': etapa.responsavel.nome if etapa.responsavel else '-'
            })
        
        gantt_data.append({
            'id': f"op_{op.id}",
            'nome': f"OP {op.numero} - {op.produto}",
            'inicio': op_inicio.isoformat(),
            'fim': op_fim.isoformat(),
            'percentual': op.percentual,
            'status': op.status,
            'obra': op.obra.codigo,
            'etapas': etapas_gantt
        })
    
    return render_template(
        "gantt.html",
        gantt_data=gantt_data,
        obras=obras,
        obra_id=obra_id,
        data_inicio=data_inicio.strftime("%Y-%m-%d"),
        data_fim=data_fim.strftime("%Y-%m-%d")
    )


@app.route("/api/obra/<int:obra_id>/ops")
def api_obra_ops(obra_id):
    """API para buscar OPs de uma obra"""
    ops = OP.query.filter_by(obra_id=obra_id).order_by(OP.numero.asc()).all()
    return {
        "ops": [
            {"id": op.id, "numero": op.numero}
            for op in ops
        ]
    }


@app.route("/api/op/<int:op_id>/etapas")
def api_op_etapas(op_id):
    """API para buscar etapas de uma OP"""
    etapas = Etapa.query.filter_by(op_id=op_id).order_by(Etapa.id.asc()).all()
    return {
        "etapas": [
            {"id": etapa.id, "nome": etapa.nome}
            for etapa in etapas
        ]
    }


# --

# ========== RELATÓRIOS (TAREFAS POR PRODUTO E HORAS POR OPERADOR) ==========

@app.route("/relatorios/tarefas-produto")
def rel_tarefas_produto():
    """Relatório de tarefas agrupadas por produto"""
    relatorio = []
    
    # Buscar todas as OPs
    ops = OP.query.all()
    
    total_geral_horas = 0
    obras_set = set()
    produtos_set = set()
    
    for op in ops:
        tarefas = []
        total_horas = 0
        
        # Buscar todas as etapas da OP
        for etapa in op.etapas:
            for tarefa in etapa.tarefas:
                horas = tarefa.horas_previstas or 0
                tarefas.append({
                    'tarefa': tarefa.titulo,
                    'etapa': etapa.nome,
                    'responsavel': tarefa.responsavel.nome if tarefa.responsavel else '-',
                    'horas': horas,
                    'status': tarefa.status,
                    'data_inicio': tarefa.data_inicio_prev.strftime('%d/%m/%Y') if tarefa.data_inicio_prev else '-',
                    'data_fim': tarefa.data_fim_prev.strftime('%d/%m/%Y') if tarefa.data_fim_prev else '-'
                })
                total_horas += horas
        
        if tarefas:
            relatorio.append({
                'produto': op.produto,
                'op_numero': op.numero,
                'obra': op.obra.nome if op.obra else '-',
                'tarefas': tarefas,
                'total_horas': total_horas,
                'total_tarefas': len(tarefas)
            })
            total_geral_horas += total_horas
            if op.obra:
                obras_set.add(op.obra.nome)
            produtos_set.add(op.produto)
    
    # Calcular resumo
    resumo = {
        'total_obras': len(obras_set),
        'total_produtos': len(produtos_set),
        'total_horas': total_geral_horas,
        'media_horas': total_geral_horas / len(produtos_set) if produtos_set else 0
    }
    
    return render_template(
        'rel_tarefas_produto.html',
        relatorio=relatorio,
        resumo=resumo
    )


@app.route("/relatorios/horas-operador")
def rel_horas_operador():
    """Relatório de horas agrupadas por operador"""
    relatorio = []
    total_geral = 0
    
    # Buscar todos os operadores
    operadores = Operador.query.filter_by(ativo=True).order_by(Operador.nome.asc()).all()
    
    for operador in operadores:
        tarefas = []
        total_horas = 0
        
        # Buscar todas as tarefas do operador
        tarefas_operador = Tarefa.query.filter_by(responsavel_id=operador.id).all()
        
        for tarefa in tarefas_operador:
            if not tarefa.etapa or not tarefa.etapa.op:
                continue
            
            horas = tarefa.horas_previstas or 0
            op = tarefa.etapa.op
            
            tarefas.append({
                'tarefa': tarefa.titulo,
                'etapa': tarefa.etapa.nome,
                'produto': op.produto,
                'op_numero': op.numero,
                'obra': op.obra.nome if op.obra else '-',
                'horas': horas,
                'status': tarefa.status,
                'data_inicio': tarefa.data_inicio_prev.strftime('%d/%m/%Y') if tarefa.data_inicio_prev else '-',
                'data_fim': tarefa.data_fim_prev.strftime('%d/%m/%Y') if tarefa.data_fim_prev else '-'
            })
            total_horas += horas
            total_geral += horas
        
        if tarefas:
            relatorio.append({
                'operador': operador.nome,
                'tarefas': tarefas,
                'total_horas': total_horas,
                'total_tarefas': len(tarefas)
            })
    
    return render_template(
        'rel_horas_operador.html',
        relatorio=relatorio,
        total_geral=total_geral
    )



# ========== RELATÓRIO: O QUE OPERADOR FARÁ EM UM PERÍODO ==========

@app.route("/relatorios/calendario-2026")
def calendario_2026():
    """Calendário de planejamento para 2026"""
    meses_data = []
    obras = Obra.query.all()
    
    # Coletar todas as datas dentro de intervalos de OBRAS
    datas_planejadas = set()
    obras_por_data = {}  # Para mostrar no modal - dados da Obra
    
    for obra in obras:
        # Usar datas de Montagem Eletromecanica
        if obra.montagem_eletro_inicio and obra.montagem_eletro_fim:
            # Converter para date se forem datetime
            data_inicio = obra.montagem_eletro_inicio.date() if hasattr(obra.montagem_eletro_inicio, 'date') else obra.montagem_eletro_inicio
            data_fim = obra.montagem_eletro_fim.date() if hasattr(obra.montagem_eletro_fim, 'date') else obra.montagem_eletro_fim
            
            # Pintar todo o intervalo entre data_inicio e prev_fim da obra
            data_atual = data_inicio
            while data_atual <= data_fim:
                if data_atual.year == 2026:
                    datas_planejadas.add(data_atual)
                    
                    # Preparar dados para o modal - dados da Obra
                    data_str = f"{data_atual.month}-{data_atual.day}"
                    if data_str not in obras_por_data:
                        obras_por_data[data_str] = []
                    
                    # Coletar produtos da Obra
                    produtos = []
                    for obra_produto in obra.produtos:
                        if obra_produto.produto:
                            produtos.append(obra_produto.produto.nome)
                    
                    # Adicionar dados da Obra (evitar duplicatas)
                    obra_info = {
                        'obra_codigo': obra.codigo,
                        'obra_nome': obra.nome,
                        'obra_cliente': obra.cliente,
                        'produtos': produtos,
                        'data_inicio': data_inicio.strftime('%d/%m/%Y'),
                        'data_fim': data_fim.strftime('%d/%m/%Y')
                    }
                    
                    # Verificar se já existe para evitar duplicatas
                    if not any(o['obra_codigo'] == obra_info['obra_codigo'] for o in obras_por_data[data_str]):
                        obras_por_data[data_str].append(obra_info)
                
                data_atual += timedelta(days=1)
        elif obra.montagem_eletro_inicio:
            # Se só tem data de início de Montagem Eletromecanica
            data_inicio = obra.montagem_eletro_inicio.date() if hasattr(obra.montagem_eletro_inicio, 'date') else obra.montagem_eletro_inicio
            if data_inicio.year == 2026:
                datas_planejadas.add(data_inicio)
                data_str = f"{data_inicio.month}-{data_inicio.day}"
                if data_str not in obras_por_data:
                    obras_por_data[data_str] = []
                
                # Coletar produtos da Obra
                produtos = []
                for obra_produto in obra.produtos:
                    if obra_produto.produto:
                        produtos.append(obra_produto.produto.nome)
                
                # Adicionar dados da Obra
                obra_info = {
                    'obra_codigo': obra.codigo,
                    'obra_nome': obra.nome,
                    'obra_cliente': obra.cliente,
                    'produtos': produtos,
                    'data_inicio': data_inicio.strftime('%d/%m/%Y'),
                    'data_fim': 'N/A'
                }
                
                # Verificar se já existe para evitar duplicatas
                if not any(o['obra_codigo'] == obra_info['obra_codigo'] for o in obras_por_data[data_str]):
                    obras_por_data[data_str].append(obra_info)
    
    # Criar calendário para cada mês de 2026
    nomes_meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    # Configurar para começar com domingo
    calendar.setfirstweekday(calendar.SUNDAY)
    
    for mes_num in range(1, 13):
        # Obter calendário do mês
        cal = calendar.monthcalendar(2026, mes_num)
        
        # Flatten para uma lista de dias
        dias = []
        for semana in cal:
            dias.extend(semana)
        
        # Datas planejadas neste mês
        datas_mes_planejadas = set()
        for data in datas_planejadas:
            if data.year == 2026 and data.month == mes_num:
                datas_mes_planejadas.add(data.day)
        
        meses_data.append({
            'nome': nomes_meses[mes_num - 1],
            'numero': mes_num,
            'dias': dias,
            'datas_planejadas': datas_mes_planejadas
        })
    
    return render_template(
        "calendario_2026.html",
        meses=meses_data,
        total_datas_planejadas=len(datas_planejadas),
        obras_por_data=obras_por_data
    )


@app.route("/api/produto/<produto_nome>/datas-eletromecanica")
def api_produto_datas_eletromecanica(produto_nome):
    """API para puxar datas de Montagem Eletromecanica de todas as obras que contem o produto"""
    
    # Buscar o produto
    produto = Produto.query.filter(Produto.nome == produto_nome).first()
    
    if not produto:
        return jsonify({
            'data_inicio': '',
            'data_fim': ''
        })
    
    # Buscar todas as Obras que contem este produto (via ObraProduto)
    obras_produtos = ObraProduto.query.filter(ObraProduto.produto_id == produto.id).all()
    
    # Buscar as datas de Montagem Eletromecanica de todas as obras
    datas_inicio = []
    datas_fim = []
    
    for obra_produto in obras_produtos:
        obra = obra_produto.obra
        if obra:
            if obra.montagem_eletro_inicio:
                datas_inicio.append(obra.montagem_eletro_inicio)
            if obra.montagem_eletro_fim:
                datas_fim.append(obra.montagem_eletro_fim)
    
    # Encontrar a data mínima e máxima
    data_inicio_min = min(datas_inicio) if datas_inicio else None
    data_fim_max = max(datas_fim) if datas_fim else None
    
    return jsonify({
        'data_inicio': data_inicio_min.strftime('%Y-%m-%d') if data_inicio_min else '',
        'data_fim': data_fim_max.strftime('%Y-%m-%d') if data_fim_max else ''
    })


@app.route("/relatorios/produto-periodo", methods=["GET", "POST"])
def rel_produto_periodo():
    """Relatório mostrando quantos produtos serão produzidos em um período"""
    
    # Buscar parâmetros de filtro
    produto_nome = request.args.get("produto") or request.form.get("produto")
    data_inicio_str = request.args.get("data_inicio") or request.form.get("data_inicio")
    data_fim_str = request.args.get("data_fim") or request.form.get("data_fim")
    
    # Converter datas
    data_inicio = None
    data_fim = None
    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
        except:
            pass
    if data_fim_str:
        try:
            data_fim = datetime.strptime(data_fim_str, "%Y-%m-%d").date()
        except:
            pass
    
    # Se não tiver datas, usar mês atual
    if not data_inicio or not data_fim:
        hoje = date.today()
        data_inicio = date(hoje.year, hoje.month, 1)
        if hoje.month == 12:
            data_fim = date(hoje.year + 1, 1, 1) - timedelta(days=1)
        else:
            data_fim = date(hoje.year, hoje.month + 1, 1) - timedelta(days=1)
    
    # Buscar todos os produtos
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome.asc()).all()
    
    # Montar relatório
    relatorio = []
    total_geral = 0
    
    # Se um produto foi selecionado
    if produto_nome:
        # Buscar OPs e filtrar por datas de Montagem Eletromecanica da obra
        ops_todas = OP.query.filter(
            OP.produto == produto_nome
        ).order_by(OP.numero.asc()).all()
        
        # Filtrar por data de Montagem Eletromecanica da obra
        ops_periodo = []
        for op in ops_todas:
            if op.obra:
                # Verificar se a Montagem Eletromecanica da obra está no período
                if op.obra.montagem_eletro_inicio and op.obra.montagem_eletro_fim:
                    data_inicio_obra = op.obra.montagem_eletro_inicio.date() if hasattr(op.obra.montagem_eletro_inicio, 'date') else op.obra.montagem_eletro_inicio
                    data_fim_obra = op.obra.montagem_eletro_fim.date() if hasattr(op.obra.montagem_eletro_fim, 'date') else op.obra.montagem_eletro_fim
                    
                    # Verificar se o período da obra sobrepõe com o período filtrado
                    if data_inicio_obra <= data_fim and data_fim_obra >= data_inicio:
                        ops_periodo.append(op)
                elif op.obra.montagem_eletro_inicio:
                    # Se só tem data de início
                    data_inicio_obra = op.obra.montagem_eletro_inicio.date() if hasattr(op.obra.montagem_eletro_inicio, 'date') else op.obra.montagem_eletro_inicio
                    if data_inicio <= data_inicio_obra <= data_fim:
                        ops_periodo.append(op)
        
        ops_detalhes = []
        total_quantidade = 0
        
        for op in ops_periodo:
            # Buscar operador responsável (da primeira tarefa)
            operador_nome = "-"
            if op.etapas and op.etapas[0].tarefas:
                tarefa = op.etapas[0].tarefas[0]
                if tarefa.responsavel:
                    operador_nome = tarefa.responsavel.nome
            
            ops_detalhes.append({
                'numero': op.numero,
                'quantidade': op.quantidade,
                'status': op.status,
                'data_inicio': op.prev_inicio.strftime('%d/%m/%Y') if op.prev_inicio else '-',
                'data_fim': op.prev_fim.strftime('%d/%m/%Y') if op.prev_fim else '-',
                'obra': op.obra.nome if op.obra else '-',
                'operador': operador_nome,
                'percentual': op.percentual_calc
            })
            total_quantidade += op.quantidade
        
        if ops_detalhes:
            relatorio.append({
                'produto': produto_nome,
                'ops': ops_detalhes,
                'total_quantidade': total_quantidade,
                'total_ops': len(ops_detalhes)
            })
            total_geral = total_quantidade
    
    return render_template(
        'rel_produto_periodo.html',
        relatorio=relatorio,
        produtos=produtos,
        produto_selecionado=produto_nome,
        data_inicio=data_inicio.strftime('%Y-%m-%d') if data_inicio else '',
        data_fim=data_fim.strftime('%Y-%m-%d') if data_fim else '',
        total_geral=total_geral
    )


@app.route("/relatorios/obras-produto-periodo", methods=["GET", "POST"])
def rel_obras_produto_periodo():
    """Relatório mostrando Obras filtradas por Produto e Período (Montagem Eletromecanica)"""
    
    # Buscar parâmetros de filtro
    produto_nome = request.args.get("produto") or request.form.get("produto")
    data_inicio_str = request.args.get("data_inicio") or request.form.get("data_inicio")
    data_fim_str = request.args.get("data_fim") or request.form.get("data_fim")
    
    # Converter datas
    data_inicio = None
    data_fim = None
    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
        except:
            pass
    if data_fim_str:
        try:
            data_fim = datetime.strptime(data_fim_str, "%Y-%m-%d").date()
        except:
            pass
    
    # Se não tiver datas, usar mês atual
    if not data_inicio or not data_fim:
        hoje = date.today()
        data_inicio = date(hoje.year, hoje.month, 1)
        if hoje.month == 12:
            data_fim = date(hoje.year + 1, 1, 1) - timedelta(days=1)
        else:
            data_fim = date(hoje.year, hoje.month + 1, 1) - timedelta(days=1)
    
    # Buscar todos os produtos
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome.asc()).all()
    
    # Montar relatório
    relatorio = []
    
    # Se um produto foi selecionado
    if produto_nome:
        # Buscar o produto
        produto = Produto.query.filter(Produto.nome == produto_nome).first()
        
        if produto:
            # Buscar todas as Obras que contêm este produto (via ObraProduto)
            obras_produtos = ObraProduto.query.filter(ObraProduto.produto_id == produto.id).all()
            
            obras_detalhes = []
            
            for obra_produto in obras_produtos:
                obra = obra_produto.obra
                if obra:
                    # Verificar se a Montagem Eletromecanica da obra está no período
                    if obra.montagem_eletro_inicio and obra.montagem_eletro_fim:
                        data_inicio_obra = obra.montagem_eletro_inicio.date() if hasattr(obra.montagem_eletro_inicio, 'date') else obra.montagem_eletro_inicio
                        data_fim_obra = obra.montagem_eletro_fim.date() if hasattr(obra.montagem_eletro_fim, 'date') else obra.montagem_eletro_fim
                        
                        # Verificar se o período da obra sobrepõe com o período filtrado
                        if data_inicio_obra <= data_fim and data_fim_obra >= data_inicio:
                            obras_detalhes.append({
                                'codigo': obra.codigo,
                                'nome': obra.nome,
                                'cliente': obra.cliente,
                                'status': obra.status,
                                'corte_dobra_inicio': obra.corte_dobra_inicio.strftime('%d/%m/%Y') if obra.corte_dobra_inicio else '-',
                                'corte_dobra_fim': obra.corte_dobra_fim.strftime('%d/%m/%Y') if obra.corte_dobra_fim else '-',
                                'montagem_eletro_inicio': obra.montagem_eletro_inicio.strftime('%d/%m/%Y') if obra.montagem_eletro_inicio else '-',
                                'montagem_eletro_fim': obra.montagem_eletro_fim.strftime('%d/%m/%Y') if obra.montagem_eletro_fim else '-',
                                'quantidade': obra_produto.quantidade
                            })
                    elif obra.montagem_eletro_inicio:
                        # Se só tem data de início
                        data_inicio_obra = obra.montagem_eletro_inicio.date() if hasattr(obra.montagem_eletro_inicio, 'date') else obra.montagem_eletro_inicio
                        if data_inicio <= data_inicio_obra <= data_fim:
                            obras_detalhes.append({
                                'codigo': obra.codigo,
                                'nome': obra.nome,
                                'cliente': obra.cliente,
                                'status': obra.status,
                                'corte_dobra_inicio': obra.corte_dobra_inicio.strftime('%d/%m/%Y') if obra.corte_dobra_inicio else '-',
                                'corte_dobra_fim': obra.corte_dobra_fim.strftime('%d/%m/%Y') if obra.corte_dobra_fim else '-',
                                'montagem_eletro_inicio': obra.montagem_eletro_inicio.strftime('%d/%m/%Y') if obra.montagem_eletro_inicio else '-',
                                'montagem_eletro_fim': obra.montagem_eletro_fim.strftime('%d/%m/%Y') if obra.montagem_eletro_fim else '-',
                                'quantidade': obra_produto.quantidade
                            })
            
            if obras_detalhes:
                relatorio.append({
                    'produto': produto_nome,
                    'obras': obras_detalhes,
                    'total_obras': len(obras_detalhes)
                })
    
    return render_template(
        'rel_obras_produto_periodo.html',
        relatorio=relatorio,
        produtos=produtos,
        produto_selecionado=produto_nome,
        data_inicio=data_inicio.strftime('%Y-%m-%d') if data_inicio else '',
        data_fim=data_fim.strftime('%Y-%m-%d') if data_fim else ''
    )


@app.route("/relatorios/operador-periodo", methods=["GET", "POST"])
def rel_operador_periodo():
    """Relatório mostrando o que cada operador fará em um período"""
    
    # Buscar parâmetros de filtro
    operador_id = request.args.get("operador_id") or request.form.get("operador_id")
    data_inicio_str = request.args.get("data_inicio") or request.form.get("data_inicio")
    data_fim_str = request.args.get("data_fim") or request.form.get("data_fim")
    
    # Converter datas
    data_inicio = None
    data_fim = None
    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
        except:
            pass
    if data_fim_str:
        try:
            data_fim = datetime.strptime(data_fim_str, "%Y-%m-%d").date()
        except:
            pass
    
    # Se não tiver datas, usar semana atual
    if not data_inicio or not data_fim:
        hoje = date.today()
        data_inicio = hoje - timedelta(days=hoje.weekday())
        data_fim = data_inicio + timedelta(days=6)
    
    # Buscar operadores
    operadores = Operador.query.filter_by(ativo=True).order_by(Operador.nome.asc()).all()
    
    # Filtrar por operador se selecionado
    if operador_id:
        operadores = [op for op in operadores if op.id == int(operador_id)]
    
    # Montar relatório
    relatorio = []
    for operador in operadores:
        tarefas_periodo = []
        total_horas = 0
        
        # Buscar todas as tarefas do operador
        tarefas = Tarefa.query.filter_by(responsavel_id=operador.id).all()
        
        for tarefa in tarefas:
            if not tarefa.data_inicio_prev or not tarefa.data_fim_prev:
                continue
            if not tarefa.etapa or not tarefa.etapa.op:
                continue
            
            # Verificar se a tarefa está no período
            if tarefa.data_inicio_prev <= data_fim and tarefa.data_fim_prev >= data_inicio:
                horas = tarefa.horas_previstas or 0
                op = tarefa.etapa.op
                
                tarefas_periodo.append({
                    'tarefa': tarefa.titulo,
                    'etapa': tarefa.etapa.nome,
                    'produto': op.produto,
                    'op_numero': op.numero,
                    'obra': op.obra.nome if op.obra else '-',
                    'horas': horas,
                    'status': tarefa.status,
                    'data_inicio': tarefa.data_inicio_prev.strftime('%d/%m/%Y'),
                    'data_fim': tarefa.data_fim_prev.strftime('%d/%m/%Y')
                })
                total_horas += horas
        
        if tarefas_periodo:
            relatorio.append({
                'operador': operador.nome,
                'tarefas': tarefas_periodo,
                'total_horas': total_horas,
                'total_tarefas': len(tarefas_periodo)
            })
    
    return render_template(
        'rel_operador_periodo.html',
        relatorio=relatorio,
        operadores=operadores,
        operador_id=operador_id,
        data_inicio=data_inicio.strftime('%Y-%m-%d') if data_inicio else '',
        data_fim=data_fim.strftime('%Y-%m-%d') if data_fim else ''
    )


# --------- IMPRESSÃO DE TAREFA ---------

@app.route("/tarefas/<int:tarefa_id>/imprimir")
def imprimir_tarefa(tarefa_id):
    from datetime import datetime
    tarefa = Tarefa.query.get_or_404(tarefa_id)
    etapa = tarefa.etapa
    op = etapa.op
    obra = op.obra
    
    return render_template("tarefa_impressao.html", 
                         tarefa=tarefa, 
                         etapa=etapa, 
                         op=op, 
                         obra=obra,
                         now=datetime.now())


# ------------ START ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    """Página de login"""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "").strip()
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and usuario.verificar_senha(senha) and usuario.ativo:
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            session['usuario_tipo'] = usuario.tipo
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", erro="Email ou senha incorretos")
    
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Fazer logout"""
    session.clear()
    return redirect(url_for("login"))


# ============ ROTAS DE MATERIAIS ============

@app.route("/materiais", methods=["GET", "POST"])
def materiais():
    """Página de Materiais - Pendências"""
    
    obras = Obra.query.order_by(Obra.nome.asc()).all()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome.asc()).all()
    pendencias = []
    
    # Se for POST, adicionar nova pendência
    if request.method == "POST":
        obra_id = request.form.get("obra_id")
        produto_id = request.form.get("produto_id")
        descricao = request.form.get("descricao")
        
        if obra_id and produto_id and descricao:
            pendencia = PendenciaMaterial(
                obra_id=int(obra_id),
                produto_id=int(produto_id),
                descricao=descricao,
                status="PENDENTE"
            )
            db.session.add(pendencia)
            db.session.commit()
            
            print(f"✅ Pendência de material criada: {descricao}")
    
    # Buscar todas as pendências
    pendencias = PendenciaMaterial.query.order_by(PendenciaMaterial.data_criacao.desc()).all()
    
    return render_template(
        "materiais.html",
        obras=obras,
        produtos=produtos,
        pendencias=pendencias
    )


@app.route("/materiais/<int:pendencia_id>/atualizar-status", methods=["POST"])
def atualizar_status_pendencia(pendencia_id):
    """Atualizar status de uma pendência"""
    
    pendencia = PendenciaMaterial.query.get(pendencia_id)
    if not pendencia:
        return jsonify({"erro": "Pendência não encontrada"}), 404
    
    novo_status = request.form.get("status")
    
    if novo_status in ["PENDENTE", "RECEBIDO", "CANCELADO"]:
        pendencia.status = novo_status
        pendencia.data_atualizacao = datetime.now()
        db.session.commit()
        
        print(f"✅ Status da pendência atualizado para: {novo_status}")
        return redirect(url_for("materiais"))
    
    return jsonify({"erro": "Status inválido"}), 400


@app.route("/materiais/<int:pendencia_id>/deletar", methods=["POST"])
def deletar_pendencia(pendencia_id):
    """Deletar uma pendência"""
    
    pendencia = PendenciaMaterial.query.get(pendencia_id)
    if not pendencia:
        return jsonify({"erro": "Pendência não encontrada"}), 404
    
    db.session.delete(pendencia)
    db.session.commit()
    
    print(f"✅ Pendência deletada")
    return redirect(url_for("materiais"))


@app.route("/api/materiais/filtrar", methods=["GET"])
def api_filtrar_materiais():
    """API para filtrar pendências por obra"""
    
    obra_id = request.args.get("obra_id")
    
    if not obra_id:
        return jsonify([])
    
    pendencias = PendenciaMaterial.query.filter_by(obra_id=int(obra_id)).all()
    
    resultado = []
    for p in pendencias:
        resultado.append({
            "id": p.id,
            "produto": p.produto.nome,
            "descricao": p.descricao,
            "status": p.status,
            "data_criacao": p.data_criacao.strftime("%d/%m/%Y %H:%M")
        })
    
    return jsonify(resultado)


@app.route("/api/obras/<int:obra_id>/produtos", methods=["GET"])
def api_produtos_por_obra(obra_id):
    """API para obter produtos de uma obra"""
    
    # Buscar a obra
    obra = Obra.query.get(obra_id)
    if not obra:
        return jsonify({"erro": "Obra não encontrada"}), 404
    
    # Buscar produtos da obra via ObraProduto
    obras_produtos = ObraProduto.query.filter_by(obra_id=obra_id).all()
    
    resultado = []
    for op in obras_produtos:
        resultado.append({
            "id": op.produto_id,
            "nome": op.produto.nome,
            "quantidade": op.quantidade
        })
    
    return jsonify(resultado)


@app.route("/api/produtos/<int:produto_id>/detalhes", methods=["GET"])
def api_detalhes_produto(produto_id):
    """API para obter detalhes de um produto"""
    
    produto = Produto.query.get(produto_id)
    if not produto:
        return jsonify({"erro": "Produto não encontrado"}), 404
    
    resultado = {
        "id": produto.id,
        "nome": produto.nome,
        "ativo": produto.ativo
    }
    
    return jsonify(resultado)


# ============ ROTAS DE PROJETOS ============

@app.route("/projetos", methods=["GET", "POST"])
def projetos():
    """Página de Projetos"""
    
    obras = Obra.query.order_by(Obra.nome.asc()).all()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome.asc()).all()
    
    # Se for POST, adicionar novo projeto
    if request.method == "POST":
        obra_id = request.form.get("obra_id")
        produto_id = request.form.get("produto_id")
        link = request.form.get("link")
        descricao = request.form.get("descricao")
        
        if obra_id and produto_id and link:
            projeto = ProjetoProduto(
                obra_id=int(obra_id),
                produto_id=int(produto_id),
                link=link,
                descricao=descricao
            )
            db.session.add(projeto)
            db.session.commit()
            
            print(f"✅ Projeto criado: {link}")
            return redirect(url_for("projetos"))
    
    # Buscar todos os projetos
    projetos_list = ProjetoProduto.query.order_by(ProjetoProduto.data_criacao.desc()).all()
    
    return render_template(
        "projetos.html",
        obras=obras,
        produtos=produtos,
        projetos=projetos_list
    )


@app.route("/projetos/<int:projeto_id>/deletar", methods=["POST"])
def deletar_projeto(projeto_id):
    """Deletar um projeto"""
    
    projeto = ProjetoProduto.query.get(projeto_id)
    if not projeto:
        return jsonify({"erro": "Projeto não encontrado"}), 404
    
    db.session.delete(projeto)
    db.session.commit()
    
    print(f"✅ Projeto deletado")
    return redirect(url_for("projetos"))


def criar_usuarios_padrao():
    """Cria os 4 usuarios padrao se nao existirem"""
    usuarios_padrao = [
        {"nome": "Admin", "email": "admin@nexon.com", "senha": "senha123", "tipo": "ADMIN"},
        {"nome": "Gerente", "email": "gerente@nexon.com", "senha": "senha123", "tipo": "GERENTE"},
        {"nome": "Operador", "email": "operador@nexon.com", "senha": "senha123", "tipo": "OPERADOR"},
        {"nome": "Visualizador", "email": "visualizador@nexon.com", "senha": "senha123", "tipo": "VISUALIZADOR"},
        {"nome": "Estrutura", "email": "estrutura@nexon.com", "senha": "senha123", "tipo": "ESPECIALISTA"},
        {"nome": "Caldeiraria", "email": "caldeiraria@nexon.com", "senha": "senha123", "tipo": "ESPECIALISTA"},
        {"nome": "Montagem", "email": "montagem@nexon.com", "senha": "senha123", "tipo": "ESPECIALISTA"},
        {"nome": "Startup", "email": "startup@nexon.com", "senha": "senha123", "tipo": "ESPECIALISTA"}
    ]
    
    for dados in usuarios_padrao:
        usuario_existente = Usuario.query.filter_by(email=dados["email"]).first()
        if not usuario_existente:
            usuario = Usuario(
                nome=dados["nome"],
                email=dados["email"],
                tipo=dados["tipo"],
                ativo=True
            )
            usuario.definir_senha(dados["senha"])
            db.session.add(usuario)
            print(f"✅ Usuario criado: {dados['email']} ({dados['tipo']})")
        else:
            print(f"⚠️ Usuario ja existe: {dados['email']}")
    
    db.session.commit()


# ============ MODO APRESENTAÇÃO - TELA CHEIA COM ROTAÇÃO ============

@app.route("/apresentacao")
def apresentacao():
    """Modo apresentação - tela cheia que muda a cada 10 segundos"""
    return render_template("apresentacao.html")


@app.route("/api/apresentacao")
def api_apresentacao():
    """API que retorna dados reais para o modo apresentação"""
    try:
        # ===== DASHBOARD =====
        total_obras = Obra.query.count()
        obras_abertas = Obra.query.filter_by(status="ATIVA").count()
        obras_em_exec = Obra.query.filter_by(status="EM_EXECUCAO").count()
        obras_concluidas = Obra.query.filter_by(status="CONCLUIDA").count()
        obras_atrasadas = Obra.query.filter_by(status="ATRASADA").count()
        
        total_ops = OP.query.count()
        ops_aberta = OP.query.filter_by(status="ABERTA").count()
        ops_em_prod = OP.query.filter_by(status="EM_PRODUCAO").count()
        ops_atrasada = OP.query.filter_by(status="ATRASADA").count()
        ops_concluida = OP.query.filter_by(status="CONCLUIDA").count()
        
        tarefas_concluidas = Tarefa.query.filter_by(status="CONCLUIDO").count()
        tarefas_em_execucao = Tarefa.query.filter_by(status="EM_EXECUCAO").count()
        tarefas_planejadas = Tarefa.query.filter_by(status="PLANEJADO").count()
        
        # Progresso médio
        ops_com_percentual = OP.query.all()
        if ops_com_percentual:
            progresso_medio = sum(op.percentual_calc for op in ops_com_percentual) / len(ops_com_percentual)
        else:
            progresso_medio = 0
        
        # ===== OBRAS =====
        todas_obras = Obra.query.order_by(Obra.corte_dobra_inicio.asc()).all()
        obras_pagina1 = todas_obras[:10]
        obras_pagina2 = todas_obras[10:20]
        obras = todas_obras[:20]
        obras_list = []
        for obra in obras:
            # Calcular % de conclusao da obra
            ops_obra = OP.query.filter_by(obra_id=obra.id).all()
            if ops_obra:
                percentual_obra = sum(op.percentual_calc for op in ops_obra) / len(ops_obra)
            else:
                percentual_obra = 0
            
            obras_list.append({
                'codigo': obra.codigo or 'N/A',
                'nome': obra.nome or 'Sem nome',
                'cliente': obra.cliente or 'N/A',
                'status': obra.status or 'N/A',
                'corte_dobra_inicio': obra.corte_dobra_inicio.strftime('%d/%m/%Y') if obra.corte_dobra_inicio else '-',
                'corte_dobra_fim': obra.corte_dobra_fim.strftime('%d/%m/%Y') if obra.corte_dobra_fim else '-',
                'montagem_eletro_inicio': obra.montagem_eletro_inicio.strftime('%d/%m/%Y') if obra.montagem_eletro_inicio else '-',
                'montagem_eletro_fim': obra.montagem_eletro_fim.strftime('%d/%m/%Y') if obra.montagem_eletro_fim else '-',
                'produtos': ', '.join([f"{item.produto.nome} ({item.quantidade})" if item.produto else f"Produto {item.quantidade}" for item in obra.produtos]) if obra.produtos and len(obra.produtos) > 0 else '-',
                'percentual': round(percentual_obra, 1)
            })
        
        # ===== OPs =====
        # Ordenar OPs pela data de início da obra (corte_dobra_inicio)
        ops = OP.query.join(Obra).order_by(Obra.corte_dobra_inicio.asc()).limit(20).all()
        ops_list = []
        for op in ops:
            cliente = op.obra.cliente if op.obra else 'N/A'
            obra_nome = op.obra.nome if op.obra else 'N/A'
            obra_codigo = op.obra.codigo if op.obra else 'N/A'
            
            corte_dobra_inicio = op.obra.corte_dobra_inicio.strftime('%d/%m/%Y') if op.obra and op.obra.corte_dobra_inicio else '-'
            corte_dobra_fim = op.obra.corte_dobra_fim.strftime('%d/%m/%Y') if op.obra and op.obra.corte_dobra_fim else '-'
            montagem_eletro_inicio = op.obra.montagem_eletro_inicio.strftime('%d/%m/%Y') if op.obra and op.obra.montagem_eletro_inicio else '-'
            montagem_eletro_fim = op.obra.montagem_eletro_fim.strftime('%d/%m/%Y') if op.obra and op.obra.montagem_eletro_fim else '-'
            
            ops_list.append({
                'numero': op.numero or f'OP{op.id}',
                'obra_codigo': obra_codigo,
                'cliente': cliente,
                'obra_nome': obra_nome,
                'produto': op.produto or 'Sem produto',
                'quantidade': op.quantidade or 0,
                'percentual': round(op.percentual_calc, 1),
                'status': op.status or 'N/A',
                'corte_dobra_inicio': corte_dobra_inicio,
                'corte_dobra_fim': corte_dobra_fim,
                'montagem_eletro_inicio': montagem_eletro_inicio,
                'montagem_eletro_fim': montagem_eletro_fim
            })
        
        return jsonify({
            'dashboard': {
                'total_obras': total_obras,
                'obras_ativas': obras_ativas,
                'obras_abertas': obras_abertas,
                'obras_em_exec': obras_em_exec,
                'obras_concluidas': obras_concluidas,
                'obras_atrasadas': obras_atrasadas,
                'total_ops': total_ops,
                'abertas': ops_aberta,
                'em_prod': ops_em_prod,
                'atrasadas': ops_atrasada,
                'concluidas': ops_concluida,
                'tarefas_concluidas': tarefas_concluidas,
                'tarefas_em_execucao': tarefas_em_execucao,
                'tarefas_planejadas': tarefas_planejadas,
                'progresso_medio': round(progresso_medio, 1)
            },
            'obras_pagina1': [o for o in obras_list if o in [obras_list[i] for i in range(min(10, len(obras_list)))]],
            'obras_pagina2': [o for o in obras_list if o in [obras_list[i] for i in range(10, min(20, len(obras_list)))]],
            'ops_pagina1': [op for op in ops_list if op in [ops_list[i] for i in range(min(10, len(ops_list)))]],
            'ops_pagina2': [op for op in ops_list if op in [ops_list[i] for i in range(10, min(20, len(ops_list)))]]
        })
    
    except Exception as e:
        print(f"[ERRO] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        criar_usuarios_padrao()
    app.run(host="0.0.0.0", port=5000, debug=True)



# Rota para sincronizar TODAS as OPs
@app.route("/admin/sincronizar-todas-etapas", methods=["POST"])
def admin_sincronizar_todas_etapas():
    """Sincroniza as etapas de TODAS as OPs com a lista de ETAPAS_FIXAS"""
    ops = OP.query.all()
    
    for op in ops:
        etapas_existentes = [e.nome for e in op.etapas]
        for etapa_nome in ETAPAS_FIXAS:
            if etapa_nome not in etapas_existentes:
                etapa = Etapa(op_id=op.id, nome=etapa_nome, status="PLANEJADO")
                db.session.add(etapa)
    
    db.session.commit()
    return redirect(url_for("ops"))



# ============ TELEGRAM NOTIFIER ============
