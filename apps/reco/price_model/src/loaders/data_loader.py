"""
데이터 로딩 모듈
"""
import pandas as pd
from pathlib import Path
from typing import Tuple


class DataLoader:
    """월세 실거래가 데이터 로더"""

    def __init__(self, base_dir: str):
        """
        Args:
            base_dir: 데이터 디렉토리 경로
        """
        self.base_dir = Path(base_dir)

    def load_train_test(
        self,
        train_filename: str = "월세_train(24.08~25.08).csv",
        test_filename: str = "월세_test(25.09~25.10).csv"
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        학습/테스트 데이터 로드

        Args:
            train_filename: 학습 데이터 파일명
            test_filename: 테스트 데이터 파일명

        Returns:
            (train_df, test_df) 튜플
        """
        train_path = self.base_dir / train_filename
        test_path = self.base_dir / test_filename

        print(f"📂 데이터 로딩 중...")
        train = pd.read_csv(train_path, encoding="utf-8-sig")
        test = pd.read_csv(test_path, encoding="utf-8-sig")

        print(f"   - Train: {train.shape}")
        print(f"   - Test:  {test.shape}")

        return train, test
