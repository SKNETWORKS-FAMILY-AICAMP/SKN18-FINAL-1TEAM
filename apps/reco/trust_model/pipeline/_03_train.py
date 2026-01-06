"""
_03_train.py
중개사 신뢰도 모델 - 학습 단계 (LogisticRegression)
이미 분할된 Train/Test 데이터 사용
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from pathlib import Path
import pickle
import warnings
warnings.filterwarnings('ignore')

TRAIN_PATH = "data/ML/trust/X_train.csv"
TEST_PATH = "data/ML/trust/X_test.csv"
TRAIN_TARGET_PATH = "data/ML/trust/y_train.csv"
TEST_TARGET_PATH = "data/ML/trust/y_test.csv"
MODEL_TEMP_PATH = "apps/reco/trust_model/temp_trained_models.pkl"


def load_processed_data():
    """이미 처리된 Train/Test 데이터 로드"""
    
    if not Path(TRAIN_PATH).exists():
        raise FileNotFoundError(f"[ERROR] Train 파일이 존재하지 않음: {TRAIN_PATH}")
    if not Path(TRAIN_TARGET_PATH).exists():
        raise FileNotFoundError(f"[ERROR] Train Target 파일이 존재하지 않음: {TRAIN_TARGET_PATH}")
    
    print(f"📂 [1단계] 처리된 데이터 로드")
    X_train = pd.read_csv(TRAIN_PATH, encoding="utf-8-sig")
    X_test = pd.read_csv(TEST_PATH, encoding="utf-8-sig")
    y_train = pd.read_csv(TRAIN_TARGET_PATH, encoding="utf-8-sig").squeeze()
    y_test = pd.read_csv(TEST_TARGET_PATH, encoding="utf-8-sig").squeeze()
    
    print(f"   - Train: {len(X_train):,}개")
    print(f"   - Test: {len(X_test):,}개")
    
    # Feature는 이미 _02_create_features.py에서 선택되어 있음
    # X_train, X_test는 그대로 사용

    
    print(f"\n📊 최종 Feature 수: {len(X_train.columns)}개")
    print(f"📋 사용된 Feature:")
    for i, feature in enumerate(X_train.columns, 1):
        print(f"   {i:2d}. {feature}")
    
    # 등급 분포 확인
    print(f"\n📊 Train 등급 분포:")
    train_dist = y_train.value_counts().sort_index()
    for grade, count in train_dist.items():
        print(f"   {grade}: {count}개 ({count/len(y_train)*100:.1f}%)")
    
    print(f"\n📊 Test 등급 분포:")
    test_dist = y_test.value_counts().sort_index()
    for grade, count in test_dist.items():
        print(f"   {grade}: {count}개 ({count/len(y_test)*100:.1f}%)")
    
    return X_train, X_test, y_train, y_test


def train_models(X_train_scaled, y_train, X_test_scaled, y_test):
    """
    LogisticRegression 모델 학습
    """
    print("\n🤖 모델 학습 시작...")
    
    models = {}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # LogisticRegression (최적 하이퍼파라미터 적용)
    print("\n[1/1] LogisticRegression 학습 중...")
    print("   - 최적 하이퍼파라미터 적용 (GridSearchCV 결과)")
    print("   - C=1, penalty=l1, solver=saga, class_weight=balanced")
    lr_model = LogisticRegression(
        C=1,  # 정규화 강도 (튜닝 결과)
        penalty='l1',  # L1 정규화 (피처 선택 효과)
        solver='saga',  # L1을 지원하는 solver
        max_iter=1000,
        class_weight='balanced',
        random_state=42
    )
    lr_model.fit(X_train_scaled, y_train)
    lr_scores = cross_val_score(lr_model, X_train_scaled, y_train, cv=cv, scoring='accuracy')
    models["LogisticRegression"] = lr_model
    print(f"   ✓ CV Score: {lr_scores.mean():.4f} (±{lr_scores.std():.4f})")
    
    print("\n✅ 모델 학습 완료!")
    return models


def main():
    print("=" * 70)
    print(" " * 20 + "모델 학습")
    print("=" * 70)

    # 1) 이미 분할된 데이터 로드
    X_train, X_test, y_train, y_test = load_processed_data()
    
    # 2) 스케일링 (Train 기준으로 fit, Test에 transform)
    print("\n🔍 [2단계] 데이터 스케일링")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    print("   ✅ StandardScaler 적용 완료 (Train 기준)")
    
    # 총거래활동량_log 피처의 가중치를 0.5배로 축소
    feature_names = X_train.columns.tolist()
    if "총거래활동량_log" in feature_names:
        feature_idx = feature_names.index("총거래활동량_log")
        X_train_scaled[:, feature_idx] *= 0.5
        X_test_scaled[:, feature_idx] *= 0.5
        print("   ✅ 총거래활동량_log 가중치 0.5배로 축소")
    
    # 3) 모델 학습
    models = train_models(X_train_scaled, y_train, X_test_scaled, y_test)
    
    # 4) Test 세트 평가
    print("\n" + "=" * 70)
    print(" " * 20 + "모델 성능 평가")
    print("=" * 70)
    
    cv_results = {}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    for name, model in models.items():
        # Train/Test 예측
        train_pred = model.predict(X_train_scaled)
        test_pred = model.predict(X_test_scaled)
        train_acc = accuracy_score(y_train, train_pred)
        test_acc = accuracy_score(y_test, test_pred)
        
        # CV 점수
        cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=cv, scoring='accuracy')
        
        cv_results[name] = {
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'train_acc': train_acc,
            'test_acc': test_acc
        }
        
        print(f"\n  {name}:")
        print(f"    - Train Accuracy: {train_acc:.4f}")
        print(f"    - Test Accuracy:  {test_acc:.4f}")
        print(f"    - 과적합 정도:     {train_acc - test_acc:.4f}")
        print(f"    - CV Mean:        {cv_scores.mean():.4f} (±{cv_scores.std():.4f})")
    
    # 5) 모델 + 스케일러 저장
    Path("apps/reco/models/trust_model/model").mkdir(parents=True, exist_ok=True)
    with open(MODEL_TEMP_PATH, "wb") as f:
        pickle.dump(
            {
                "models": models,
                "scaler": scaler,
                "X_train_scaled": X_train_scaled,
                "y_train": y_train,
                "X_test_scaled": X_test_scaled,
                "y_test": y_test,
                "feature_names": list(X_train.columns),
                "cv_results": cv_results,
            },
            f,
        )
    
    print(f"\n✓ 학습 완료, temp 모델 저장: {MODEL_TEMP_PATH}")
    
    # 6) 최고 성능 모델 출력
    best_model_name = max(cv_results.keys(), key=lambda k: cv_results[k]['test_acc'])
    print(f"\n🏆 최고 Test 성능 모델: {best_model_name}")
    print(f"   - Test Accuracy: {cv_results[best_model_name]['test_acc']:.4f}")
    print(f"   - Train Accuracy: {cv_results[best_model_name]['train_acc']:.4f}")
    
    print("\n" + "=" * 70)
    print(" " * 25 + "완료!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
