-- 그룹 역할만 생성한다. 로그인 비밀번호는 관리자가 별도로 발급한다.
DO $$ BEGIN
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='app_read') THEN CREATE ROLE app_read NOLOGIN; END IF;
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='app_review') THEN CREATE ROLE app_review NOLOGIN; END IF;
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='app_workflow') THEN CREATE ROLE app_workflow NOLOGIN; END IF;
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='app_batch') THEN CREATE ROLE app_batch NOLOGIN; END IF;
END $$;
GRANT USAGE ON SCHEMA public TO app_read, app_review, app_workflow, app_batch;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_read, app_review, app_workflow, app_batch;
GRANT INSERT, UPDATE ON reviews TO app_review;
-- 검수 API 트랜잭션은 finding·사용자·검사 상태를 함께 갱신하므로 별도 서비스 역할을 쓴다.
GRANT INSERT, UPDATE ON reviews,findings,users,inspection_attempts TO app_workflow;
GRANT INSERT ON metrics_snapshots TO app_workflow;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO app_workflow;

GRANT INSERT,UPDATE ON inspection_attempts,inspection_views,findings TO app_batch;
