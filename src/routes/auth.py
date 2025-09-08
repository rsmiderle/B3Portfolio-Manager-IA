from flask import Blueprint, redirect, url_for, session, request, current_app, flash
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
import os
import urllib3
from src.models import db
from src.models.all_models import User

# Desabilitar avisos de SSL para evitar erros em requisições
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

oauth = OAuth()

@auth_bp.record_once
def on_load(state):
    app = state.app
    oauth.init_app(app)
    
    # Configurar o provedor Google OAuth
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            'verify': False  # Desabilitar verificação SSL para ambiente de desenvolvimento
        },
    )

@auth_bp.route('/login')
def login():
    # Detectar ambiente e usar o esquema apropriado
    scheme = 'https' if not current_app.debug or request.headers.get('X-Forwarded-Proto') == 'https' else 'http'
    redirect_uri = url_for('auth.callback', _external=True, _scheme=scheme)
    print(f"URI de redirecionamento: {redirect_uri}")  # Para depuração
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/callback')
def callback():
    # Processar o callback do Google OAuth
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if user_info:
        # Verificar se o usuário já existe
        user = User.query.filter_by(google_id=user_info['sub']).first()
        
        if not user:
            # Criar um novo usuário
            try:
                user = User(
                    email=user_info['email'],
                    name=user_info.get('name', ''),
                    profile_pic=user_info.get('picture', ''),
                    google_id=user_info['sub']
                )
                db.session.add(user)
                db.session.commit()
            except ValueError as e:
                # Log do erro crítico de configuração
                current_app.logger.error(f"FALHA CRÍTICA DE SEGURANÇA: {e}")
                # Mensagem para o usuário e redirecionamento
                flash('Ocorreu um erro de configuração de segurança no servidor que impede a criação de novos usuários. Por favor, contate o administrador.', 'danger')
                return redirect(url_for('main.index'))
        
        # Fazer login do usuário
        login_user(user)
        flash('Login realizado com sucesso!', 'success')
        
        # Redirecionar para o dashboard após login bem-sucedido
        return redirect(url_for('main.dashboard'))
    
    flash('Falha ao realizar login. Tente novamente.', 'danger')
    return redirect(url_for('main.index'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('main.index'))
