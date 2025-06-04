from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import pdfkit
import os
from sqlalchemy import text, inspect
from pytz import timezone
import time

# Configurar o fuso horário padrão (removido time.tzset() para compatibilidade com Windows)
os.environ['TZ'] = 'America/Sao_Paulo'
try:
    time.tzset()  # Isso só funcionará em Unix
except AttributeError:
    pass  # Ignora em Windows, usaremos pytz para timezone

app = Flask(__name__)

# Set a secret key for session management
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or 'dev-secret-key'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://rgsclimatizacao_db_user:BTWRNA8eH6nh6M3aG33J8UZlcJFWdcLe@dpg-d0s5nu49c44c73cqcpq0-a.oregon-postgres.render.com/rgsclimatizacao_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Definir o fuso horário para o Brasil
tz = timezone('America/Sao_Paulo')

class Orcamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True)
    cliente_nome = db.Column(db.String(100))
    cliente_telefone = db.Column(db.String(20))
    cliente_email = db.Column(db.String(100))
    servico = db.Column(db.String(100))
    valor_base = db.Column(db.Float)
    desconto = db.Column(db.Float)
    valor_final = db.Column(db.Float)
    forma_pagamento = db.Column(db.String(50))
    taxa_cartao = db.Column(db.Float, default=0.0)
    taxa_maquina = db.Column(db.Float, default=0.0)
    parcelas = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='pendente')
    data_criacao = db.Column(db.DateTime, default=lambda: datetime.now(tz))
    validade_dias = db.Column(db.Integer, default=7)
    observacoes = db.Column(db.Text)
    proxima_visita = db.Column(db.Date)
    data_servico = db.Column(db.Date)
    recibo_id = db.Column(db.Integer, db.ForeignKey('recibo.id'))
    recibo = db.relationship('Recibo', backref='orcamento', uselist=False)

class Recibo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True)
    cliente_nome = db.Column(db.String(100))
    cliente_telefone = db.Column(db.String(20))
    cliente_email = db.Column(db.String(100))
    cliente_documento = db.Column(db.String(20))
    valor = db.Column(db.Float)
    valor_extenso = db.Column(db.String(200))
    forma_pagamento = db.Column(db.String(50))
    parcelas = db.Column(db.Integer, default=1)
    valor_parcela = db.Column(db.Float)
    referente = db.Column(db.String(200))
    data_emissao = db.Column(db.DateTime, default=lambda: datetime.now(tz))
    emitente_nome = db.Column(db.String(100))
    emitente_documento = db.Column(db.String(20))

def initialize_database():
    with app.app_context():
        # Verificar e adicionar colunas ausentes
        inspector = inspect(db.engine)
        columns = [column['name'] for column in inspector.get_columns('orcamento')]
        
        if 'data_servico' not in columns:
            try:
                db.session.execute(text('ALTER TABLE orcamento ADD COLUMN data_servico DATE'))
                db.session.commit()
                print("✅ Coluna 'data_servico' adicionada com sucesso!")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro ao adicionar coluna data_servico: {e}")
        
        if 'proxima_visita' not in columns:
            try:
                db.session.execute(text('ALTER TABLE orcamento ADD COLUMN proxima_visita DATE'))
                db.session.commit()
                print("✅ Coluna 'proxima_visita' adicionada com sucesso!")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro ao adicionar coluna proxima_visita: {e}")
        
        db.create_all()

initialize_database()

@app.route('/')
def index():
    return redirect(url_for('lista_orcamentos'))

