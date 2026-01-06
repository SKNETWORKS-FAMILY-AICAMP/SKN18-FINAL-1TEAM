# 인프라 먼저 (빌드 없음)
docker compose up -d postgres neo4j redis elasticsearch
# 각 서비스 개별 빌드
docker compose build backend
docker compose build rag
docker compose build reco
docker compose build frontend
docker compose build scripts

# 전체 시작
docker compose up -d
### 환경 변수 설정

```bash
# 1. 환경 변수 파일 생성
cp .env.example .env

# 2. .env 파일 편집 후 필수 값 입력:
#    - POSTGRES_PASSWORD (필수)
#    - NEO4J_PASSWORD (필수)
#    - OPENAI_API_KEY (필수 - RAG 기능)
#    - NEXTAUTH_SECRET (필수 - 아래 명령으로 생성)
#    - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET (선택 - 구글 로그인)
#    - NEXT_PUBLIC_KAKAO_MAP_KEY (선택 - 카카오맵)

# NEXTAUTH_SECRET 생성 (PowerShell)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 🚀 빠른 시작

```bash
# 1. 서비스 시작 (첫 실행 시 이미지 자동 빌드)
docker compose up -d

# 2. 서비스 상태 확인 (모든 서비스가 healthy가 될 때까지 대기)
docker compose ps

# 3. Django 마이그레이션
docker compose exec backend python manage.py migrate

# 4. 데이터 Import (30분~1시간 소요)
docker compose --profile scripts run --rm scripts python 03_import/import_all.py

# 5. Trust Score Import (30분~1시간 소요)
docker compose --profile scripts run --rm scripts python 03_import/trust/import_trust_all.py

# 6. 완료! 브라우저에서 http://localhost:3000 접속
```

---

## 🐳 Docker 명령어 상세

### 기본 명령어

| 명령어 | 설명 |
|--------|------|
| `docker compose up -d` | 모든 서비스 백그라운드 실행 |
| `docker compose up` | 포그라운드 실행 (로그 확인 가능) |
| `docker compose down` | 서비스 중지 + 컨테이너 삭제 |
| `docker compose stop` | 서비스 중지만 (컨테이너 유지) |
| `docker compose ps` | 서비스 상태 확인 |
| `docker compose logs -f` | 전체 로그 실시간 확인 |
| `docker compose logs -f backend` | 특정 서비스 로그만 확인 |

### 이미지 빌드

```bash
# 이미지 빌드 (코드 변경 후)
docker compose build

# 특정 서비스만 빌드
docker compose build backend rag

# 캐시 무시하고 처음부터 빌드
docker compose build --no-cache

# 빌드 후 바로 실행
docker compose up -d --build
```

### ⚠️ 완전 초기화 (기존 데이터 모두 삭제)

```bash
# 1. 모든 컨테이너 + 볼륨 + 네트워크 삭제
docker compose down -v --remove-orphans

# 2. 이미지 삭제 (선택)
docker compose down --rmi all

# 3. 캐시 삭제 후 새로 빌드
docker compose build --no-cache

# 4. 서비스 시작
docker compose up -d
```

### Profile 기반 서비스

```bash
# Kibana (Elasticsearch 대시보드)
docker compose --profile dashboards up -d

# Jupyter Notebook (Analytics)
docker compose --profile analytics up -d

# 스크립트 실행 (데이터 Import 등)
docker compose --profile scripts run --rm scripts python 03_import/<스크립트명>

# 크롤링
docker compose --profile crawling run --rm crawling python <스크립트명>
```

---

## 💾 데이터베이스 초기화

### 1️⃣ Django 마이그레이션 (PostgreSQL 테이블 생성)

```bash
docker compose exec backend python manage.py migrate
```

### 2️⃣ PostgreSQL 데이터 Import

```bash
# PostgreSQL 매물 데이터 Import
docker compose --profile scripts run --rm scripts python 03_import/postgres/import_postgres_only.py
```

### 3️⃣ Neo4j 데이터 Import (노드 + 엣지 생성)

```bash
# Neo4j 전체 데이터 Import (노드 + 관계)
docker compose --profile scripts run --rm scripts python 03_import/neo4j/import_neo4j_only.py

