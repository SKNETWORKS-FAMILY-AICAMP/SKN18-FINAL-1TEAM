#!/usr/bin/env python
"""
전체 ETL 파이프라인 실행 스크립트
1. 크롤링 (Peterpan 부동산)
2. 전처리 (OpenAI API)
3. S3 업로드
4. 데이터 Import (Neo4j, PostgreSQL, Elasticsearch)
5. 중개사 신뢰도 등급 적용
6. 실거래가 분류 모델 적용
"""
import os
import sys
import subprocess
from pathlib import Path

def run_script(script_path, cwd=None):
    print(f"\n🚀 실행 중: {script_path}")
    result = subprocess.run([sys.executable, str(script_path)], cwd=cwd)
    if result.returncode != 0:
        print(f"❌ 실패: {script_path} (Exit code: {result.returncode})")
        return False
    return True

def main():
    base_dir = Path(__file__).parent
    
    print("\n" + "=" * 80)
    print(" " * 25 + "🚀 전체 ETL 파이프라인 시작")
    print("=" * 80)
    
    # Step 1: 크롤링 (선택적 - 환경변수로 제어)
    skip_crawling = os.getenv("SKIP_CRAWLING", "false").lower() == "true"
    if not skip_crawling:
        print("\n" + "=" * 80)
        print(" " * 20 + "�️ [Step 1/6] 크롤링 시작")
        print("=" * 80)
        crawl_script = base_dir / "01_crawling" / "peterpan" / "crawl_seoul.py"
        if crawl_script.exists():
            print(f"📍 스크립트: {crawl_script}")
            if not run_script(crawl_script):
                sys.exit(1)
        else:
            print(f"⚠️ 크롤링 스크립트를 찾을 수 없습니다: {crawl_script}")
            print("   크롤링 없이 계속 진행합니다...")
    else:
        print("\n⏭ 크롤링 건너뛰기 (SKIP_CRAWLING=true)")
    
    # Step 2: 전처리 (선택적 - 환경변수로 제어)
    skip_preprocessing = os.getenv("SKIP_PREPROCESSING", "false").lower() == "true"
    if not skip_preprocessing:
        print("\n" + "=" * 80)
        print(" " * 20 + "🔧 [Step 2/6] 전처리 시작")
        print("=" * 80)
        preprocess_script = base_dir / "02_preprocessing" / "generate_search_text_parallel.py"
        if preprocess_script.exists():
            print(f"📍 스크립트: {preprocess_script}")
            if not run_script(preprocess_script):
                sys.exit(1)
        else:
            print(f"⚠️ 전처리 스크립트를 찾을 수 없습니다: {preprocess_script}")
            print("   전처리 없이 계속 진행합니다...")
    else:
        print("\n⏭ 전처리 건너뛰기 (SKIP_PREPROCESSING=true)")
    
    # Step 3: S3 업로드 (선택적 - 환경변수로 제어)
    upload_to_s3 = os.getenv("UPLOAD_TO_S3", "false").lower() == "true"
    if upload_to_s3:
        print("\n" + "=" * 80)
        print(" " * 20 + "📤 [Step 3/6] S3 업로드 시작")
        print("=" * 80)
        upload_script = base_dir / "upload_to_s3.py"
        if upload_script.exists():
            print(f"📍 스크립트: {upload_script}")
            if not run_script(upload_script):
                print("⚠️ S3 업로드 실패, 계속 진행합니다...")
        else:
            print(f"⚠️ S3 업로드 스크립트를 찾을 수 없습니다: {upload_script}")
    else:
        print("\n⏭ S3 업로드 건너뛰기 (UPLOAD_TO_S3=false)")
    
    # Step 4: 데이터 Import (Neo4j, PostgreSQL, Elasticsearch, Trust, Price)
    print("\n" + "=" * 80)
    print(" " * 15 + "📦 [Step 4/6] 데이터 Import 시작")
    print("=" * 80)
    import_script = base_dir / "03_import" / "import_all.py"
    if not import_script.exists():
        print(f"❌ Import 스크립트를 찾을 수 없습니다: {import_script}")
        sys.exit(1)
    
    print(f"📍 스크립트: {import_script}")
    if not run_script(import_script):
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✅ 전체 ETL 파이프라인이 성공적으로 완료되었습니다!")
    print("=" * 80)

if __name__ == "__main__":
    main()
