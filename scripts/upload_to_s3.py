#!/usr/bin/env python
"""
크롤링/전처리 완료 후 S3에 데이터 업로드

환경 변수:
- S3_BUCKET: S3 버킷 이름 (기본값: realestate-etl-data)
- S3_PREFIX: S3 프리픽스 (기본값: data/)
- AWS_REGION: AWS 리전 (기본값: ap-northeast-2)
- DATA_DIR: 로컬 데이터 디렉토리 (기본값: /data 또는 ./data)
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

# 데이터 디렉토리 결정
if os.path.exists('/data'):
    LOCAL_DATA_DIR = Path('/data')
else:
    # 스크립트 위치 기준으로 data 폴더 찾기
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    LOCAL_DATA_DIR = project_root / 'data'

def upload_to_s3():
    """로컬 데이터를 S3에 업로드"""
    print("\n" + "=" * 70)
    print(" " * 20 + "📤 S3 데이터 업로드")
    print("=" * 70)
    print(f"로컬 경로: {LOCAL_DATA_DIR}")
    print(f"S3 버킷: s3://{S3_BUCKET}/{S3_PREFIX}")
    print("=" * 70)
    
    if not LOCAL_DATA_DIR.exists():
        print(f"\n❌ 데이터 디렉토리를 찾을 수 없습니다: {LOCAL_DATA_DIR}")
        return False
    
    try:
        # S3 클라이언트 생성
        s3 = boto3.client('s3', region_name=AWS_REGION)
        
        # 업로드할 파일 목록 수집
        files_to_upload = []
        for file_path in LOCAL_DATA_DIR.rglob('*'):
            if file_path.is_file():
                files_to_upload.append(file_path)
        
        if not files_to_upload:
            print("\n⚠️ 업로드할 파일이 없습니다.")
            return True
        
        print(f"\n📋 업로드할 파일 목록 ({len(files_to_upload)}개):")
        total_size = 0
        for file_path in files_to_upload:
            size = file_path.stat().st_size
            total_size += size
            size_mb = size / (1024 * 1024)
            relative_path = file_path.relative_to(LOCAL_DATA_DIR)
            print(f"   - {relative_path} ({size_mb:.2f} MB)")
        
        total_size_mb = total_size / (1024 * 1024)
        print(f"\n총 크기: {total_size_mb:.2f} MB")
        
        # 파일 업로드
        uploaded_count = 0
        failed_count = 0
        
        print("\n📤 업로드 시작...")
        for file_path in files_to_upload:
            try:
                # S3 키 생성
                relative_path = file_path.relative_to(LOCAL_DATA_DIR)
                s3_key = f"{S3_PREFIX}{relative_path}".replace('\\', '/')
                
                # 파일 업로드
                print(f"   업로드 중: {relative_path} → s3://{S3_BUCKET}/{s3_key}")
                s3.upload_file(str(file_path), S3_BUCKET, s3_key)
                uploaded_count += 1
                
            except Exception as e:
                print(f"   ❌ 업로드 실패: {relative_path} - {e}")
                failed_count += 1
        
        # 결과 출력
        print("\n" + "=" * 70)
        print(f"✅ S3 업로드 완료!")
        print(f"   업로드 성공: {uploaded_count}개")
        if failed_count > 0:
            print(f"   업로드 실패: {failed_count}개")
        print(f"   총 크기: {total_size_mb:.2f} MB")
        print("=" * 70)
        
        return failed_count == 0
        
    except Exception as e:
        print(f"\n❌ S3 업로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    start_time = datetime.now()
    
    print(f"\n시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = upload_to_s3()
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"소요 시간: {duration}\n")
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