# 중개사 데이터 재Import
docker compose --profile scripts run --rm scripts python 03_import/reimport_brokers.py
```

### 4️⃣ Elasticsearch 인덱싱 + 임베딩

```bash
# Elasticsearch 매물 인덱싱 (검색 기능)
docker compose --profile scripts run --rm scripts python 03_import/elasticsearch/import_es_index.py --recreate

# 벡터 임베딩 생성 (RAG 기능)
docker compose --profile scripts run --rm scripts python 03_import/elasticsearch/import_es_embeddings.py
```

### 5️⃣ 전체 데이터 Import (권장)

```bash
# 모든 데이터베이스 한번에 Import
docker compose --profile scripts run --rm scripts python 03_import/import_all.py
```

```

---

## 🤖 ML 모델 실행 가이드

### 1️⃣ 중개사 신뢰도 모델 (Trust Model)

```bash
# Step 1: 데이터 전처리 (data/brokerinfo 폴더에 CSV 생성)
docker compose run --rm reco python models/trust_model/data_preprocessing/run_all_preprocessing.py

# Step 2: 모델 학습 (data/ML/trust/ CSV 및 model/*.pkl 생성)
docker compose run --rm reco python models/trust_model/run_all.py

# Step 3: 중개사 기본정보 Import
docker compose --profile scripts run --rm scripts python 03_import/reimport_brokers.py

# Step 4: 중개사 통계정보 Update
docker compose --profile scripts run --rm scripts python 03_import/update_broker_stats.py

# Step 5: Trust Score 예측 및 DB 저장
docker compose --profile scripts run --rm scripts python 04_analysis/trust_prediction/predict_trust_scores.py
```

### 2️⃣ 실거래가 분류 모델 (Price Model)

> 📁 경로: `apps/reco/models/price_model/ML/src`

```bash
# Step 1: 데이터 전처리 (train/test/모델용.csv 생성)
docker compose run --rm reco python models/price_model/ML/src/prepare_wolse_dataset.py

# Step 2: 모델 학습 (~5분 소요, pkl 파일 생성)
docker compose run --rm reco python models/price_model/ML/src/main.py

# Step 3: SHAP 분석 (shap_plots 폴더에 이미지 생성)
docker compose run --rm reco python models/price_model/ML/src/example_shap.py

# Step 4: 매물에 적용 후 3중 분류 결과 DB 저장
# ⚠️ 사전 준비: data/RDB/land 폴더에 JSON 파일 필요
docker compose run --rm reco python models/price_model/ML/src/apply_model_to_json.py
```

### 3️⃣ 전체 실행 순서 (처음 설정 시)

```bash
# 1. 인프라 실행
docker compose up -d

# 2. Django 마이그레이션
docker compose exec backend python manage.py migrate

# 3. 데이터 Import
docker compose --profile scripts run --rm scripts python 03_import/import_all.py

# 4. Trust Model 실행 (Step 1~5)
# 5. Price Model 실행 (Step 1~4)

# 6. 서비스 확인
# http://localhost:3000 접속
```

---

## 🌐 접속 주소

| 서비스 | URL | 설명 |
|--------|-----|------|
| **Frontend** | http://localhost:3000 | 메인 웹사이트 |
| **Backend API** | http://localhost:8000 | Django REST API |
| **RAG/Chatbot** | http://localhost:8001 | AI 챗봇 서비스 |
| **Recommendation** | http://localhost:8002 | 추천 서비스 |
| **Neo4j Browser** | http://localhost:7474 | Neo4j 그래프 DB 관리 |
| **Kibana** | http://localhost:5601 | Elasticsearch 대시보드 |
| **Jupyter** | http://localhost:8888 | 데이터 분석 노트북 |
