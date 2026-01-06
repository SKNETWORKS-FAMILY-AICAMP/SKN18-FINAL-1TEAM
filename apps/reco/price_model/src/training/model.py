"""
머신러닝 모델 정의 모듈 - 3중 분류 (저렴/적정/비쌈)
"""
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from typing import Dict

def get_models() -> Dict[str, object]:
    """
    학습에 사용할 분류 모델들을 반환

    Returns:
        모델 딕셔너리 {모델명: 모델 객체}
    """
    models = {
        "XGBoost": XGBClassifier(
            n_estimators=1200,       # 3000 -> 1200 (트리 수 감소)
            learning_rate=0.03,

            # 트리 복잡도 ↓
            max_depth=4,            # 5 -> 4
            min_child_weight=30,    # 20 -> 30

            # 샘플링 ↓
            subsample=0.6,          # 0.7 -> 0.6
            colsample_bytree=0.6,   # 0.7 -> 0.6

            # 규제 강화
            reg_alpha=3.0,          # 2.0 -> 3.0
            reg_lambda=15.0,        # 10.0 -> 15.0
            gamma=1.0,

            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
        ),

        "LightGBM": LGBMClassifier(
            n_estimators=2000,        # 충분히 크게 두고, trainer.py에서 early stopping 사용
            learning_rate=0.03,

            # 트리 복잡도 ↓
            max_depth=5,             # 7 -> 5
            num_leaves=31,           # 63 -> 31
            min_child_samples=150,   # 80 -> 150 (leaf 당 샘플 수 ↑)

            # 샘플링/피처 서브샘플링 ↑ (랜덤성 ↑ → 과적합 ↓)
            subsample=0.6,           # 0.7 -> 0.6
            colsample_bytree=0.6,    # 0.7 -> 0.6

            # 규제 강화
            reg_alpha=1.0,           # 0.5 -> 1.0 (L1)
            reg_lambda=5.0,          # 3.0 -> 5.0 (L2)
            min_split_gain=0.05,     # 0.01 -> 0.05

            objective="multiclass",
            num_class=3,
            metric="multi_logloss",
            random_state=42,
            n_jobs=-1,
            class_weight="balanced",
            is_unbalance=True,
            verbosity=-1,    
        ),
    }

    return models
