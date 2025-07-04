"""Adicionando coluna email à tabela cliente

Revision ID: 1fcafdc683bf
Revises: 6d595cda567f
Create Date: 2025-06-02 18:08:36.224578

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1fcafdc683bf'
down_revision = '6d595cda567f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('cliente_manutencao')
    with op.batch_alter_table('cliente', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('endereco', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('status_manutencao', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('proxima_manutencao', sa.DateTime(), nullable=True))
        batch_op.alter_column('nome',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
        batch_op.drop_column('created_at')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('cliente', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=True))
        batch_op.alter_column('nome',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
        batch_op.drop_column('proxima_manutencao')
        batch_op.drop_column('status_manutencao')
        batch_op.drop_column('endereco')
        batch_op.drop_column('email')

    op.create_table('cliente_manutencao',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('nome', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('servico', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('ultimo_orcamento', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('ultimo_valor', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('data_ultimo_servico', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('observacoes', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('proxima_manutencao', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='cliente_manutencao_pkey')
    )
    # ### end Alembic commands ###
