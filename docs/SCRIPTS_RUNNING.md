# Scripts 디렉토리

로컬 ETL 데이터 파이프라인 스크립트 모음

## 📁 폴더 구조

```
scripts/
├── run_all.py              # 🚀 전체 파이프라인 실행 (로컬 전용)
│
├── 01_crawling/            # 데이터 수집
│   └── peterpan/           # 피터팬 매물 크롤러
│       └── crawl_seoul.py
│
├── 02_preprocessing/       # 데이터 전처리
│   └── generate_search_text_parallel.py  # ES search_text 생성 (OpenAI)
│
└── 03_import/              # DB 임포트 및 모델 적용
    ├── import_all.py       # 통합 Import 스크립트
    ├── config.py           # 환경 변수 설정
    ├── db_health_check.py  # DB 연결 확인
    │
    ├── neo4j/              # Neo4j 그래프 데이터
    │   └── import_neo4j_only.py
    │
    ├── postgres/           # PostgreSQL 관계형 데이터
    │   └── import_postgres_only.py
    │
    ├── elasticsearch/      # Elasticsearch 검색 인덱스
    │   └── es817_property_importer.py
    │
    ├── trust/              # 중개사 신뢰도 등급 모델
    │   └── import_trust_all.py
    │
    └── price_model/        # 실거래가 분류 모델
        └── apply_price_classification.py
```

---

## 🚀 빠른 시작

### 전체 파이프라인 실행 (권장)

```bash
# 로컬 실행 (localhost DB 연결)
cd scripts
python run_all.py
```

**파이프라인 단계:**
1. 크롤링 (Peterpan 부동산)
2. 전처리 (OpenAI API)
3. 데이터 Import (Neo4j, PostgreSQL, Elasticsearch)
4. 중개사 신뢰도 등급 적용
5. 실거래가 분류 모델 적용

### 선택적 실행

```bash
# 크롤링 건너뛰기 (기존 데이터 사용)
python run_all.py --skip-crawling

# 전처리 건너뛰기
python run_all.py --skip-preprocessing

# 둘 다 건너뛰기
python run_all.py --skip-crawling --skip-preprocessing
```

---

## 📦 개별 단계 실행

### 1. 크롤링

```bash
cd 01_crawling/peterpan
python crawl_seoul.py
```

### 2. 전처리

```bash
cd 02_preprocessing
python generate_search_text_parallel.py
```

### 3. DB Import (전체)

```bash
cd 03_import
python import_all.py
```

### 4. DB Import (개별)

```bash
# Neo4j만
python import_all.py --only neo4j

# PostgreSQL만
python import_all.py --only postgres

# Elasticsearch만
python import_all.py --only es

# 중개사 신뢰도 등급만
python import_all.py --only trust

# 실거래가 분류 모델만
python import_all.py --only price
```

### 5. DB 연결 확인 건너뛰기

```bash
python import_all.py --skip-health-check
```

---

## 🐳 Docker 실행

### 전체 파이프라인

```bash
# 크롤링부터 전체 Import까지
docker compose --profile scripts run --rm scripts python run_all.py

# Neo4j, PostgreSQL, Elasticsearch, Trust 모델, Price 모델
docker compose --profile scripts run --rm scripts python 03_import/import_all.py
```

### 개별 Import

```bash
# Neo4j만
docker compose --profile scripts run --rm scripts python 03_import/import_all.py --only neo4j

# PostgreSQL만
docker compose --profile scripts run --rm scripts python 03_import/import_all.py --only postgres

# Elasticsearch만
docker compose --profile scripts run --rm scripts python 03_import/import_all.py --only es

# Trust 모델만
docker compose --profile scripts run --rm scripts python 03_import/import_all.py --only trust

# Price 모델만
docker compose --profile scripts run --rm scripts python 03_import/import_all.py --only price
```

---

## 📊 데이터 흐름

```
크롤링 (crawl_seoul.py)
    ↓
data/properties_*.json
    ↓
전처리 (generate_search_text_parallel.py)
    ↓
data/properties_*_with_search_text.json
    ↓
┌─────────────────────────────────────┐
│     Import (import_all.py)          │
├─────────────────────────────────────┤
│  1. Neo4j (그래프 관계)              │
│  2. PostgreSQL (관계형 데이터)       │
│  3. Elasticsearch (검색 인덱스)      │
│  4. Trust Model (중개사 신뢰도)      │
│  5. Price Model (가격 분류)          │
└─────────────────────────────────────┘
    ↓
Backend API (Django)
Frontend (Next.js)
```
---