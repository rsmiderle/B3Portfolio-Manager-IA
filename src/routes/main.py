from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from flask_login import login_required, current_user
from wtforms import DateField, SubmitField
from wtforms.validators import DataRequired
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from src.models import db
from src.models.all_models import Acao, Negociacao, SaldoPrecoMedio

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('dashboard.html')
    return render_template('login.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

class RelatorioForm(FlaskForm):
    data_base = DateField('Data Base', validators=[DataRequired()])
    submit = SubmitField('Gerar Relatório')

@main_bp.route('/gerar_relatorio', methods=['GET', 'POST'])
@login_required
def gerar_relatorio():
    form = RelatorioForm()
    if form.validate_on_submit():
        data_base = form.data_base.data
        resultado = calcular_posicao_na_data(data_base)
        return render_template('relatorio_resultado.html', 
                              resultado=resultado, 
                              data_base=data_base)
    
    return render_template('gerar_relatorio.html')

def calcular_posicao_na_data(data_base):
    """
    Calcula a posição (saldo e preço médio) de cada ação na data base informada.
    Considera todas as negociações até a data e os saldos cadastrados.
    Inclui o valor de corretagem no cálculo do preço médio para operações de compra.
    """
    resultado = []
    
    # Buscar todas as ações que possuem negociações ou saldos cadastrados
    acoes = db.session.query(Acao).join(
        Negociacao, Acao.id == Negociacao.acao_id, isouter=True
    ).join(
        SaldoPrecoMedio, Acao.id == SaldoPrecoMedio.acao_id, isouter=True
    ).filter(
        db.or_(
            Negociacao.id != None,
            SaldoPrecoMedio.id != None
        ),
        Acao.user_hash == current_user.hash_id  # Filtrar apenas ações do usuário atual
    ).distinct().all()
    
    for acao in acoes:
        # Buscar o saldo mais recente cadastrado antes da data base
        saldo_cadastrado = SaldoPrecoMedio.query.filter(
            SaldoPrecoMedio.acao_id == acao.id,
            SaldoPrecoMedio.data_base <= data_base,
            SaldoPrecoMedio.user_hash == current_user.hash_id  # Filtrar apenas saldos do usuário atual
        ).order_by(SaldoPrecoMedio.data_base.desc()).first()
        
        data_inicial = None
        saldo_inicial = 0
        preco_medio_inicial = 0
        
        if saldo_cadastrado:
            data_inicial = saldo_cadastrado.data_base
            saldo_inicial = saldo_cadastrado.quantidade
            preco_medio_inicial = saldo_cadastrado.preco_medio
        
        # Buscar todas as negociações entre a data inicial e a data base
        negociacoes = Negociacao.query.filter(
            Negociacao.acao_id == acao.id,
            Negociacao.data_negocio <= data_base,
            Negociacao.user_hash == current_user.hash_id  # Filtrar apenas negociações do usuário atual
        )
        
        if data_inicial:
            negociacoes = negociacoes.filter(Negociacao.data_negocio > data_inicial)
            
        negociacoes = negociacoes.order_by(Negociacao.data_negocio).all()
        
        # Calcular saldo e preço médio
        saldo = saldo_inicial
        preco_medio = preco_medio_inicial
        valor_investido = saldo_inicial * preco_medio_inicial
        
        for neg in negociacoes:
            if neg.tipo_movimentacao == 'Compra':
                # Calcular o valor total da compra incluindo corretagem
                valor_compra = neg.quantidade * neg.preco
                
                # Adicionar corretagem ao valor investido se informada
                if neg.corretagem is not None and neg.corretagem > 0:
                    valor_compra += neg.corretagem
                
                # Atualizar valor investido e saldo
                valor_investido += valor_compra
                saldo += neg.quantidade
                
                # Recalcular preço médio
                if saldo > 0:
                    preco_medio = valor_investido / saldo
            elif neg.tipo_movimentacao == 'Venda':
                # Atualizar saldo
                saldo -= neg.quantidade
                
                # Se o saldo zerar ou ficar negativo, reiniciar o preço médio
                if saldo <= 0:
                    valor_investido = 0
                    preco_medio = 0
                    # Se ficar negativo (erro nos dados), corrigir para zero
                    if saldo < 0:
                        saldo = 0
        
        # Só adicionar ao resultado se tiver saldo
        if saldo > 0:
            # Buscar CNPJ se não estiver cadastrado
            cnpj = acao.cnpj
            if not cnpj:
                cnpj = buscar_cnpj_online(acao.codigo)
                # Atualizar o CNPJ no banco se encontrado
                if cnpj and cnpj != "CNPJ não encontrado":
                    acao.cnpj = cnpj
                    db.session.commit()
            
            resultado.append({
                'codigo': acao.codigo,
                'quantidade': saldo,
                'preco_medio': preco_medio,
                'valor_total': saldo * preco_medio,
                'cnpj': cnpj or "CNPJ não cadastrado"
            })
    
    # Ordenar por código da ação
    resultado.sort(key=lambda x: x['codigo'])
    
    return resultado

def buscar_cnpj_online(codigo_acao):
    """Busca o CNPJ da ação na internet"""
    try:
        # Desabilitar verificação de SSL para evitar erros
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Fazer a busca no Google
        url = f"https://www.google.com/search?q=cnpj+{codigo_acao}+b3+bovespa"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Procurar por padrões de CNPJ (XX.XXX.XXX/XXXX-XX)
            text = soup.get_text()
            cnpj_pattern = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}'
            cnpj_matches = re.findall(cnpj_pattern, text)
            
            if cnpj_matches:
                return cnpj_matches[0]
        
        return "CNPJ não encontrado"
    except Exception as e:
        return f"Erro ao buscar CNPJ: {str(e)}"
