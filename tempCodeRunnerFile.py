@app.route('/manutencao_preventiva', methods=['GET', 'POST'])
def manutencao_preventiva():
    pagina = request.args.get('pagina', 1, type=int)
    itens_por_pagina = 10
    
    filtro_cliente = request.form.get('cliente', request.args.get('cliente', ''))
    filtro_status = request.form.get('status', request.args.get('status', ''))
    filtro_data = request.form.get('data', request.args.get('data', ''))
    
    if request.method == 'POST':
        return redirect(url_for('manutencao_preventiva',
                            cliente=filtro_cliente,
                            status=filtro_status,
                            data=filtro_data,
                            pagina=1))
    
    # Query for the list of clients (not a single client)
    query = db.session.query(
        Cliente.id,
        Cliente.nome,
        Cliente.telefone,
        Cliente.email,
        Cliente.endereco,
        Cliente.status_manutencao,
        Cliente.proxima_manutencao
    )
    
    if filtro_cliente:
        query = query.filter(Cliente.nome.ilike(f'%{filtro_cliente}%'))
    
    if filtro_status:
        query = query.filter(Cliente.status_manutencao == filtro_status)
    
    if filtro_data:
        try:
            data_filtro = datetime.strptime(filtro_data, '%Y-%m')
            query = query.filter(
                db.extract('year', Cliente.proxima_manutencao) == data_filtro.year,
                db.extract('month', Cliente.proxima_manutencao) == data_filtro.month
            )
        except ValueError:
            pass
    
    clientes_orcamentos = db.session.query(Orcamento.cliente_nome).distinct().all()
    clientes_dos_orcamentos = [cliente[0] for cliente in clientes_orcamentos]
    
    clientes_paginados = query.paginate(page=pagina, per_page=itens_por_pagina, error_out=False)
    
    return render_template('manutencao_preventiva.html', 
                        clientes=clientes_paginados.items,
                        clientes_dos_orcamentos=clientes_dos_orcamentos,
                        pagina=pagina,
                        total_paginas=clientes_paginados.pages,
                        filtro_cliente=filtro_cliente,
                        filtro_status=filtro_status,
                        filtro_data=filtro_data)