@app.route('/orcamento', methods=['GET', 'POST'])
def orcamento():
    if request.method == 'POST':
        try:
            ano_atual = datetime.now(tz).year
            ultimo_orcamento = Orcamento.query.filter(
                Orcamento.numero.like(f'%-{ano_atual}')
            ).order_by(Orcamento.id.desc()).first()
            
            numero_sequencial = 1 if not ultimo_orcamento else int(ultimo_orcamento.numero.split('-')[1]) + 1
            novo_numero = f"Pedido-{numero_sequencial:04d}-{ano_atual}"

            data_servico_str = request.form.get('data_servico', '').strip()
            data_servico = None
            
            if data_servico_str:
                try:
                    data_servico = datetime.strptime(data_servico_str, '%d/%m/%Y').date()
                except ValueError:
                    flash('Data inválida. Use o formato DD/MM/AAAA (ex: 20/05/2025).', 'error')
                    return redirect(url_for('orcamento'))

            if not data_servico:
                data_servico = date.today()
                flash(f'Data não informada. Usando data atual: {data_servico.strftime("%d/%m/%Y")}', 'info')

            novo_orcamento = Orcamento(
                numero=novo_numero,
                cliente_nome=request.form.get('cliente'),
                cliente_telefone=request.form.get('telefone', ''),
                cliente_email=request.form.get('email', ''),
                servico=request.form.get('servico'),
                valor_base=float(request.form.get('valor_base', 0).replace(',', '.')),
                desconto=float(request.form.get('desconto', 0)),
                forma_pagamento=request.form.get('forma_pagamento', 'dinheiro'),
                taxa_maquina=float(request.form.get('taxa_maquina', 0)),
                parcelas=int(request.form.get('parcelas', 1)),
                observacoes=request.form.get('observacoes', ''),
                status='pendente',
                data_servico=data_servico,
                data_criacao=datetime.now(tz)
            )

            valor_com_desconto = novo_orcamento.valor_base * (1 - novo_orcamento.desconto / 100)
            valor_com_taxa = valor_com_desconto + (valor_com_desconto * novo_orcamento.taxa_maquina / 100)
            novo_orcamento.valor_final = round(valor_com_taxa, 2)

            db.session.add(novo_orcamento)
            db.session.commit()

            flash(f'Orçamento {novo_numero} criado com sucesso! Data do serviço: {data_servico.strftime("%d/%m/%Y")}', 'success')
            return redirect(url_for('lista_orcamentos'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar orçamento: {str(e)}', 'error')
            return redirect(url_for('orcamento'))

    hoje = date.today().strftime('%d/%m/%Y')
    return render_template('orcamento.html', data_hoje=hoje)

@app.route('/lista_orcamentos')
def lista_orcamentos():
    try:
        orcamentos = Orcamento.query.order_by(Orcamento.data_criacao.desc()).all()
        return render_template('lista_orcamentos.html', orcamentos=orcamentos)
    except Exception as e:
        flash(f'Erro ao carregar orçamentos: {str(e)}', 'error')
        return render_template('lista_orcamentos.html', orcamentos=[])

@app.route('/excluir_orcamento/<int:id>', methods=['POST'])
def excluir_orcamento(id):
    try:
        orcamento = Orcamento.query.get_or_404(id)
        db.session.delete(orcamento)
        db.session.commit()
        return jsonify({"status": "success", "message": "Orçamento excluído com sucesso!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/editar_orcamento/<int:id>', methods=['GET', 'POST', 'PUT'])
def editar_orcamento(id):
    orcamento = Orcamento.query.get_or_404(id)
    
    if request.method in ['POST', 'PUT']:
        try:
            orcamento.cliente_nome = request.form['cliente']
            orcamento.cliente_telefone = request.form.get('telefone', '')
            orcamento.cliente_email = request.form.get('email', '')
            orcamento.servico = request.form['servico']
            orcamento.valor_base = float(request.form.get('valor_base', 0))
            orcamento.desconto = float(request.form.get('desconto', 0))
            orcamento.forma_pagamento = request.form.get('forma_pagamento', 'dinheiro')
            orcamento.taxa_maquina = float(request.form.get('taxa_maquina', 0))
            orcamento.parcelas = int(request.form.get('parcelas', 1))
            orcamento.observacoes = request.form.get('observacoes', '')
            orcamento.status = request.form.get('status', 'pendente')

            valor_com_desconto = orcamento.valor_base * (1 - orcamento.desconto / 100)
            valor_com_taxa = valor_com_desconto + (valor_com_desconto * orcamento.taxa_maquina / 100)
            orcamento.valor_final = round(valor_com_taxa, 2)

            data_servico_str = request.form.get('data_servico')
            data_servico_anterior = orcamento.data_servico
            if data_servico_str:
                try:
                    nova_data_servico = datetime.strptime(data_servico_str, '%Y-%m-%d').date()
                    orcamento.data_servico = nova_data_servico
                    
                    if orcamento.status == 'concluido' and (data_servico_anterior != nova_data_servico or not orcamento.proxima_visita):
                        orcamento.proxima_visita = nova_data_servico + relativedelta(months=3)
                except ValueError:
                    flash('Data do serviço inválida. Mantida a data anterior.', 'warning')

            proxima_visita_str = request.form.get('proxima_visita')
            if proxima_visita_str:
                try:
                    orcamento.proxima_visita = datetime.strptime(proxima_visita_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Data de próxima visita inválida.', 'warning')
            elif orcamento.status == 'concluido' and not orcamento.proxima_visita and orcamento.data_servico:
                orcamento.proxima_visita = orcamento.data_servico + relativedelta(months=3)

            db.session.commit()
            flash('Orçamento atualizado com sucesso!', 'success')
            return redirect(url_for('lista_orcamentos'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar orçamento: {str(e)}', 'danger')
            return redirect(url_for('editar_orcamento', id=id))

    data_servico = orcamento.data_servico.strftime('%Y-%m-%d') if orcamento.data_servico else ''
    proxima_visita = orcamento.proxima_visita.strftime('%Y-%m-%d') if orcamento.proxima_visita else ''
    
    return render_template('editar_orcamento.html', 
                         orcamento=orcamento,
                         data_servico=data_servico,
                         proxima_visita=proxima_visita)

@app.route('/gerar_pdf/<int:id>')
def gerar_pdf_orcamento(id):
    try:
        orcamento = Orcamento.query.get_or_404(id)
        rendered = render_template('gerar_pdf.html', orcamento=orcamento)

        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
            'no-outline': None,
            'enable-local-file-access': None,
        }

        config = None
        wkhtmltopdf_paths = [
            r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
            r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
        ]
        for path in wkhtmltopdf_paths:
            if os.path.exists(path):
                config = pdfkit.configuration(wkhtmltopdf=path)
                break
        
        pdf = pdfkit.from_string(rendered, False, options=options, configuration=config)
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        safe_name = orcamento.cliente_nome.replace(" ", "_")
        response.headers['Content-Disposition'] = f'inline; filename={safe_name}.pdf'

        return response

    except Exception as e:
        print(f"Erro na geração do PDF: {e}")
        flash(f'Erro ao gerar PDF: {str(e)}', 'error')
        return render_template('gerar_pdf.html', orcamento=orcamento)

@app.route('/precificacao')
def precificacao():
    return render_template('precificacao.html')

@app.route('/recibo/<int:id>')
def recibo(id):
    try:
        orcamento = Orcamento.query.get_or_404(id)
        
        def valor_para_extenso(valor):
            try:
                from num2words import num2words
                return num2words(valor, lang='pt_BR', to='currency')
            except:
                inteiro = int(valor)
                centavos = int(round((valor - inteiro) * 100))
                texto = f"{inteiro} reais" if inteiro != 1 else "um real"
                if centavos > 0:
                    texto += f" e {centavos} centavos"
                return texto
        
        ano_atual = datetime.now(tz).year
        ultimo_recibo = Recibo.query.order_by(Recibo.id.desc()).first()
        numero_sequencial = 1 if not ultimo_recibo else int(ultimo_recibo.numero.split('/')[0]) + 1
        numero_recibo = f"{numero_sequencial:04d}/{ano_atual}"
        
        try:
            novo_recibo = Recibo(
                numero=numero_recibo,
                cliente_nome=orcamento.cliente_nome,
                cliente_telefone=getattr(orcamento, 'cliente_telefone', ''),
                cliente_email=getattr(orcamento, 'cliente_email', ''),
                cliente_documento='Não informado',
                valor=orcamento.valor_final,
                valor_extenso=valor_para_extenso(orcamento.valor_final),
                forma_pagamento=getattr(orcamento, 'forma_pagamento', 'À vista'),
                parcelas=getattr(orcamento, 'parcelas', 1),
                valor_parcela=orcamento.valor_final,
                referente=f"Serviço de {orcamento.servico} - Orçamento {orcamento.numero}",
                emitente_nome="RGS Climatização",
                emitente_documento="XX.XXX.XXX/0001-XX",
                data_emissao=datetime.now(tz)
            )
            
            db.session.add(novo_recibo)
            db.session.commit()
            
        except Exception as db_error:
            print(f"Erro ao salvar recibo: {db_error}")
            class ReciboTemp:
                def __init__(self):
                    self.numero = numero_recibo
                    self.cliente_nome = orcamento.cliente_nome
                    self.cliente_documento = 'Não informado'
                    self.valor = orcamento.valor_final
                    self.valor_extenso = valor_para_extenso(orcamento.valor_final)
                    self.forma_pagamento = getattr(orcamento, 'forma_pagamento', 'À vista')
                    self.parcelas = getattr(orcamento, 'parcelas', 1)
                    self.valor_parcela = orcamento.valor_final
                    self.referente = f"Serviço de {orcamento.servico}"
                    self.data_emissao = datetime.now(tz)
                    self.emitente_nome = "RGS Climatização"
            
            novo_recibo = ReciboTemp()
        
        try:
            rendered = render_template('recibo.html', recibo=novo_recibo)
            
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': 'UTF-8',
                'no-outline': None
            }
            
            config = None
            wkhtmltopdf_paths = [
                r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
                r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
            ]
            
            for path in wkhtmltopdf_paths:
                if os.path.exists(path):
                    config = pdfkit.configuration(wkhtmltopdf=path)
                    break
            
            pdf = pdfkit.from_string(rendered, False, options=options, configuration=config)
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename=recibo_{numero_recibo.replace("/", "_")}.pdf'
            return response
            
        except Exception as pdf_error:
            print(f"Erro ao gerar PDF: {pdf_error}")
            return render_template('recibo.html', recibo=novo_recibo)
    
    except Exception as e:
        flash(f'Erro ao gerar recibo: {str(e)}', 'error')
        return redirect(url_for('lista_orcamentos'))

@app.route('/atualizar_status/<int:id>', methods=['POST'])
def atualizar_status(id):
    orcamento = Orcamento.query.get_or_404(id)
    novo_status = request.json.get('status')
    
    if novo_status not in ['pendente', 'aprovado', 'rejeitado', 'em_andamento', 'concluido', 'cancelado']:
        return jsonify({'status': 'error', 'message': 'Status inválido'}), 400
    
    try:
        orcamento.status = novo_status
        
        if novo_status == 'concluido' and not orcamento.proxima_visita:
            orcamento.proxima_visita = date.today() + relativedelta(months=3)
        
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Status atualizado com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)