"""
월세 가격 분류 ML 패키지

모듈 구조:
- loaders/: 데이터 로딩 및 파싱 (DataLoader, JSONDataParser, prepare_wolse_dataset)
- preprocessing/: 전처리 (PriceDataPreprocessor)
- training/: 모델 정의 및 학습 (get_models, ModelTrainer)
- analysis/: 분석 및 해석 (ModelExplainer, example_shap)
- inference/: 추론 (PriceClassifier)
- core/: 설정 및 유틸리티 (config, DatabaseManager)
"""

__version__ = "1.0.0"
