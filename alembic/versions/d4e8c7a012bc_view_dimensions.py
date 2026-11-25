"""SQLite에만 추가됐던 원본 시점 크기를 PostgreSQL에도 가산한다."""
from alembic import op
import sqlalchemy as sa
revision='d4e8c7a012bc'
down_revision='c3e7b6d901ab'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('inspection_views',sa.Column('width',sa.Integer(),nullable=True))
    op.add_column('inspection_views',sa.Column('height',sa.Integer(),nullable=True))

def downgrade():raise RuntimeError('원본 크기 컬럼 자동 삭제 금지')
