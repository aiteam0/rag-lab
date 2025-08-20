# 🐳 Docker PostgreSQL 가이드 (Multimodal RAG)

> 💡 **초보자를 위한 안내**: 이 가이드는 Docker를 처음 사용하는 분들도 쉽게 따라할 수 있도록 작성되었습니다.

## 목차
1. [Docker란?](#docker란)
2. [사전 요구사항](#사전-요구사항)
3. [빠른 시작 가이드](#빠른-시작-가이드)
4. [상세 설치 과정](#상세-설치-과정)
5. [데이터베이스 설정](#데이터베이스-설정)
6. [일상적인 사용법](#일상적인-사용법)
7. [트러블슈팅](#트러블슈팅)
8. [자주 묻는 질문](#자주-묻는-질문)

---

## 🤔 Docker란?

Docker는 애플리케이션을 **컨테이너**라는 격리된 환경에서 실행하는 도구입니다.

### 왜 Docker를 사용하나요?
- ✅ **설치 간편**: PostgreSQL과 pgvector를 한 번에 설치
- ✅ **환경 독립**: 시스템에 직접 설치하지 않음
- ✅ **쉬운 제거**: 컨테이너 삭제만으로 깔끔하게 정리
- ✅ **일관성**: 모든 개발자가 동일한 환경 사용

### 핵심 개념
- **이미지(Image)**: 설치 패키지 같은 것 (예: PostgreSQL + pgvector)
- **컨테이너(Container)**: 실행 중인 프로그램
- **볼륨(Volume)**: 데이터 저장 공간
- **포트(Port)**: 프로그램 접속 통로

---

## 📋 사전 요구사항

### 1. Docker 설치 확인
```bash
# Docker 버전 확인
docker --version

# Docker Compose 버전 확인
docker-compose --version
```

### 2. Docker가 없다면 설치

#### Windows (WSL2 사용 중)
1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) 다운로드
2. 설치 후 WSL2 백엔드 활성화
3. Docker Desktop 실행

#### Ubuntu/Debian
```bash
# Docker 설치
sudo apt update
sudo apt install docker.io docker-compose

# 사용자를 docker 그룹에 추가 (sudo 없이 사용)
sudo usermod -aG docker $USER

# 로그아웃 후 다시 로그인
```

#### Mac
1. [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) 다운로드
2. 설치 후 실행

### 3. 로컬 PostgreSQL 확인
```bash
# PostgreSQL이 실행 중인지 확인
sudo service postgresql status

# 실행 중이면 중지 (포트 충돌 방지)
sudo service postgresql stop
```

---

## 🚀 빠른 시작 가이드

### 3단계로 끝내기

```bash
# 1. Docker 폴더로 이동
cd /mnt/e/MyProject2/multimodal-rag-wsl-v2/docker

# 2. Docker 컨테이너 시작
docker-compose up -d

# 3. 테이블 생성
cd ..
uv run scripts/1_phase1_setup_database.py
```

완료! 이제 PostgreSQL이 Docker에서 실행 중입니다.

---

## 📖 상세 설치 과정

### Step 1: 프로젝트 구조 확인
```
multimodal-rag-wsl-v2/
├── docker/
│   ├── docker-compose.yml    # Docker 설정 파일
│   ├── init-db.sql           # 초기화 스크립트
│   └── postgres-data/        # 데이터 저장 폴더 (자동 생성)
├── .env                      # 환경 설정 (수정 불필요!)
└── scripts/                  # 데이터베이스 관리 스크립트
```

### Step 2: 환경 변수 확인 (.env)
```bash
# .env 파일 확인
cat .env | grep DB_

# 다음과 같아야 함:
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=multimodal_rag
# DB_USER=multimodal_user
# DB_PASSWORD=multimodal_pass123
```

> ⚠️ **중요**: DB_HOST는 반드시 `localhost`여야 합니다!

### Step 3: Docker 컨테이너 시작
```bash
cd docker

# 백그라운드에서 시작 (-d 옵션)
docker-compose up -d

# 실행 확인
docker ps

# 출력 예시:
# CONTAINER ID   IMAGE                      STATUS      PORTS
# abc123...      pgvector/pgvector:pg16    Up 1 min    0.0.0.0:5432->5432/tcp
```

### Step 4: 컨테이너 상태 확인
```bash
# 로그 확인 (에러가 없는지 확인)
docker-compose logs postgres-rag

# 정상 로그 예시:
# postgres-rag | PostgreSQL init process complete; ready for start up.
# postgres-rag | LOG: database system is ready to accept connections
```

### Step 5: 연결 테스트
```bash
# 프로젝트 루트로 이동
cd ..

# 연결 테스트
uv run scripts/test_phase1_db_connection.py

# 성공 메시지:
# ✅ Connected successfully!
# ✅ Table exists!
```

---

## 🔧 데이터베이스 설정

### 1. 테이블 생성 (첫 실행 시)
```bash
# 테이블과 인덱스 생성
uv run scripts/1_phase1_setup_database.py

# 옵션 선택:
# 1. Setup database (create tables and indexes) <- 이것 선택
# 2. Test connection only
# 3. Exit
```

### 2. 데이터 입력
```bash
# 문서 데이터 입력
uv run scripts/2_phase1_ingest_documents.py

# 옵션:
# 1. Full ingestion         <- 전체 데이터
# 2. Test ingestion         <- 테스트 (5개만)
```

### 3. 테스트 실행
```bash
# Phase 1 전체 테스트
uv run scripts/test_phase1.py
```

---

## 💻 일상적인 사용법

### 시작하기
```bash
# Docker 컨테이너 시작
cd docker && docker-compose up -d

# 상태 확인
docker ps
```

### 중지하기
```bash
# 컨테이너 중지 (데이터 유지)
cd docker && docker-compose stop

# 또는 down (데이터 유지)
docker-compose down
```

### 데이터베이스 접속
```bash
# psql로 직접 접속
docker exec -it multimodal-rag-postgres psql -U multimodal_user multimodal_rag

# SQL 명령어 예시
\dt                  # 테이블 목록
\d mvp_ddu_documents # 테이블 구조
SELECT COUNT(*) FROM mvp_ddu_documents; # 문서 개수
\q                   # 종료
```

### 로그 보기
```bash
# 실시간 로그 보기
docker-compose logs -f postgres-rag

# 최근 100줄만 보기
docker-compose logs --tail=100 postgres-rag
```

### 데이터 백업
```bash
# 백업 생성
docker exec multimodal-rag-postgres pg_dump -U multimodal_user multimodal_rag > backup_$(date +%Y%m%d).sql

# 백업 복원
docker exec -i multimodal-rag-postgres psql -U multimodal_user multimodal_rag < backup_20241214.sql
```

---

## 🔨 트러블슈팅

### 문제 1: 포트 충돌
```
Error: bind: address already in use
```

**해결방법:**
```bash
# 5432 포트 사용 중인 프로세스 확인
sudo lsof -i :5432

# 로컬 PostgreSQL 중지
sudo service postgresql stop

# 또는 Docker 포트 변경 (docker-compose.yml)
ports:
  - "5433:5432"  # 호스트 5433 -> 컨테이너 5432
```

### 문제 2: 권한 오류
```
Error: permission denied for schema public
```

**해결방법:**
```bash
# 컨테이너 재시작
docker-compose restart

# init-db.sql이 실행되었는지 확인
docker-compose logs postgres-rag | grep "pgvector extension"
```

### 문제 3: 연결 실패
```
Error: could not connect to server
```

**해결방법:**
```bash
# 1. 컨테이너 실행 중인지 확인
docker ps

# 2. 컨테이너 시작
cd docker && docker-compose up -d

# 3. 방화벽 확인 (Windows)
# Windows Defender 방화벽에서 Docker Desktop 허용
```

### 문제 4: 디스크 공간 부족
```
Error: could not extend file
```

**해결방법:**
```bash
# Docker 이미지/컨테이너 정리
docker system prune -a

# 오래된 볼륨 정리
docker volume prune
```

### 문제 5: 느린 성능
**해결방법:**
```bash
# Docker Desktop 메모리 할당 증가 (Settings > Resources)
# 권장: 최소 2GB, 이상적으로 4GB

# WSL2 메모리 설정 (.wslconfig)
[wsl2]
memory=4GB
processors=2
```

---

## ❓ 자주 묻는 질문

### Q1: Docker와 로컬 PostgreSQL을 동시에 사용할 수 있나요?
**A:** 아니요. 둘 다 5432 포트를 사용하므로 하나만 실행해야 합니다.

### Q2: 데이터는 어디에 저장되나요?
**A:** `docker/postgres-data/` 폴더에 저장됩니다. Docker를 삭제해도 이 폴더는 유지됩니다.

### Q3: Docker 컨테이너를 완전히 제거하려면?
```bash
# 컨테이너와 네트워크 제거 (데이터는 유지)
docker-compose down

# 데이터까지 완전 삭제
docker-compose down -v
rm -rf docker/postgres-data/
```

### Q4: 로컬과 Docker 간 전환하려면?
```bash
# Docker -> 로컬
cd docker && docker-compose down
sudo service postgresql start

# 로컬 -> Docker
sudo service postgresql stop
cd docker && docker-compose up -d
```

### Q5: pgvector 버전을 확인하려면?
```bash
docker exec multimodal-rag-postgres psql -U multimodal_user multimodal_rag -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
```

### Q6: 메모리 사용량이 너무 높아요
Docker Desktop 설정에서 리소스 제한을 조정하거나, docker-compose.yml의 `deploy.resources.limits.memory`를 수정하세요.

### Q7: Windows에서 docker-compose 명령이 안 돼요
Docker Desktop이 실행 중인지 확인하고, WSL2 터미널에서 실행하세요.

### Q8: 다른 프로젝트와 충돌하지 않나요?
컨테이너 이름(`multimodal-rag-postgres`)과 네트워크(`multimodal-rag-network`)가 고유하므로 충돌하지 않습니다.

---

## 📌 유용한 명령어 모음

```bash
# === 시작/중지 ===
cd docker && docker-compose up -d    # 시작
cd docker && docker-compose stop     # 중지
cd docker && docker-compose restart  # 재시작

# === 상태 확인 ===
docker ps                            # 실행 중인 컨테이너
docker-compose logs -f              # 실시간 로그
docker stats multimodal-rag-postgres # 리소스 사용량

# === 데이터베이스 ===
docker exec -it multimodal-rag-postgres psql -U multimodal_user multimodal_rag  # DB 접속
docker exec multimodal-rag-postgres pg_dump -U multimodal_user multimodal_rag > backup.sql  # 백업

# === 정리 ===
docker-compose down                 # 컨테이너 제거
docker system prune -a              # 미사용 리소스 정리
```

---

## 🎯 다음 단계

Docker PostgreSQL이 준비되었다면:

1. **테이블 생성**: `uv run scripts/1_phase1_setup_database.py`
2. **데이터 입력**: `uv run scripts/2_phase1_ingest_documents.py`
3. **워크플로우 테스트**: `uv run scripts/3_phase2_test_workflow.py`

---

## 📞 도움이 필요하면

- GitHub Issues에 문제를 등록하세요
- 로그 파일을 첨부하면 더 빠른 해결이 가능합니다
- `docker-compose logs > error.log` 명령으로 로그 저장

---

*이 가이드가 도움이 되었다면 ⭐ 스타를 눌러주세요!*