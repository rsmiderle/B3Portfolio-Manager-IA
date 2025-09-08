from datetime import datetime
import hashlib
import os
from flask_login import UserMixin
from src.models import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    profile_pic = db.Column(db.String(200), nullable=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    hash_id = db.Column(db.String(64), unique=True, nullable=False, index=True)  # Identificador anonimizado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    relatorios = db.relationship('Relatorio', backref='user', lazy=True, cascade="all, delete-orphan", 
                                foreign_keys="Relatorio.user_hash")
    acoes = db.relationship('Acao', backref='user', lazy=True, cascade="all, delete-orphan",
                           foreign_keys="Acao.user_hash")
    saldos = db.relationship('SaldoPrecoMedio', backref='user', lazy=True, cascade="all, delete-orphan",
                            foreign_keys="SaldoPrecoMedio.user_hash")
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        # Gera automaticamente o hash_id ao criar o usuário
        if self.google_id:
            self.generate_hash_id()
    
    def generate_hash_id(self):
        """Gera um identificador anonimizado baseado no Google ID usando salt da variável de ambiente"""
        # Obtém o salt da variável de ambiente. Lança um erro se não estiver definido.
        salt = os.environ.get('ANONYMIZATION_SALT')
        if not salt or salt == 'DEFAULT_SALT_CHANGE_IN_PRODUCTION':
            raise ValueError("ANONYMIZATION_SALT não está definida ou está usando o valor padrão inseguro. Esta variável é obrigatória para a segurança do sistema.")

        # Combina o Google ID com o salt e gera um hash SHA-256
        hash_input = f"{self.google_id}{salt}"
        self.hash_id = hashlib.sha256(hash_input.encode()).hexdigest()
    
    def is_admin(self):
        """Verifica se o usuário é administrador com base na variável de ambiente ADMIN_EMAIL"""
        admin_email = os.environ.get('ADMIN_EMAIL')
        if not admin_email:
            return False
        
        # Compara o email do usuário com o email de administrador definido na variável de ambiente
        return self.email.lower() == admin_email.lower()
    
    def __repr__(self):
        return f'<User {self.email}>'
