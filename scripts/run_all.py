#!/usr/bin/env python
"""
전체 ETL 파이프라인 실행 스크립트
1. 크롤링 (Peterpan 부동산 데이터)
2. 전처리 (검색 텍스트 생성)
3. 데이터 Import (PostgreSQL, Neo4j, Elasticsearch)
4. 가격 분류 모델 적용
"""
import os
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

def run_script(script_path, cwd=None, args=None):
    """Python 스크립트 실행"""
    print(f"\n🚀 실행 중: {script_path}")
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"❌ 실패: {script_path} (Exit code: {result.returncode})")
        return False
    return True

def main():
    base_dir = Path(__file__).parent
    start_time = datetime.now()
    
    print("\n" + "=" * 80)
    print(" " * 25 + "🚀 ETL 파이프라인 시작")
    print("=" * 80)
    print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Step 0: S3 데이터 다운로드 (선택적)
    if os.getenv('DOWNLOAD_FROM_S3', 'false').lower() == 'true':
        print("\n" + "=" * 80)
        print(" " * 20 + "📥 [Step 0/5] S3 데이터 다운로드")
        print("=" * 80)
        download_script = base_dir / "download_from_s3.py"
        if download_script.exists():
            print(f"📍 스크립트: {download_script}")
            if not run_script(download_script):
                print("❌ S3 다운로드 실패")
                sys.exit(1)
        else:
            print(f"⚠️ S3 다운로드 스크립트 없음: {download_script}")
            print("   S3 다운로드 없이 계속 진행합니다...")
    
    # # Step 1: 크롤링 (환경 변수로 건너뛰기 가능)
    # if os.getenv('SKIP_CRAWLING', 'false').lower() != 'true':
    #     print("\n" + "=" * 80)
    #     print(" " * 20 + "🕷️ [Step 1/4] 크롤링 시작")
    #     print("=" * 80)
    # crawl_script = base_dir / "01_crawling" / "peterpan" / "crawl_seoul.py"
    # if crawl_script.exists():
    #     print(f"📍 스크립트: {crawl_script}")
    #     if not run_script(crawl_script):
    #         print("⚠️ 크롤링 실패, 계속 진행합니다...")
    # else:
    #     print(f"⚠️ 크롤링 스크립트 없음: {crawl_script}")
    #     print("   기존 데이터로 계속 진행합니다...")
    
    # # Step 2: 전처리
    #     print("\n" + "=" * 80)
    #     print(" " * 20 + "🔧 [Step 2/4] 전처리 시작")
    #     print("=" * 80)
    # preprocess_script = base_dir / "02_preprocessing" / "generate_search_text_parallel.py"
    # if preprocess_script.exists():
    #     print(f"📍 스크립트: {preprocess_script}")
    #     if not run_script(preprocess_script):
    #         print("⚠️ 전처리 실패, 계속 진행합니다...")
    # else:
    #     print(f"⚠️ 전처리 스크립트 없음: {preprocess_script}")
    #     print("   전처리 없이 계속 진행합니다...")
    
    # Step 2.5: S3 업로드 (크롤링/전처리 후)
    if os.getenv('UPLOAD_TO_S3', 'false').lower() == 'true':
        print("\n" + "=" * 80)
        print(" " * 20 + "📤 [Step 2.5/5] S3 데이터 업로드")
        print("=" * 80)
        upload_script = base_dir / "upload_to_s3.py"
        if upload_script.exists():
            print(f"📍 스크립트: {upload_script}")
            if not run_script(upload_script):
                print("⚠️ S3 업로드 실패, 계속 진행합니다...")
        else:
            print(f"⚠️ S3 업로드 스크립트 없음: {upload_script}")
            print("   S3 업로드 없이 계속 진행합니다...")
    
    
    # Step 2.7: PostgreSQL 컬럼 추가 (마이그레이션)
    print("\n" + "=" * 80)
    print(" " * 18 + "🔧 [Step 2.7/5] PostgreSQL 스키마 마이그레이션")
    print("=" * 80)
    migration_script = base_dir / "03_import" / "postgres" / "add_columns.py"
    if migration_script.exists():
        print(f"📍 스크립트: {migration_script}")
        if not run_script(migration_script):
            print("⚠️ 마이그레이션 실패, 계속 진행합니다...")
    else:
        print(f"⚠️ 마이그레이션 스크립트 없음: {migration_script}")
    
    # Step 3: 데이터 Import
    print("\n" + "=" * 80)
    print(" " * 18 + "📦 [Step 3/5] 데이터 Import 시작")
    print("=" * 80)
    import_script = base_dir / "03_import" / "import_all.py"
    if not import_script.exists():
        print(f"❌ Import 스크립트를 찾을 수 없습니다: {import_script}")
        sys.exit(1)
    
    print(f"📍 스크립트: {import_script}")
    if not import_script.exists():
        print(f"❌ Import 스크립트를 찾을 수 없습니다: {import_script}")
        sys.exit(1)
    
    print(f"📍 스크립트: {import_script}")
    if not run_script(import_script):
        print("❌ 데이터 Import 실패")
        sys.exit(1)
    
    # Step 4: 가격 분류 모델 적용
    print("\n" + "=" * 80)
    print(" " * 15 + "🤖 [Step 4/4] 가격 분류 모델 적용 시작")
    print("=" * 80)
    analysis_script = base_dir / "03_import" / "price_model" / "apply_price_classification.py"
    if not analysis_script.exists():
        print(f"⚠️ 분석 스크립트 없음: {analysis_script}")
        print("   분석 없이 파이프라인을 완료합니다...")
    else:
        print(f"📍 스크립트: {analysis_script}")
        if not run_script(analysis_script):
            print("⚠️ 가격 분류 실패, 파이프라인은 완료합니다...")
    
    # 완료
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "=" * 80)
    print("✅ ETL 파이프라인 완료!")
    print("=" * 80)
    print(f"종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 소요 시간: {duration}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
