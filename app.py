from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from flask import make_response
import pdfkit
import os

app = Flask(__name__)

# Set a secret key for session management
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or 'dev-secret-key'  # Important for sessions

# Conexão com o banco de dados PostgreSQL da Render
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://rgsclimatizacao_db_user:BTWRNA8eH6nh6M3aG33J8UZlcJFWdcLe@dpg-d0s5nu49c44c73cqcpq0-a.oregon-postgres.render.com/rgsclimatizacao_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)


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
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    validade_dias = db.Column(db.Integer, default=7)
    observacoes = db.Column(db.Text)
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
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)
    emitente_nome = db.Column(db.String(100))
    emitente_documento = db.Column(db.String(20))

# Inicializar banco de dados
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return redirect(url_for('lista_orcamentos'))

@app.route('/orcamento', methods=['GET', 'POST'])
def orcamento():
    if request.method == 'POST':
        try:
            # Criar um novo número de orçamento no formato Pedido-NNNN-AAAA
            ano_atual = datetime.now().year
            # Busca o último orçamento do ano atual
            ultimo_orcamento = Orcamento.query.filter(
                Orcamento.numero.like(f'%-{ano_atual}')
            ).order_by(Orcamento.id.desc()).first()
            
            # Se não houver orçamentos este ano, começa com 1, senão incrementa
            if ultimo_orcamento:
                # Extrai o número sequencial do último pedido
                numero_anterior = int(ultimo_orcamento.numero.split('-')[1])
                numero_sequencial = numero_anterior + 1
            else:
                numero_sequencial = 1
                
            novo_numero = f"Pedido-{numero_sequencial:04d}-{ano_atual}"

            # Criar o orçamento
            novo_orcamento = Orcamento(
                numero=novo_numero,
                cliente_nome=request.form.get('cliente'),
                cliente_telefone=request.form.get('telefone', ''),
                cliente_email=request.form.get('email', ''),
                servico=request.form.get('servico'),
                valor_base=float(request.form.get('valor_base', 0)),
                desconto=float(request.form.get('desconto', 0)),
                forma_pagamento=request.form.get('forma_pagamento', 'dinheiro'),
                taxa_maquina=float(request.form.get('taxa_maquina', 0)),
                parcelas=int(request.form.get('parcelas', 1)),
                observacoes=request.form.get('observacoes', ''),
                status='pendente'
            )

            # Calcular valor final
            valor_com_desconto = novo_orcamento.valor_base * (1 - novo_orcamento.desconto / 100)
            valor_com_taxa = valor_com_desconto + (valor_com_desconto * novo_orcamento.taxa_maquina / 100)
            novo_orcamento.valor_final = round(valor_com_taxa, 2)

            db.session.add(novo_orcamento)
            db.session.commit()

            flash(f'Orçamento {novo_numero} criado com sucesso!', 'success')
            return redirect(url_for('lista_orcamentos'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar orçamento: {str(e)}', 'error')
            return redirect(url_for('orcamento'))

    return render_template('orcamento.html')

@app.route('/lista_orcamentos')
def lista_orcamentos():
    orcamentos = Orcamento.query.order_by(Orcamento.data_criacao.desc()).all()
    return render_template('lista_orcamentos.html', orcamentos=orcamentos)

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
            orcamento.servico = request.form['servico']
            orcamento.valor_final = float(request.form['valor'])
            orcamento.status = request.form['status']
            
            db.session.commit()
            flash('Orçamento atualizado com sucesso!', 'success')
            return redirect(url_for('lista_orcamentos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar orçamento: {str(e)}', 'danger')
    
    return render_template('editar_orcamento.html', orcamento=orcamento)

# Update your gerar_pdf route
@app.route('/gerar_pdf/<int:id>', endpoint='gerar_pdf_orcamento')
def gerar_pdf(id):
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

        import os
        config = None
        wkhtmltopdf_paths = [
            r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
            r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
        ]
        for path in wkhtmltopdf_paths:
            if os.path.exists(path):
                config = pdfkit.configuration(wkhtmltopdf=path)
                print(f"wkhtmltopdf encontrado em: {path}")
                break
        
        if not config:
            print("wkhtmltopdf não encontrado! Verifique o caminho.")

        pdf = pdfkit.from_string(rendered, False, options=options, configuration=config)
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'

        # Aqui alterei para usar o nome do cliente no nome do arquivo:
        safe_name = orcamento.cliente_nome.replace(" ", "_")
        response.headers['Content-Disposition'] = f'inline; filename={safe_name}.pdf'

        return response

    except Exception as e:
        print(f"Erro na geração do PDF do orçamento: {e}")
        flash(f'Erro ao gerar PDF do orçamento: {str(e)}', 'error')
        return render_template('gerar_pdf.html', orcamento=orcamento)


@app.route('/precificacao')
def precificacao():
    return render_template('precificacao.html')

from flask import render_template

@app.route('/recibo/<int:id>')
def recibo(id):
    try:
        # Buscar o orçamento
        orcamento = Orcamento.query.get_or_404(id)
        print(f"Orçamento encontrado: {orcamento.id}")
        
        # Função para converter valor para extenso
        def valor_para_extenso(valor):
            try:
                from num2words import num2words
                return num2words(valor, lang='pt_BR', to='currency')
            except:
                # Fallback simples
                inteiro = int(valor)
                centavos = int(round((valor - inteiro) * 100))
                texto = f"{inteiro} reais" if inteiro != 1 else "um real"
                if centavos > 0:
                    texto += f" e {centavos} centavos"
                return texto
        
        # Criar dados do recibo baseado no orçamento
        from datetime import datetime
        
        # Gerar número do recibo
        ano_atual = datetime.now().year
        try:
            ultimo_recibo = Recibo.query.order_by(Recibo.id.desc()).first()
            numero_sequencial = 1 if not ultimo_recibo else int(ultimo_recibo.numero.split('/')[0]) + 1
        except:
            numero_sequencial = 1
        
        numero_recibo = f"{numero_sequencial:04d}/{ano_atual}"
        
        # Criar novo recibo
        try:
            novo_recibo = Recibo(
                numero=numero_recibo,
                cliente_nome=orcamento.cliente_nome,
                cliente_telefone=getattr(orcamento, 'cliente_telefone', ''),
                cliente_email=getattr(orcamento, 'cliente_email', ''),
                cliente_documento='Não informado',  # Pode ser passado como parâmetro depois
                valor=orcamento.valor_final,
                valor_extenso=valor_para_extenso(orcamento.valor_final),
                forma_pagamento=getattr(orcamento, 'forma_pagamento', 'À vista'),
                parcelas=getattr(orcamento, 'parcelas', 1),
                valor_parcela=orcamento.valor_final,
                referente=f"Serviço de {orcamento.servico} - Orçamento {orcamento.numero}",
                emitente_nome="RGS Climatização",
                emitente_documento="XX.XXX.XXX/0001-XX",
                data_emissao=datetime.now()
            )
            
            db.session.add(novo_recibo)
            db.session.commit()
            print(f"Recibo criado com ID: {novo_recibo.id}")
            
        except Exception as db_error:
            print(f"Erro ao salvar recibo no banco: {db_error}")
            # Se falhar ao salvar, criar objeto temporário
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
                    self.data_emissao = datetime.now()
                    self.emitente_nome = "RGS Climatização"
            
            novo_recibo = ReciboTemp()
        
        # Tentar gerar PDF
        try:
            import pdfkit
            import os
            
            # Renderizar template
            rendered = render_template('recibo.html', recibo=novo_recibo)
            print("Template renderizado com sucesso")
            
            # Configurações do PDF
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': 'UTF-8',
                'no-outline': None
            }
            
            # Configurar wkhtmltopdf
            config = None
            wkhtmltopdf_paths = [
                r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
                r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
            ]
            
            for path in wkhtmltopdf_paths:
                if os.path.exists(path):
                    config = pdfkit.configuration(wkhtmltopdf=path)
                    print(f"wkhtmltopdf encontrado em: {path}")
                    break
            
            # Gerar PDF
            pdf = pdfkit.from_string(rendered, False, options=options, configuration=config)
            print("PDF gerado com sucesso")
            
            # Retornar PDF como resposta
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename=recibo_{numero_recibo.replace("/", "_")}.pdf'
            return response
            
        except ImportError as import_error:
            print(f"Biblioteca não encontrada: {import_error}")
            flash('Para gerar PDF, instale: pip install pdfkit', 'warning')
            return render_template('recibo.html', recibo=novo_recibo)
            
        except Exception as pdf_error:
            print(f"Erro ao gerar PDF: {pdf_error}")
            flash(f'PDF não pôde ser gerado: {str(pdf_error)}. Mostrando em HTML.', 'warning')
            return render_template('recibo.html', recibo=novo_recibo)
    
    except Exception as e:
        print(f"Erro geral na função recibo: {e}")
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
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Status atualizado com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
