from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import json
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Arquivos de dados
ORCAMENTOS_FILE = 'orcamentos.json'
PRECIFICACOES_FILE = 'precificacoes.json'
CUSTOS_FIXOS_FILE = 'custos_fixos.json'
TIPOS_SERVICO_FILE = 'tipos_servico.json'

# Inicializar arquivos se não existirem
def init_files():
    default_custos_fixos = {
        "prolabore": 3000.00,
        "agua": 150.00,
        "luz": 300.00,
        "aluguel": 1200.00,
        "internet": 150.00,
        "telefone": 100.00,
        "contador": 500.00,
        "software": 200.00,
        "marketing": 300.00
    }

    default_tipos_servico = {
        "instalacao": {
            "mao_obra": 250.00,
            "tempo_medio": 4,
            "custo_km": 1.20
        },
        "manutencao": {
            "mao_obra": 180.00,
            "tempo_medio": 2,
            "custo_km": 1.00
        },
        "limpeza": {
            "mao_obra": 120.00,
            "tempo_medio": 1.5,
            "custo_km": 0.80
        }
    }

    if not os.path.exists(CUSTOS_FIXOS_FILE):
        with open(CUSTOS_FIXOS_FILE, 'w') as f:
            json.dump(default_custos_fixos, f, indent=4)

    if not os.path.exists(TIPOS_SERVICO_FILE):
        with open(TIPOS_SERVICO_FILE, 'w') as f:
            json.dump(default_tipos_servico, f, indent=4)

init_files()

# Carregar dados dos arquivos
def load_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

CUSTOS_FIXOS = load_data(CUSTOS_FIXOS_FILE)
TIPOS_SERVICO = load_data(TIPOS_SERVICO_FILE)

