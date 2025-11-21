import json
import os

def merge_json_by_category():
    # ---------------------------------------------------------
    # [수정됨] 경로 설정
    # ---------------------------------------------------------
    # 1. 현재 스크립트가 있는 폴더 경로
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. JSON 파일들이 들어있는 'data' 폴더 경로 결합
    data_dir = os.path.join(current_dir, 'data')
    
    # data 폴더가 실제로 있는지 확인
    if not os.path.exists(data_dir):
        print(f"❌ 오류: '{data_dir}' 폴더를 찾을 수 없습니다.")
        return

    # ---------------------------------------------------------
    # 병합 설정
    # ---------------------------------------------------------
    category_map = {
        "아파트": "00_통합_아파트.json",
        "원투룸": "00_통합_원투룸.json",
        "빌라주택": "00_통합_빌라주택.json",
        "오피스텔": "00_통합_오피스텔.json",
        "상가": "00_통합_상가.json"
    }

    # 'data' 폴더 내의 모든 json 파일 확인
    # (listdir는 파일명만 가져오므로 나중에 data_dir와 합쳐야 함)
    all_files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
    
    print(f"--- [병합 시작] '{data_dir}' 폴더 내 JSON 파일 {len(all_files)}개 감지됨 ---")

    for keyword, output_filename in category_map.items():
        merged_data = []
        processed_files_count = 0
        
        # 해당 키워드가 포함된 파일 찾기 (단, 통합 파일 자체는 제외)
        target_files = [f for f in all_files if keyword in f and "00_통합" not in f]
        
        if not target_files:
            continue

        print(f"\n>> 카테고리: '{keyword}' 병합 중... (대상 파일: {len(target_files)}개)")

        for filename in target_files:
            # [수정] 파일 전체 경로 생성 (data 폴더 + 파일명)
            file_path = os.path.join(data_dir, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        merged_data.extend(data) # 리스트 합치기
                        processed_files_count += 1
                    else:
                        print(f"  [경고] '{filename}' 파일 형식이 리스트가 아닙니다. 건너뜁니다.")
            except Exception as e:
                print(f"  [오류] '{filename}' 읽기 실패: {e}")

        # 병합된 데이터가 있으면 'data' 폴더 안에 저장
        if merged_data:
            # (중복 제거 로직) 매물번호 기준
            unique_data = {item.get('매물번호'): item for item in merged_data if item.get('매물번호')}.values()
            final_list = list(unique_data)

            # [수정] 저장 경로도 'data' 폴더 내부로 지정
            output_path = os.path.join(data_dir, output_filename)

            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(final_list, f, ensure_ascii=False, indent=2)
                
                print(f"  ✅ 저장 완료: {output_filename}")
                print(f"  📊 합계: 파일 {processed_files_count}개 / 매물 {len(merged_data)}개 -> (중복제거 후) {len(final_list)}개")
            except Exception as e:
                print(f"  ❌ 저장 실패: {e}")
        else:
            print(f"  ⚠️ 병합할 데이터가 없습니다.")

    print("\n--- [병합 완료] 모든 작업이 끝났습니다. ---")

if __name__ == "__main__":
    merge_json_by_category()