"""
데이터 전처리 파이프라인 통합 실행 스크립트

모든 전처리 단계를 순차적으로 실행합니다.

사용법:
    python run_all_preprocessing.py
"""

import sys
from pathlib import Path
from datetime import datetime


def run_script(script_name: str, step: int, description: str) -> bool:
    """
    스크립트를 실행합니다.
    
    Args:
        script_name: 실행할 스크립트 파일명
        step: 단계 번호
        description: 단계 설명
        
    Returns:
        성공 여부
    """
    print(f"\n{'='*80}")
    print(f"Step {step}: {description}")
    print(f"파일: {script_name}")
    print(f"{'='*80}\n")
    
    try:
        # 스크립트를 모듈로 import하여 실행
        script_path = Path(__file__).parent / script_name
        
        # 동적으로 모듈 로드
        import importlib.util
        spec = importlib.util.spec_from_file_location(script_name.replace('.py', ''), script_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        
        # main 함수 실행
        module.main()
        
        print(f"\n✅ Step {step} 완료!")
        return True
        
    except Exception as e:
        print(f"\n❌ Step {step} 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 실행 함수"""
    start_time = datetime.now()
    
    print("="*80)
    print("🚀 데이터 전처리 파이프라인 시작")
    print("="*80)
    print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 실행할 스크립트 목록
    scripts = [
        ("_00_load_Landbroker.py", 0, "Land 데이터에서 중개사 정보 추출"),
        ("_01_load_broker.py", 1, "Broker API 데이터 로드"),
        ("_02_load_brokerOffice.py", 2, "BrokerOffice API 데이터 로드"),
        ("_03_merge_all_brokers.py", 3, "모든 중개사 데이터 병합"),
        ("_04_clean_broker.py", 4, "데이터 정제"),
        ("_05_group_by_office.py", 5, "사무소별 집계"),
    ]
    
    results = []
    
    # 각 스크립트 순차 실행
    for script_name, step, description in scripts:
        success = run_script(script_name, step, description)
        results.append((step, script_name, success))
        
        # 실패 시 중단 여부 확인
        if not success:
            user_input = input("\n계속 진행하시겠습니까? (y/n): ").lower()
            if user_input != 'y':
                print("\n파이프라인을 중단합니다.")
                break
    
    # 결과 요약
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*80)
    print("📊 실행 결과 요약")
    print("="*80)
    
    for step, script_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{status} - Step {step}: {script_name}")
    
    success_count = sum(1 for _, _, success in results if success)
    total_count = len(results)
    
    print(f"\n총 실행: {total_count}개")
    print(f"성공: {success_count}개")
    print(f"실패: {total_count - success_count}개")
    print(f"소요 시간: {duration:.2f}초")
    print(f"종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    if success_count == total_count:
        print("\n🎉 모든 전처리 단계가 성공적으로 완료되었습니다!")
    else:
        print("\n⚠️  일부 단계가 실패했습니다.")


if __name__ == "__main__":
    main()