# Rotas para gerenciar custos fixos
@app.route('/api/custos_fixos', methods=['GET', 'POST'])
def manage_custos_fixos():
    global CUSTOS_FIXOS

    if request.method == 'GET':
        return jsonify(CUSTOS_FIXOS)

    elif request.method == 'POST':
        data = request.json
        with open(CUSTOS_FIXOS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        CUSTOS_FIXOS = data
        return jsonify({"status": "success"})

@app.route('/api/tipos_servico', methods=['GET', 'POST'])
def manage_tipos_servico():
    global TIPOS_SERVICO

    if request.method == 'GET':
        return jsonify(TIPOS_SERVICO)

    elif request.method == 'POST':
        data = request.json
        with open(TIPOS_SERVICO_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        TIPOS_SERVICO = data
        return jsonify({"status": "success"})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/orcamento', methods=['GET', 'POST'])
def orcamento():
    if request.method == 'POST':
        cliente = request.form['cliente']
        telefone = request.form.get('telefone', '')
        email = request.form.get('email', '')
        servico = request.form['servico']
        valor_base = float(request.form['valor_base'])
        taxa_cartao = float(request.form.get('taxa_cartao', 0))
        parcelas = int(request.form.get('parcelas', 1))
        observacoes = request.form.get('observacoes', '')

        valor_total = valor_base * (1 + taxa_cartao / 100) if taxa_cartao > 0 else valor_base

        novo_orcamento = {
            'cliente': cliente,
            'telefone': telefone,
            'email': email,
            'servico': servico,
            'valor_base': valor_base,
            'taxa_cartao': taxa_cartao,
            'parcelas': parcelas,
            'valor_total': valor_total,
            'observacoes': observacoes,
            'data': datetime.now().strftime('%d/%m/%Y %H:%M')
        }

        try:
            with open(ORCAMENTOS_FILE, 'r+') as f:
                try:
                    orcamentos = json.load(f)
                except json.JSONDecodeError:
                    orcamentos = []
                orcamentos.append(novo_orcamento)
                f.seek(0)
                json.dump(orcamentos, f, indent=4)
                f.truncate()
        except FileNotFoundError:
            with open(ORCAMENTOS_FILE, 'w') as f:
                json.dump([novo_orcamento], f, indent=4)

        return redirect(url_for('lista_orcamentos'))

    return render_template('orcamento.html')

@app.route('/precificacao', methods=['GET', 'POST'])
def precificacao():
    if request.method == 'POST':
        tipo_servico = request.form['tipo_servico']
        custo_materiais = float(request.form['custo_materiais'])
        horas_estimadas = float(request.form['horas_estimadas'])
        margem_lucro = float(request.form['margem_lucro'])

        custo_fixo_mensal = sum(CUSTOS_FIXOS.values())
        custo_fixo_diario = custo_fixo_mensal / 22  # Dias úteis médios no mês

        if tipo_servico in TIPOS_SERVICO:
            servico = TIPOS_SERVICO[tipo_servico]
            custo_mao_obra = servico['mao_obra'] * horas_estimadas
            custo_total = custo_materiais + custo_mao_obra + (custo_fixo_diario * (horas_estimadas / 8))
            preco_venda = custo_total * (1 + margem_lucro / 100)

            return render_template('precificacao.html',
                                calculado=True,
                                tipo_servico=tipo_servico,
                                custo_materiais=custo_materiais,
                                horas_estimadas=horas_estimadas,
                                margem_lucro=margem_lucro,
                                custo_fixo_diario=custo_fixo_diario,
                                custo_mao_obra=custo_mao_obra,
                                custo_total=custo_total,
                                preco_venda=preco_venda,
                                custos_fixos=CUSTOS_FIXOS,
                                tipos_servico=TIPOS_SERVICO)
        else:
            return render_template('precificacao.html',
                                calculado=False,
                                erro_servico="Tipo de serviço inválido.",
                                custos_fixos=CUSTOS_FIXOS,
                                tipos_servico=TIPOS_SERVICO)

    return render_template('precificacao.html',
                         calculado=False,
                         custos_fixos=CUSTOS_FIXOS,
                         tipos_servico=TIPOS_SERVICO)

@app.route('/lista_orcamentos')
def lista_orcamentos():
    try:
        with open(ORCAMENTOS_FILE, 'r') as f:
            orcamentos = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        orcamentos = []
    
    return render_template('lista_orcamentos.html', orcamentos=orcamentos)

@app.route('/excluir_orcamento/<int:index>', methods=['POST'])
def excluir_orcamento(index):
    try:
        with open(ORCAMENTOS_FILE, 'r') as f:
            orcamentos = json.load(f)

        if 0 <= index < len(orcamentos):
            orcamentos.pop(index)
            with open(ORCAMENTOS_FILE, 'w') as f:
                json.dump(orcamentos, f, indent=4)
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Índice inválido"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/editar_orcamento/<int:index>', methods=['GET', 'POST'])
def editar_orcamento(index):
    try:
        with open(ORCAMENTOS_FILE, 'r') as f:
            orcamentos = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "Orçamento não encontrado", 404

    if index < 0 or index >= len(orcamentos):
        return "Orçamento não encontrado", 404
    
    orcamento = orcamentos[index]
    
    if request.method == 'POST':
        orcamento['cliente'] = request.form.get('cliente')
        orcamento['telefone'] = request.form.get('telefone', '')
        orcamento['email'] = request.form.get('email', '')
        orcamento['servico'] = request.form.get('servico')
        orcamento['valor_base'] = float(request.form.get('valor_base'))
        orcamento['taxa_cartao'] = float(request.form.get('taxa_cartao', 0))
        orcamento['parcelas'] = int(request.form.get('parcelas', 1))
        orcamento['valor_total'] = orcamento['valor_base'] * (1 + orcamento['taxa_cartao'] / 100)
        orcamento['observacoes'] = request.form.get('observacoes', '')
        orcamento['data'] = datetime.now().strftime('%d/%m/%Y %H:%M')

        with open(ORCAMENTOS_FILE, 'w') as f:
            json.dump(orcamentos, f, indent=4)

        return redirect(url_for('lista_orcamentos'))
    
    return render_template('editar_orcamento.html', orcamento=orcamento, index=index)

@app.route('/gerar_pdf/<int:index>')
def gerar_pdf(index):
    try:
        # Lê os orçamentos do arquivo JSON
        with open(ORCAMENTOS_FILE, 'r') as f:
            orcamentos = json.load(f)

        if index < 0 or index >= len(orcamentos):
            return "Orçamento não encontrado", 404

        orcamento = orcamentos[index]

        # Geração do PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Logo aumentada
        logo_path = os.path.join(app.root_path, 'static', 'imagem', 'logo.png')
        if os.path.exists(logo_path):
            p.drawImage(logo_path, 40, height - 120, width=150, height=100, preserveAspectRatio=True, mask='auto')
        else:
            print(f"Logo não encontrada no caminho: {logo_path}")

        # Título
        p.setFont("Helvetica-Bold", 16)
        p.drawString(200, height - 80, "Orçamento de Serviço")

        # Dados do orçamento
        p.setFont("Helvetica", 12)
        y = height - 160
        espacamento = 20

        for chave, valor in orcamento.items():
            p.drawString(40, y, f"{chave.capitalize().replace('_', ' ')}: {valor}")
            y -= espacamento

        p.showPage()
        p.save()

        buffer.seek(0)

        # Nome do cliente no nome do PDF (ajuste o campo se necessário)
        nome_cliente = orcamento.get('cliente', f"cliente_{index+1}")  # <-- altere 'cliente' se precisar
        nome_arquivo = "".join(c for c in nome_cliente if c.isalnum() or c in " ._-").strip() + ".pdf"

        return send_file(buffer, as_attachment=True,
                         download_name=nome_arquivo,
                         mimetype='application/pdf')

    except Exception as e:
        return f"Erro ao gerar PDF: {str(e)}", 500


if __name__ == '__main__':
    app.run(debug=True)