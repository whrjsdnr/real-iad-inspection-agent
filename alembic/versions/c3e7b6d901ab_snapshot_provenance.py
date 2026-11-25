"""참고 기준선과 실측 지표의 출처 분리. 기존 행/테이블은 보존한다."""
from alembic import op
import sqlalchemy as sa
revision='c3e7b6d901ab'
down_revision='8e4e22a3388c'
branch_labels=None
depends_on=None

def upgrade():
    for name in ['source_scope','baseline_kind','split_reference','review_status']:
        op.add_column('metrics_snapshots',sa.Column(name,sa.String(),nullable=True))

def downgrade():
    # 자동 데이터 손실을 막기 위해 downgrade는 명시적 수동 계획이 필요하다.
    raise RuntimeError('출처 컬럼 삭제는 자동 수행하지 않습니다')
