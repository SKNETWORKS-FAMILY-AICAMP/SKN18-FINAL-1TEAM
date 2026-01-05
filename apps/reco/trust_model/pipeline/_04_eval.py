"""
_04_eval.py
중개사 신뢰도 모델 - 평가 단계
"""

import numpy as np
import pickle
import pandas as pd
from pathlib import Path
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


MODEL_TEMP_PATH = "apps/reco/trust_model/temp_trained_models.pkl"


def load_temp_model():
    """
    03_train.py에서 저장한 temp 모델 파일 로드
    """
    if not Path(MODEL_TEMP_PATH).exists():
        raise FileNotFoundError("[ERROR] temp_trained_models.pkl 파일이 없습니다. 먼저 03_train.py를 실행하세요.")

    with open(MODEL_TEMP_PATH, "rb") as f:
        data = pickle.load(f)

    return data


def evaluate_model(models, X_train, y_train, X_test, y_test, cv_results=None):
    """
    모델별 평가 수행 (훈련/테스트/CV 정확도 모두 출력)
    """
    results = []

    for name, model in models.items():
        print("\n===============================")
        print(f"📌 모델 평가: {name}")
        print("===============================")

        # 훈련 및 테스트 예측
        train_preds = model.predict(X_train)
        test_preds = model.predict(X_test)

        train_acc = accuracy_score(y_train, train_preds)
        test_acc = accuracy_score(y_test, test_preds)

        print(f"▶ Train Accuracy: {train_acc:.4f}")
        print(f"▶ Test Accuracy:  {test_acc:.4f}")
        print(f"▶ 과적합 정도:     {train_acc - test_acc:.4f}")
        
        # CV 결과가 있으면 출력
        if cv_results and name in cv_results:
            cv_mean = cv_results[name]['cv_mean']
            cv_std = cv_results[name]['cv_std']
            print(f"▶ CV Mean:        {cv_mean:.4f} (±{cv_std:.4f})")
            print(f"▶ CV vs Test:     {cv_mean - test_acc:.4f}")

        print("\n▶ Test Classification Report:")
        print(classification_report(y_test, test_preds))

        print("▶ Test Confusion Matrix:")
        cm = confusion_matrix(y_test, test_preds)
        
        # 등급 라벨 (실제 데이터에 맞게 조정)
        labels = sorted(y_test.unique())
        
        # 혼동행렬을 보기 좋게 출력
        print("\n" + " " * 12 + "예측")
        print(" " * 8 + "  ".join([f"{label:>6}" for label in labels]))
        print(" " * 6 + "-" * (8 * len(labels) + 4))
        
        for i, label in enumerate(labels):
            if i == len(labels) // 2:
                row_label = f"실제 {label} |"
            else:
                row_label = f"     {label} |"
            row_values = "  ".join([f"{val:>6}" for val in cm[i]])
            print(f"{row_label} {row_values}")
        print()

        result_dict = {
            "model": name,
            "train_accuracy": train_acc,
            "test_accuracy": test_acc,
            "overfitting": train_acc - test_acc
        }
        
        # CV 결과 추가
        if cv_results and name in cv_results:
            result_dict.update({
                "cv_mean": cv_results[name]['cv_mean'],
                "cv_std": cv_results[name]['cv_std'],
                "cv_vs_test": cv_results[name]['cv_mean'] - test_acc
            })
        
        results.append(result_dict)

    return pd.DataFrame(results)



def main():
    print("📊 모델 평가 중...")

    # 1) temp 모델 로드
    data = load_temp_model()
    models = data["models"]
    X_train = data["X_train_scaled"]
    y_train = data["y_train"]
    X_test = data["X_test_scaled"]
    y_test = data["y_test"]
    cv_results = data.get("cv_results", None)  # CV 결과 로드

    # 2) 평가
    eval_df = evaluate_model(models, X_train, y_train, X_test, y_test, cv_results)

    # 3) 평가 결과 저장 (주석 처리)
    # Path("apps/reco/models/trust_model/results").mkdir(parents=True, exist_ok=True)
    # eval_path = "apps/reco/models/trust_model/results/model_eval_results.csv"
    # eval_df.to_csv(eval_path, index=False, encoding="utf-8-sig")

    print("✅ 모델 평가 완료\n")
    
    # 4) CV 기준 최고 모델 출력
    if 'cv_mean' in eval_df.columns:
        best_cv_idx = eval_df['cv_mean'].idxmax()
        best_cv_model = eval_df.loc[best_cv_idx, 'model']
        best_cv_score = eval_df.loc[best_cv_idx, 'cv_mean']
        print(f"🏆 최고 CV 성능 모델: {best_cv_model} ({best_cv_score:.4f})")


if __name__ == "__main__":
    main()
