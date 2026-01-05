"""
_05_save_model.py
중개사 신뢰도 모델 - 최종 저장 단계
"""

import pickle
from pathlib import Path
import pandas as pd

TEMP_MODEL_PATH = "apps/reco/trust_model/temp_trained_models.pkl"
FINAL_MODEL_PATH = "apps/reco/trust_model/final_trust_model.pkl"
EVAL_RESULTS_PATH = "apps/reco/trust_model/model_eval_results.csv"


def select_best_model(temp_data):
    """
    temp 모델 데이터에서 최고 성능 모델 선택
    
    선택 기준:
    1. 과적합률(train_acc - test_acc)이 가장 낮은 모델
    2. 과적합률이 같으면 Test Accuracy가 높은 모델
    """
    models = temp_data["models"]
    cv_results = temp_data.get("cv_results", {})
    
    if not cv_results:
        # CV 결과가 없으면 첫 번째 모델 선택
        first_model = list(models.keys())[0]
        print(f"⚠️ CV 결과가 없습니다. 첫 번째 모델을 선택합니다: {first_model}")
        return first_model
    
    # 모델별 성능 정보 수집
    model_scores = []
    
    print("📊 모델별 성능:")
    for model_name, results in cv_results.items():
        train_acc = results['train_acc']
        test_acc = results['test_acc']
        overfitting_rate = train_acc - test_acc  # 과적합률
        cv_mean = results['cv_mean']
        cv_std = results['cv_std']
        
        print(f"  {model_name}:")
        print(f"    - Train Accuracy: {train_acc:.4f}")
        print(f"    - Test Accuracy:  {test_acc:.4f}")
        print(f"    - 과적합률:        {overfitting_rate:.4f}")
        print(f"    - CV Mean:        {cv_mean:.4f} (±{cv_std:.4f})")
        
        model_scores.append({
            'name': model_name,
            'overfitting_rate': overfitting_rate,
            'test_acc': test_acc,
            'train_acc': train_acc,
            'cv_mean': cv_mean
        })
    
    # 정렬: 1) 과적합률 오름차순, 2) Test Accuracy 내림차순
    model_scores.sort(key=lambda x: (x['overfitting_rate'], -x['test_acc']))
    
    best_model_info = model_scores[0]
    best_model = best_model_info['name']
    
    print(f"\n🏆 최고 성능 모델 (과적합률 최소 + Test 정확도 최대): {best_model}")
    print(f"   - 과적합률: {best_model_info['overfitting_rate']:.4f}")
    print(f"   - Test Accuracy: {best_model_info['test_acc']:.4f}")
    print(f"   - Train Accuracy: {best_model_info['train_acc']:.4f}")
    
    return best_model


def main():
    print("💾 최종 모델 저장 중...")

    # 1) temp 모델 파일 확인
    if not Path(TEMP_MODEL_PATH).exists():
        raise FileNotFoundError(f"[ERROR] {TEMP_MODEL_PATH} 파일이 없습니다. 먼저 03_train.py를 실행하세요.")

    # 2) temp 모델 로드
    with open(TEMP_MODEL_PATH, "rb") as f:
        temp_data = pickle.load(f)

    # 3) 최고 성능 모델 선택
    best_model_name = select_best_model(temp_data)

    # 4) 최고 성능 모델만 추출하여 최종 저장
    Path("apps/reco/models/trust_model/model").mkdir(parents=True, exist_ok=True)
    
    final_model_data = {
        "model": temp_data["models"][best_model_name],
        "scaler": temp_data["scaler"],
        "feature_names": temp_data["feature_names"],
        "model_name": best_model_name
    }

    with open(FINAL_MODEL_PATH, "wb") as f:
        pickle.dump(final_model_data, f)

    print(f"✓ 최종 모델 저장 완료: {FINAL_MODEL_PATH}")
    print(f"✓ 선택된 모델: {best_model_name}")


if __name__ == "__main__":
    main()
