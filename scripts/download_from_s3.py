#!/usr/bin/env python
"""
S3에서 최신 크롤링 데이터 다운로드

환경 변수:
- S3_BUCKET: S3 버킷 이름 (기본값: realestate-etl-data)
- S3_PREFIX: S3 프리픽스 (기본값: data/)
- AWS_REGION: AWS 리전 (기본값: ap-northeast-2)
"""
import os
import sys
import boto3
from pathlib import Path
from datetime import datetime

# 설정
S3_BUCKET = os.getenv('S3_BUCKET', 'realestate-etl-data')
S3_PREFIX = os.getenv('S3_PREFIX', 'data/')
AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')
LOCAL_DATA_DIR = Path('/data')

def download_from_s3():
    """S3에서 데이터 다운로드"""
    print("\n" + "=" * 70)
    print(" " * 20 + "📥 S3 데이터 다운로드")
    print("=" * 70)
    print(f"S3 버킷: s3://{S3_BUCKET}/{S3_PREFIX}")
    print(f"로컬 경로: {LOCAL_DATA_DIR}")
    print("=" * 70)
    
    try:
        # S3 클라이언트 생성
        s3 = boto3.client('s3', region_name=AWS_REGION)
        
        # 로컬 디렉토리 생성
        LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # S3 객체 목록 조회
        print("\n📋 S3 객체 목록 조회 중...")
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
        
        downloaded_count = 0
        total_size = 0
        
        for page in pages:
            if 'Contents' not in page:
                print("⚠️ S3에 파일이 없습니다.")
                continue
                
            for obj in page['Contents']:
                s3_key = obj['Key']
                
                # 디렉토리는 건너뛰기
                if s3_key.endswith('/'):
                    continue
                
                # 로컬 파일 경로 (S3_PREFIX 제거)
                # S3: "data/GraphDB_data/subway_station/file.csv"
                # → Local: "/data/GraphDB_data/subway_station/file.csv"
                relative_path = s3_key
                if s3_key.startswith(S3_PREFIX):
                    relative_path = s3_key[len(S3_PREFIX):]
                
                # /data 디렉토리에 직접 저장 (data/ 중복 방지)
                local_file = LOCAL_DATA_DIR / relative_path
                
                # 로컬 디렉토리 생성
                local_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 파일 다운로드
                file_size = obj['Size']
                file_size_mb = file_size / (1024 * 1024)
                
                print(f"\n📥 다운로드 중: {s3_key}")
                print(f"   크기: {file_size_mb:.2f} MB")
                print(f"   저장 위치: {local_file}")
                
                s3.download_file(S3_BUCKET, s3_key, str(local_file))
                
                downloaded_count += 1
                total_size += file_size
                
                print(f"   ✅ 완료")
        
        # 결과 출력
        total_size_mb = total_size / (1024 * 1024)
        print("\n" + "=" * 70)
        print(f"✅ S3 다운로드 완료!")
        print(f"   다운로드 파일 수: {downloaded_count}")
        print(f"   총 크기: {total_size_mb:.2f} MB")
        print("=" * 70)
        
        # 다운로드된 파일 목록 출력 (샘플)
        print("\n📁 다운로드된 파일 구조:")
        print(f"   {LOCAL_DATA_DIR}/")
        
        # 주요 폴더만 표시
        for dir_name in ['RDB', 'GraphDB_data']:
            dir_path = LOCAL_DATA_DIR / dir_name
            if dir_path.exists():
                file_count = sum(1 for _ in dir_path.rglob('*') if _.is_file())
                print(f"   ├─ {dir_name}/ ({file_count} files)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ S3 다운로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    start_time = datetime.now()
    
    print(f"\n시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = download_from_s3()
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"소요 시간: {duration}\n")
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
