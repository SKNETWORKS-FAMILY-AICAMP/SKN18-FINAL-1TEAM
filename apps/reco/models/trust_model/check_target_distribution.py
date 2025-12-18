"""
check_target_distribution.py
생성된 Train/Test 타겟 파일(CSV)을 로드하여
등급 분포(A/B/C)를 시각화하고 저장합니다.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 한글 폰트 설정 (Windows)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

def main():
    print("📊 타겟 분포 시각화 도구 실행\n")
    
    # 1. 파일 경로
    train_path = Path("data/ML/trust/train_target.csv")
    test_path = Path("data/ML/trust/test_target.csv")
    save_dir = Path("results/validation")
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. 로드
    if not train_path.exists() or not test_path.exists():
        print(f"❌ 파일이 없습니다.\n- {train_path}\n- {test_path}")
        return
        
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    
    print(f"📂 Train: {len(train_df)}개")
    print(f"📂 Test:  {len(test_df)}개")
    
    # 3. 데이터 통합 (Source 컬럼 추가)
    # Target 컬럼: 0(C), 1(B), 2(A) 가정
    grade_map = {0: "C", 1: "B", 2: "A"}
    
    train_df['Grade'] = train_df['Target'].map(grade_map)
    test_df['Grade'] = test_df['Target'].map(grade_map)
    
    train_df['Source'] = 'Train'
    test_df['Source'] = 'Test'
    
    combined_df = pd.concat([train_df[['Grade', 'Source']], test_df[['Grade', 'Source']]])
    
    # 4. 시각화
    plt.figure(figsize=(10, 6))
    
    # 등급 순서 지정 (C -> B -> A)
    order = ["C", "B", "A"]
    
    # Countplot
    ax = sns.countplot(data=combined_df, x='Grade', hue='Source', order=order, palette='viridis')
    
    plt.title('Train vs Test 등급(Target) 분포 비교', fontsize=14, fontweight='bold')
    plt.xlabel('신뢰도 등급', fontsize=12)
    plt.ylabel('사무소 수 (Count)', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # 값 표시
    for p in ax.patches:
        height = p.get_height()
        if height > 0:
            ax.text(p.get_x() + p.get_width()/2., height + 1, f'{int(height)}', 
                    ha="center", fontsize=10)
    
    # 5. 저장
    save_path = save_dir / "00_target_distribution_check.png"
    plt.savefig(save_path, dpi=130, bbox_inches='tight')
    plt.close()
    
    print(f"\n✅ 그래프 저장 완료: {save_path}")
    
    # 6. 수치 출력
    print("\n[Train 분포]")
    print(train_df['Grade'].value_counts(normalize=True).reindex(order).map(lambda x: f"{x*100:.1f}%"))
    
    print("\n[Test 분포]")
    print(test_df['Grade'].value_counts(normalize=True).reindex(order).map(lambda x: f"{x*100:.1f}%"))

if __name__ == "__main__":
    main()
