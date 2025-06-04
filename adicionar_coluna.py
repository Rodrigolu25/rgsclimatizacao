from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://rgsclimatizacao_db_user:BTWRNA8eH6nh6M3aG33J8UZlcJFWdcLe@dpg-d0s5nu49c44c73cqcpq0-a.oregon-postgres.render.com/rgsclimatizacao_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

with app.app_context():
    try:
        db.engine.execute(text("ALTER TABLE orcamento ADD COLUMN proxima_visita DATE"))
        print("✅ Coluna adicionada com sucesso!")
    except Exception as e:
        print(f"Erro (pode já existir): {e}")