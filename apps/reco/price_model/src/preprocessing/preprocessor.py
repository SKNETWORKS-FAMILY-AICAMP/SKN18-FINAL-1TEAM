"""
데이터 전처리 및 피처 엔지니어링 모듈
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from typing import Tuple, List, Dict


class PriceDataPreprocessor:
    """월세 실거래가 데이터 전처리 클래스"""

    def __init__(self, target_name: str = "가격_클래스"):
        """
        Args:
            target_name: 타깃 변수명 (분류 클래스)
        """
        self.target_name = target_name
        self.price_column = "환산보증금_평당가"  # 가격 계산용 컬럼
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.preprocessor: ColumnTransformer = None
        self.candidate_features: List[str] = []

        # 클래스 레이블 정의
        self.class_labels = {
            0: {"label": "UNDERPRICED", "label_kr": "저렴"},
            1: {"label": "FAIR", "label_kr": "적정"},
            2: {"label": "OVERPRICED", "label_kr": "비쌈"}
        }
        
        # 학습 데이터 통계 저장용
        self.train_stats = {}
        self.area_bins = None
        self.gu_deposit_mean = None
        self.train_gu_quantiles = None
        self.gu_count_qcat = None

    def create_target(self, df: pd.DataFrame, train_stats: Dict = None) -> pd.DataFrame:
        """
        3중 분류 타깃 생성 (저렴/적정/비쌈)

        행정동×건물용도별 분위수 기준으로 분류 (Train 데이터 기준):
        - < 33.3%ile: 저렴 (UNDERPRICED, class=0)
        - 33.3%ile ~ 66.7%ile: 적정 (FAIR, class=1)
        - > 66.7%ile: 비쌈 (OVERPRICED, class=2)

        Args:
            df: 원본 데이터프레임
            train_stats: 학습 데이터의 통계 (테스트 데이터 처리 시 사용)
                    {"gu_quantiles": {(법정동명, 건물용도): (q33, q67)}}
        """

        df = df.copy()

        # 적용 이자율 계산 (안전한 최소 이자율)
        df["적용이자율"] = (df["기준금리"] + 2.0) / 100.0
        df.loc[df["적용이자율"] <= 0, "적용이자율"] = np.nan

        # 환산보증금: 보증금 + 월세를 전세로 환산
        df["환산보증금(만원)"] = df["보증금(만원)"] + (df["임대료(만원)"] * 12) / df["적용이자율"]

        # 평수 계산
        df["전용평수"] = df["임대면적"] / 3.3

        # 평당 환산보증금 계산
        df[self.price_column] = df["환산보증금(만원)"] / df["전용평수"]

        # 연월에서 연도/월 분리
        df["계약연도"] = df["연월"].str.slice(0, 4).astype(int)
        df["계약월"] = df["연월"].str.slice(5, 7).astype(int)

        # 건물 연식 계산
        df["건물연식"] = df["계약연도"] - df["건축년도"]

        # 행정동×건물용도별 분위수 계산
        if train_stats is None:
            # Train 데이터: 자체 통계 계산
            group_quantiles: Dict[tuple, tuple] = {}
            grouped = df.groupby(["법정동명", "건물용도"])
            for key, g in grouped:
                values = g[self.price_column].dropna()
                if len(values) > 0:
                    q33 = values.quantile(0.333)
                    q67 = values.quantile(0.667)
                else:
                    # 데이터 없으면 전체 분위수 사용
                    q33 = df[self.price_column].quantile(0.333)
                    q67 = df[self.price_column].quantile(0.667)
                group_quantiles[key] = (q33, q67)

            # 기존 인터페이스와 호환성을 위해 이름 유지
            self.train_gu_quantiles = group_quantiles
            print(f"\n✅ 행정동×건물용도별 분위수 기준 계산 완료 ({len(group_quantiles)}개 그룹)")
        else:
            # Test 데이터: Train의 통계 사용
            group_quantiles = train_stats.get("gu_quantiles", {})


        # 3중 분류 레이블 생성
        def classify_price_by_quantile(row):
            key = (row["법정동명"], row["건물용도"])
            price = row[self.price_column]

            if pd.isna(price):
                return 1  # 정보 없으면 적정으로 분류

            # 행정동×건물용도 분위수 가져오기
            if key in group_quantiles:
                q33, q67 = group_quantiles[key]
            else:
                # 해당 그룹 정보 없으면 전체 분위수 사용
                q33 = df[self.price_column].quantile(0.25)
                q67 = df[self.price_column].quantile(0.75)

            # 분위수 기준 분류
            if price < q33:
                return 0  # 저렴
            elif price > q67:
                return 2  # 비쌈
            else:
                return 1  # 적정

        df[self.target_name] = df.apply(classify_price_by_quantile, axis=1)

        return df

    def advanced_feature_engineering(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        노트북 기반 고급 피처 엔지니어링 (시계열 안전 버전)

        Args:
            train_df: 학습 데이터
            test_df: 테스트 데이터

        Returns:
            (전처리된 train_df, 전처리된 test_df)
        """
        df_train = train_df.copy()
        df_test = test_df.copy()

        if df_test.empty and len(df_test.columns) == 0:
            df_test = df_train.iloc[:0].copy()

        print("\n" + "=" * 60)
        print("🔧 고급 Feature Engineering 시작 (개선 버전)")
        print("=" * 60)

        # 🚨 중요: 시계열 데이터이므로 연월 기준 정렬
        print("0. 시계열 정렬 중...")
        df_train = df_train.sort_values("연월").reset_index(drop=True)
        df_test = df_test.sort_values("연월").reset_index(drop=True)

        # 1. 면적 범주화 (5분위수 기반)
        print("1. 면적 범주화 중...")
        if self.area_bins is None:
            qbin, bins = pd.qcut(
                df_train["임대면적"],
                q=5,
                labels=False,
                retbins=True,
                duplicates="drop"
            )
            self.area_bins = bins
        else:
            bins = self.area_bins

        label_map = {
            0: "초소형",
            1: "소형",
            2: "중소형",
            3: "중형",
            4: "대형이상"
        }

        df_train["면적_qcat"] = pd.cut(
            df_train["임대면적"],
            bins=bins,
            labels=[label_map[i] for i in range(len(bins)-1)],
            include_lowest=True
        )

        df_test["면적_qcat"] = pd.cut(
            df_test["임대면적"],
            bins=bins,
            labels=[label_map[i] for i in range(len(bins)-1)],
            include_lowest=True
        )

        # 2. 자치구 권역
        print("2. 자치구 권역 생성 중...")
        east = ["광진구", "중랑구", "동대문구", "성동구", "강북구", "도봉구", "성북구", "노원구"]
        west = ["은평구", "서대문구", "마포구"]
        south = ["강서구", "양천구", "영등포구", "구로구", "금천구", "관악구", "동작구"]
        city = ["종로구", "중구", "용산구"]

        def map_direction(gu):
            if gu in east:
                return "동북"
            if gu in west:
                return "서북"
            if gu in south:
                return "서남"
            if gu in city:
                return "도심"
            return "동남"

        df_train["구_권역"] = df_train["자치구명"].apply(map_direction)
        df_test["구_권역"] = df_test["자치구명"].apply(map_direction)

        # 3. 연월 → 분기 변환
        print("3. 분기 변환 중...")
        df_train["연월_dt"] = pd.to_datetime(df_train["연월"], errors='coerce')
        df_test["연월_dt"] = pd.to_datetime(df_test["연월"], errors='coerce')

        # df_train["분기"] = df_train["연월_dt"].dt.quarter
        # df_train["분기_라벨"] = df_train["분기"].astype(str) + "분기"

        # df_test["분기"] = df_test["연월_dt"].dt.quarter
        # df_test["분기_라벨"] = df_test["분기"].astype(str) + "분기"

        # #3-1. 계약 월/계절/반기
        # print("3-1. 계약 월/계절/반기 생성 중...")
        # for df in (df_train, df_test):
        #     if "계약월" not in df.columns:
        #         df["계약월"] = pd.to_datetime(df["연월"], errors="coerce").dt.month

        #     month = df["계약월"]

        #     def map_season(m):
        #             if m in [3, 4, 5]:
        #                 return "봄"
        #             if m in [6, 7, 8]:
        #                 return "여름"
        #             if m in [9, 10, 11]:
        #                 return "가을"
        #             return "겨울"

        #     df["계약_계절"] = month.apply(map_season)
        #   df["계약_반기"] = np.where(month <= 6, "상반기", "하반기")

        # # 4. 층 구간화
        # print("4. 층 구간화 중...")
        # df_train["층_bin"] = pd.cut(
        #     df_train["층"],
        #     bins=[0, 3, 6, 11, 70],
        #     labels=["저층", "중층", "중고층", "고층"]
        # )

        # df_test["층_bin"] = pd.cut(
        #     df_test["층"],
        #     bins=[0, 3, 6, 11, 70],
        #     labels=["저층", "중층", "중고층", "고층"]
        # )

        # 5. 건축연차 계산 (이미 create_target에 있지만 확인)
        print("5. 건축연차 확인 중...")
        if "건축연차" not in df_train.columns:
            df_train["계약연도"] = pd.to_datetime(df_train["연월"]).dt.year
            df_train["건축연차"] = df_train["계약연도"] - df_train["건축년도"]

        if "건축연차" not in df_test.columns:
            df_test["계약연도"] = pd.to_datetime(df_test["연월"]).dt.year
            df_test["건축연차"] = df_test["계약연도"] - df_test["건축년도"]

        # 6. 건축시대 구간화
        print("6. 건축시대 구간화 중...")
        df_train["건축시대"] = pd.cut(
            df_train["건축년도"],
            bins=[0, 2000, 2010, 2020, 2025],
            labels=["2000년 이전", "00년대", "10년대", "20년대 이후"]
        )

        df_test["건축시대"] = pd.cut(
            df_test["건축년도"],
            bins=[0, 2000, 2010, 2020, 2025],
            labels=["2000년 이전", "00년대", "10년대", "20년대 이후"]
        )

        # 7. 복합 카테고리 생성 (자치구_건물용도)
        print("7. 복합 카테고리 생성 중...")
        df_train["자치구_건물용도"] = df_train["자치구명"] + "_" + df_train["건물용도"]
        df_test["자치구_건물용도"] = df_test["자치구명"] + "_" + df_test["건물용도"]

        # 8. 자치구별 거래량
        print("8. 자치구별 거래량 계산 중...")
        gu_count = df_train.groupby("자치구명").size().to_dict()
        df_train["자치구_거래량"] = df_train["자치구명"].map(gu_count)
        df_test["자치구_거래량"] = df_test["자치구명"].map(gu_count)

        # 자치구 거래량 구간화
        if self.gu_count_qcat is None:
            # train의 경계값을 기준으로 test도 구간화
            train_boundaries = df_train.groupby("자치구명")["자치구_거래량"].first()
            train_qcat = pd.qcut(
                train_boundaries,
                q=3,
                labels=['하위거래구', '중위거래구', '상위거래구'],
                duplicates="drop"
            ).to_dict()
            self.gu_count_qcat = train_qcat
        else:
            train_qcat = self.gu_count_qcat

        df_train["자치구_거래량_구간"] = df_train["자치구명"].map(train_qcat)
        df_test["자치구_거래량_구간"] = df_test["자치구명"].map(train_qcat)

        # 9. 금리 특성 생성 중...
        print("9. 금리 특성 생성 중...")
        rate_cols = ["무담보콜금리", "KORIBOR", "CD", "기업대출", "전세자금대출", "변동형주택담보대출"]

        available_rate_cols = [c for c in rate_cols if c in df_train.columns]
        missing_rate_cols = [c for c in rate_cols if c not in df_train.columns]

        if missing_rate_cols:
            print(f"[경고] 금리 컬럼 없음 (무시): {missing_rate_cols}")

        if available_rate_cols:
            df_train["금리_평균"] = df_train[available_rate_cols].mean(axis=1)
            df_test["금리_평균"] = df_test[available_rate_cols].mean(axis=1)
        else:
            # 금리 컬럼이 하나도 없는 극단 상황 대비
            df_train["금리_평균"] = np.nan
            df_test["금리_평균"] = np.nan


        # df_train["금리_평균"] = df_train[rate_cols].mean(axis=1)
        # df_test["금리_평균"] = df_test[rate_cols].mean(axis=1)

        # 금리 이동평균
        # df_train["금리_MA_6"] = df_train["금리_평균"].rolling(window=6, min_periods=1).mean()
        # df_test["금리_MA_6"] = df_test["금리_평균"].rolling(window=6, min_periods=1).mean()

        # 금리 편차
        # df_train["금리_편차"] = df_train["금리_평균"] - df_train["금리_MA_6"]
        # df_test["금리_편차"] = df_test["금리_평균"] - df_test["금리_MA_6"]

        # 금리 국면
        # df_train["금리_국면"] = pd.cut(
        #     df_train["금리_편차"],
        #     bins=[-np.inf, -0.05, 0.05, np.inf],
        #     labels=["인하국면", "동결국면", "인상국면"]
        # )

        # df_test["금리_국면"] = pd.cut(
        #     df_test["금리_편차"],
        #     bins=[-np.inf, -0.05, 0.05, np.inf],
        #     labels=["인하국면", "동결국면", "인상국면"]
        # )

        # # 10. 금리 z-score 구간
        # print("10. 금리 z-score 구간화 중...")
        # mean_rate = df_train["금리_평균"].mean()
        # std_rate = df_train["금리_평균"].std()

        # df_train["금리_z"] = (df_train["금리_평균"] - mean_rate) / std_rate
        # df_test["금리_z"] = (df_test["금리_평균"] - mean_rate) / std_rate

        # df_train["금리_z_구간"] = pd.cut(
        #     df_train["금리_z"],
        #     bins=[-np.inf, -1, 1, np.inf],
        #     labels=["낮음", "보통", "높음"]
        # )

        # df_test["금리_z_구간"] = pd.cut(
        #     df_test["금리_z"],
        #     bins=[-np.inf, -1, 1, np.inf],
        #     labels=["낮음", "보통", "높음"]
        # )

        # 10-1. 금리/물가/보증금/임대료 관련 추가 범주형 피처
        print("10-1. 추가 범주형 금리/가격 피처 생성 중...")

        for df in (df_train, df_test):
            # # 기준금리 레벨 (논리적 구간: 2.5, 3.0, 3.5 기준)
            # df["기준금리_레벨"] = pd.cut(
            #     df["기준금리"],
            #     bins=[-np.inf, 2.5, 3.0, np.inf],
            #     labels=["저금리", "중간금리", "고금리"]
            # )

            # # 소비자물가 레벨 (대략 1.8, 2.2 기준)
            # df["소비자물가_레벨"] = pd.cut(
            #     df["소비자물가"],
            #     bins=[-np.inf, 1.8, 2.2, np.inf],
            #     labels=["저물가", "보통물가", "고물가"]
            # )

            # # 보증금 구간 (만원 단위: 0~2천 / 2천~6천 / 6천~2만 / 2만 초과)
            # df["보증금_구간"] = pd.cut(
            #     df["보증금(만원)"],
            #     bins=[-np.inf, 2000, 6000, 20000, np.inf],
            #     labels=["저보증금(≤2천)", "중간보증금(2천~6천)", "고보증금(6천~2만)", "초고보증금(>2만)"]
            # )

            # # 임대료 구간 (만원 단위: 0~30 / 30~60 / 60~100 / 100 초과)
            # df["임대료_구간"] = pd.cut(
            #     df["임대료(만원)"],
            #     bins=[-np.inf, 30, 60, 100, np.inf],
            #     labels=["저임대료(≤30)", "중간임대료(30~60)", "중고임대료(60~100)", "고임대료(>100)"]
            # )

            # 보증금/임대료 비율 및 구간
            ratio = df["보증금(만원)"] / df["임대료(만원)"].replace({0: np.nan})
            df["보증금임대료비율"] = ratio
            df["보증금임대료비율_구간"] = pd.cut(
                ratio,
                bins=[-np.inf, 50, 200, 1000, np.inf],
                labels=["매우낮음(≤50)", "보통비율(50~200)", "높은비율(200~1000)", "매우높음(>1000)"]
            )

            # # KORIBOR - 기준금리 스프레드 및 구간
            # spread = df["KORIBOR"] - df["기준금리"]
            # df["KORIBOR_스프레드"] = spread
            # df["KORIBOR_스프레드_구간"] = pd.cut(
            #     spread,
            #     bins=[-np.inf, -0.05, 0.05, np.inf],
            #     labels=["역전/매우낮음", "근접", "높음"]
            # )

        # 11. 자치구 수준 z-score (전용면적, 건축연도, 층수)
        # print("11. 자치구 수준 z-score 생성 중...")

        # # 자치구별 평균 계산
        # gu_mean_area = df_train.groupby("자치구명")["전용평수"].mean().to_dict()
        # gu_mean_year = df_train.groupby("자치구명")["건축년도"].mean().to_dict()
        # gu_mean_floor = df_train.groupby("자치구명")["층"].mean().to_dict()

        # # 각 데이터셋에 자치구 평균 매핑
        # for df in [df_train, df_test]:
        #     df["자치구_평균_전용면적"] = df["자치구명"].map(gu_mean_area)
        #     df["자치구_평균_건축연도"] = df["자치구명"].map(gu_mean_year)
        #     df["자치구_평균_층수"] = df["자치구명"].map(gu_mean_floor)

        #     # 평균 대비 비율 계산
        #     df["평균대비_전용면적"] = df["전용평수"] / df["자치구_평균_전용면적"]
        #     df["평균대비_건축연도"] = df["건축년도"] / df["자치구_평균_건축연도"]
        #     df["평균대비_층수"] = df["층"] / df["자치구_평균_층수"]

        # # z-score 계산
        # for col in ["평균대비_전용면적", "평균대비_건축연도", "평균대비_층수"]:
        #     mu = df_train[col].mean()
        #     sigma = df_train[col].std()
        #     df_train[col + "_z"] = (df_train[col] - mu) / sigma
        #     df_test[col + "_z"] = (df_test[col] - mu) / sigma

        # def z_bin(z):
        #     if z <= -1:
        #         return "낮음"
        #     elif z <= 1:
        #         return "보통"
        #     else:
        #         return "높음"

        # df_train["전용면적_자치구수준_z"] = df_train["평균대비_전용면적_z"].apply(z_bin)
        # df_train["건축연도_자치구수준_z"] = df_train["평균대비_건축연도_z"].apply(z_bin)
        # # df_train["층수_자치구수준_z"] = df_train["평균대비_층수_z"].apply(z_bin)

        # df_test["전용면적_자치구수준_z"] = df_test["평균대비_전용면적_z"].apply(z_bin)
        # df_test["건축연도_자치구수준_z"] = df_test["평균대비_건축연도_z"].apply(z_bin)
        # # df_test["층수_자치구수준_z"] = df_test["평균대비_층수_z"].apply(z_bin)

        # # 12. 기준금리_전월대비_범주
        # print("12. 기준금리_전월대비_범주 생성 중...")

        # # 연월별 금리 테이블 생성 (train에서만)
        # macro = (
        #     df_train[["연월", "연월_dt", "기준금리"]]
        #     .drop_duplicates()
        #     .sort_values("연월_dt")
        #     .reset_index(drop=True)
        # )

        # # 전월 기준금리 값 계산
        # macro["기준금리_전월값"] = macro["기준금리"].shift(1)

        # # train과 test에 연월 기준으로 매핑
        # for df in [df_train, df_test]:
        #     df_temp = df.merge(
        #         macro[["연월", "기준금리_전월값"]],
        #         on="연월",
        #         how="left"
        #     )

        #     # 전월 대비 변화율
        #     df_temp["기준금리_전월대비변화"] = (
        #         (df_temp["기준금리"] - df_temp["기준금리_전월값"]) / df_temp["기준금리_전월값"]
        #     )

        #     def sign_cat_label(x):
        #         if pd.isna(x):
        #             return "변화없음"
        #         if x > 0:
        #             return "상승"
        #         if x < 0:
        #             return "하락"
        #         return "변화없음"

        #     df_temp["기준금리_전월대비_범주"] = (
        #         df_temp["기준금리_전월대비변화"].apply(sign_cat_label).astype("category")
        #     )

        #     # 원본 df 업데이트
        #     if df is df_train:
        #         df_train = df_temp
        #     else:
        #         df_test = df_temp

        # 13. 자치구_월별_임대료수준_구간
        print("13. 자치구_월별_임대료수준_구간 생성 중...")

        for df in [df_train, df_test]:
            # 자치구-연월 그룹 평균
            gu_month_mean = (
                df.groupby(["자치구명", "연월"])["임대료(만원)"]
                .transform("mean")
            )
            df["자치구_월별_평균임대료"] = gu_month_mean

            # 계약 임대료 / 평균 비율
            ratio = df["임대료(만원)"] / df["자치구_월별_평균임대료"]
            df["자치구_월별_평균대비비율"] = ratio

            # 범주화 (±10% 기준)
            def level_cat(r):
                if pd.isna(r):
                    return "정보없음"
                if r < 0.9:
                    return "평균보다저렴"
                if r > 1.1:
                    return "평균보다비쌈"
                return "평균수준"

            df["자치구_월별_임대료수준_구간"] = df["자치구_월별_평균대비비율"].apply(level_cat)

        # 14. 자치구_용도_월별_임대료_평균 (자치구 건물용도별 월별 임대료 평균)
        print("14. 자치구_용도_월별_임대료_평균 생성 중...")

        for df in [df_train, df_test]:
            df["자치구_용도_월별_임대료_평균"] = (
                df
                .groupby(["자치구명", "건물용도", "연월"])["임대료(만원)"]
                .transform("mean")
            )

        # 15. 법정동_용도_월별_임대료_평균 (법정동 건물용도별 월별 임대료 평균)
        print("15. 법정동_용도_월별_임대료_평균 생성 중...")

        for df in [df_train, df_test]:
            df["법정동_용도_월별_임대료_평균"] = (
                df
                .groupby(["법정동명", "건물용도", "연월"])["임대료(만원)"]
                .transform("mean")
            )

        # # 15-1. 동용도_희소도_구간 생성 (동 내 용도별 매물 비율 기준)
        # print("15-1. 동용도_희소도_구간 생성 중...")

        # # 동 전체 매물 수, 동×용도 매물 수 (train 기준)
        # dong_total = df_train.groupby("법정동명").size().rename("동_전체매물수")
        # dong_usage = df_train.groupby(["법정동명", "건물용도"]).size().rename("동용도_매물수")

        # rarity_df = (
        #     dong_usage
        #     .reset_index()
        #     .merge(dong_total.reset_index(), on="법정동명", how="left")
        # )
        # rarity_df["동용도_비율"] = rarity_df["동용도_매물수"] / rarity_df["동_전체매물수"]

        # # 비율 기준 희소도 구간 (앞에서 확인한 thresholds 그대로 사용)
        # def rarity_label(p: float) -> str:
        #     if p <= 0.03:
        #         return "매우희소"
        #     if p <= 0.10:
        #         return "희소"
        #     if p <= 0.30:
        #         return "보통"
        #     if p <= 0.60:
        #         return "다수"
        #     return "과밀"

        # rarity_df["동용도_희소도_구간"] = rarity_df["동용도_비율"].apply(rarity_label)

        # # 매물 레벨로 매핑 (train/test 모두)
        # rarity_map = rarity_df.set_index(["법정동명", "건물용도"])["동용도_희소도_구간"]

        # for df in [df_train, df_test]:
        #     keys = list(zip(df["법정동명"], df["건물용도"]))
        #     df["동용도_희소도_구간"] = [rarity_map.get(k, "보통") for k in keys]

        # # 15-2. 동용도_공급국면 생성 (최근 매물 수 변화율 기준)
        # print("15-2. 동용도_공급국면 생성 중...")

        # # Train 기준 동×용도×연월별 매물 수 집계 (연월_dt는 이미 위에서 생성되어 있음)
        # monthly_cnt = (
        #     df_train
        #     .groupby(["법정동명", "건물용도", "연월", "연월_dt"])
        #     .size()
        #     .reset_index(name="매물수")
        # )

        # def label_supply_phase(g: pd.DataFrame, window: int = 3) -> pd.Series:
        #     g = g.sort_values("연월_dt")
        #     # 기본값: 안정기
        #     labels = ["안정기"] * len(g)

        #     if len(g) >= window * 2:
        #         recent_mean = g["매물수"].iloc[-window:].mean()
        #         prev_mean = g["매물수"].iloc[-window*2:-window].mean()

        #         if prev_mean == 0:
        #             if recent_mean == 0:
        #                 phase = "안정기"
        #             elif recent_mean <= 2:
        #                 phase = "공급증가 초기"
        #             else:
        #                 phase = "공급과잉기"
        #         else:
        #             growth = (recent_mean - prev_mean) / prev_mean
        #             if growth <= -0.3:
        #                 phase = "공급축소기"
        #             elif growth < 0.3:
        #                 phase = "안정기"
        #             elif growth < 1.0:
        #                 phase = "공급증가 초기"
        #             else:
        #                 phase = "공급과잉기"

        #         labels = [phase] * len(g)

        #     return pd.Series(labels, index=g.index)

        # monthly_cnt["동용도_공급국면"] = (
        #     monthly_cnt
        #     .groupby(["법정동명", "건물용도"], group_keys=False)
        #     .apply(label_supply_phase)
        # )

        # supply_map = monthly_cnt[["법정동명", "건물용도", "연월", "동용도_공급국면"]]

        # # 매물 레벨로 매핑 (train/test 모두)
        # for df in [df_train, df_test]:
        #     df = df.merge(
        #         supply_map,
        #         on=["법정동명", "건물용도", "연월"],
        #         how="left"
        #     )
        #     df["동용도_공급국면"] = df["동용도_공급국면"].fillna("안정기")
        #     if df is df_train:
        #         df_train = df
        #     else:
        #         df_test = df

        # 16. 보증금_지역대비 생성 (구별 평균 대비 비율)
        print("16. 보증금_지역대비 생성 중...")

        # 1) Train: 자치구별 평균 보증금(만원) 기준으로 비율 계산
        if self.gu_deposit_mean is None:
            self.gu_deposit_mean = df_train.groupby("자치구명")["보증금(만원)"].mean().to_dict()
        
        gu_deposit_mean_train = df_train["자치구명"].map(self.gu_deposit_mean)
        df_train["보증금_지역대비"] = df_train["보증금(만원)"] / gu_deposit_mean_train

        # 2) Test: Train에서 구한 자치구별 평균을 사용
        df_test["보증금_지역대비"] = df_test["보증금(만원)"] / df_test["자치구명"].map(self.gu_deposit_mean)

        # 매핑되지 않은 자치구(새로운 구 등)는 기본값 1.0으로 처리
        df_test["보증금_지역대비"] = df_test["보증금_지역대비"].fillna(1.0)


        # 16. Label Encoding 적용
        print("16. Label Encoding 적용 중...")
        cat_cols_for_le = ["자치구명", "법정동명", "자치구_건물용도"]

        for col in cat_cols_for_le:
            le = LabelEncoder()

            # train과 test를 합쳐서 모든 카테고리로 학습
            all_vals = pd.concat([df_train[col], df_test[col]]).astype(str)
            le.fit(all_vals)

            df_train[col + "_LE"] = le.transform(df_train[col].astype(str))
            df_test[col + "_LE"] = le.transform(df_test[col].astype(str))

            # LabelEncoder 저장
            self.label_encoders[col] = le

        for df in [df_train, df_test]:
            # 1. 중요 Feature 간 곱셈 교호작용
            df["면적_x_건축연차"] = df["임대면적"] * df["건축연차"]
            df["자치구거래량_x_면적"] = df["자치구_거래량"] * df["임대면적"]

            # 2. 금리와 지역의 교호작용
            df["자치구_x_금리평균"] = df["자치구명_LE"] * df["금리_평균"]

            # 3. 계절 × 자치구 (계절별 지역 선호도)
            # df["계절_x_자치구"] = (
            #     df["계약_계절"].astype(str) + "_" + df["자치구명"].astype(str)
            # )

        # 17. 최종 피처 선택
        print("17. 최종 피처 선택 중...")
        self.candidate_features = [
            "자치구명_LE",
            "법정동명_LE",
            "자치구_건물용도_LE",
            "건물용도",
            "임대면적",
            "면적_qcat",
            "구_권역",
            # "분기_라벨",
            # "계약_계절",
            # "계약_반기",
            # "층_bin",
            "층",
            "건축연차",
            "건축시대",
            # "자치구_거래량_구간",
            # "보증금_구간",
            # "임대료_구간",
            "보증금임대료비율_구간",
            # "기준금리_레벨",
            # "소비자물가_레벨",
            # "KORIBOR_스프레드_구간",
            # "금리_국면",
            # "금리_z_구간",
            # "전용면적_자치구수준_z",
            # "건축연도_자치구수준_z",
            # "층수_자치구수준_z",
            "KORIBOR",
            "기업대출",
            # "전세자금대출",
            # "CD",
            # "무담보콜금리",
            # "변동형주택담보대출",
            # "소비자물가",
            # "기준금리_전월대비_범주",
            "자치구_월별_임대료수준_구간",
            "자치구_용도_월별_임대료_평균",
            "법정동_용도_월별_임대료_평균",
            # "동용도_희소도_구간",
            # "동용도_공급국면",
            "면적_x_건축연차",
            "자치구거래량_x_면적",
            # "자치구_x_금리평균",
            # "계절_x_자치구",
            "보증금_지역대비",
        ]

        # 실제 존재하는 컬럼만 필터링
        self.candidate_features = [c for c in self.candidate_features if c in df_train.columns]

        print("\n✅ Feature Engineering 완료!")
        print(f"   - 총 피처 수: {len(self.candidate_features)}개")
        print(f"\n사용된 피처 목록:")
        for i, feat in enumerate(self.candidate_features, 1):
            print(f"   {i:2d}. {feat}")
        print("=" * 60 + "\n")

        return df_train, df_test

    def feature_engineering(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        피처 엔지니어링 (Label Encoding)

        Args:
            train_df: 학습 데이터
            test_df: 테스트 데이터

        Returns:
            (전처리된 train_df, 전처리된 test_df)
        """
        df_train = train_df.copy()
        df_test = test_df.copy()

        # 복합 카테고리 생성
        df_train["자치구_건물용도"] = df_train["자치구명"] + "_" + df_train["건물용도"]
        df_test["자치구_건물용도"] = df_test["자치구명"] + "_" + df_test["건물용도"]

        # Label Encoding 적용
        cat_cols_for_le = ["자치구명", "법정동명", "자치구_건물용도"]

        for col in cat_cols_for_le:
            le = LabelEncoder()

            # train과 test를 합쳐서 모든 카테고리로 학습
            all_vals = pd.concat([df_train[col], df_test[col]]).astype(str)
            le.fit(all_vals)

            df_train[col + "_LE"] = le.transform(df_train[col].astype(str))
            df_test[col + "_LE"] = le.transform(df_test[col].astype(str))

            # LabelEncoder 저장
            self.label_encoders[col] = le

        # 최종 피처 선택
        self.candidate_features = [
            "자치구명_LE", "법정동명_LE",
            "자치구_건물용도_LE",
            "건물연식",
            "건물용도",
            "층",
            "임대면적",
            "KORIBOR", "기업대출", "전세자금대출",
            "CD", "무담보콜금리",
            "변동형주택담보대출",
            "소비자물가",
        ]

        # 실제 존재하는 컬럼만 필터링
        self.candidate_features = [c for c in self.candidate_features if c in df_train.columns]

        return df_train, df_test

    def prepare_train_test_split(
        self,
        df_train: pd.DataFrame,
        split_date: str = "2025-06"
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        시계열 기반 Train/Val 분할

        Args:
            df_train: 전체 학습 데이터
            split_date: 검증 데이터 시작 날짜

        Returns:
            (X_train, y_train, X_val, y_val)
        """
        # 타깃이 없는 행 제거 및 정렬
        df_train_ml = df_train.dropna(subset=[self.target_name]).copy()
        df_train_ml = df_train_ml.sort_values("연월").reset_index(drop=True)

        # 날짜 기준 분할
        train_mask = df_train_ml["연월"] < split_date
        val_mask = (df_train_ml["연월"] >= split_date) & (df_train_ml["연월"] < "2025-09")

        train_data = df_train_ml[train_mask]
        val_data = df_train_ml[val_mask]

        X_train = train_data[self.candidate_features]
        y_train = train_data[self.target_name]

        X_val = val_data[self.candidate_features]
        y_val = val_data[self.target_name]

        print(f"\n✅ 시계열 기반 Train/Val Split 완료:")
        print(f"   - Train: {len(X_train):,}개 ({len(X_train) / len(df_train_ml) * 100:.1f}%)")
        print(f"   - Val:   {len(X_val):,}개 ({len(X_val) / len(df_train_ml) * 100:.1f}%)")
        print(f"   - Train 기간: {train_data['연월'].min()} ~ {train_data['연월'].max()}")
        print(f"   - Val 기간:   {val_data['연월'].min()} ~ {val_data['연월'].max()}")

        # 클래스 분포 출력
        print(f"\n📊 클래스 분포:")
        print(f"   [Train]")
        for class_id, info in self.class_labels.items():
            count = (y_train == class_id).sum()
            pct = count / len(y_train) * 100
            print(f"      - {info['label_kr']} ({info['label']}): {count:,}개 ({pct:.1f}%)")
        print(f"   [Val]")
        for class_id, info in self.class_labels.items():
            count = (y_val == class_id).sum()
            pct = count / len(y_val) * 100
            print(f"      - {info['label_kr']} ({info['label']}): {count:,}개 ({pct:.1f}%)")

        return X_train, y_train, X_val, y_val

    def get_preprocessor(self, X_train: pd.DataFrame) -> ColumnTransformer:
        """
        전처리 파이프라인 생성 (OneHotEncoding 사용)

        ⚠️ 주의: Tree 모델에는 비효율적! get_tree_preprocessor() 사용 권장

        Args:
            X_train: 학습 데이터

        Returns:
            ColumnTransformer
        """
        # 숫자/범주 피처 분리
        numeric_features = X_train.select_dtypes(include=[np.number]).columns.tolist()
        categorical_features = [c for c in X_train.columns if c not in numeric_features]

        print(f"\n📊 피처 타입:")
        print(f"   - 수치형: {len(numeric_features)}개 - {numeric_features}")
        print(f"   - 범주형: {len(categorical_features)}개 - {categorical_features}")

        # 전처리 파이프라인
        self.preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), numeric_features),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
            ]
        )

        return self.preprocessor

    def get_tree_preprocessor(self, X_train: pd.DataFrame):
        """
        Tree 모델용 전처리 파이프라인 (Label Encoding + No Scaling)

        Tree 기반 모델(XGBoost, LightGBM)에 최적화된 전처리:
        - 범주형 변수: Label Encoding (이미 적용됨)
        - 수치형 변수: 스케일링 없음 (Tree 모델은 스케일 불변)

        Args:
            X_train: 학습 데이터

        Returns:
            None (전처리 없이 데이터 그대로 사용)
        """
        # 범주형 변수를 Label Encoding으로 변환
        categorical_features = X_train.select_dtypes(include=['object', 'category']).columns.tolist()

        print(f"\n🌳 Tree 모델용 전처리:")
        print(f"   - 범주형 변수를 Label Encoding으로 변환")
        print(f"   - 스케일링 없음 (Tree 모델은 스케일 불변)")

        if len(categorical_features) > 0:
            print(f"\n📋 범주형 변수 ({len(categorical_features)}개):")
            for feat in categorical_features:
                print(f"   - {feat}")

        # Tree 모델용으로는 전처리 파이프라인을 None으로 설정
        # (범주형 변수는 이미 Label Encoding되어 있음)
        self.preprocessor = None

        return None

    def prepare_tree_features(
        self,
        X_train: pd.DataFrame,
        X_val: pd.DataFrame,
        X_test: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Tree 모델용 피처 준비 (범주형 변수를 Label Encoding으로 변환)

        Args:
            X_train: 학습 데이터
            X_val: 검증 데이터
            X_test: 테스트 데이터

        Returns:
            (변환된 X_train, 변환된 X_val, 변환된 X_test)
        """
        print("\n🔧 Tree 모델용 피처 변환 중...")

        X_train_tree = X_train.copy()
        X_val_tree = X_val.copy()
        X_test_tree = X_test.copy()

        # 범주형 변수를 Label Encoding으로 변환
        categorical_cols = X_train.select_dtypes(include=['object', 'category']).columns.tolist()

        if len(categorical_cols) > 0:
            print(f"   - 범주형 변수 {len(categorical_cols)}개를 Label Encoding으로 변환")

            for col in categorical_cols:
                if col not in self.label_encoders:
                    # 새로운 LabelEncoder 생성
                    le = LabelEncoder()

                    # train, val, test를 합쳐서 모든 카테고리로 학습
                    all_vals = pd.concat([
                        X_train_tree[col],
                        X_val_tree[col],
                        X_test_tree[col]
                    ]).astype(str)
                    le.fit(all_vals)

                    self.label_encoders[col] = le
                else:
                    le = self.label_encoders[col]

                # 변환
                X_train_tree[col] = le.transform(X_train_tree[col].astype(str))
                X_val_tree[col] = le.transform(X_val_tree[col].astype(str))
                X_test_tree[col] = le.transform(X_test_tree[col].astype(str))

        print(f"\n✅ 변환 완료:")
        print(f"   - Train: {X_train_tree.shape}")
        print(f"   - Val:   {X_val_tree.shape}")
        print(f"   - Test:  {X_test_tree.shape}")

        return X_train_tree, X_val_tree, X_test_tree

    def transform_features(
        self,
        X_train: pd.DataFrame,
        X_val: pd.DataFrame,
        X_test: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        피처 변환 적용

        Args:
            X_train: 학습 데이터
            X_val: 검증 데이터
            X_test: 테스트 데이터

        Returns:
            (변환된 X_train, 변환된 X_val, 변환된 X_test)
        """
        if self.preprocessor is None:
            raise ValueError("먼저 get_preprocessor()를 호출하여 전처리기를 생성하세요.")

        print("\n🔧 데이터 전처리 중...")
        X_train_transformed = self.preprocessor.fit_transform(X_train)
        X_val_transformed = self.preprocessor.transform(X_val)
        X_test_transformed = self.preprocessor.transform(X_test)

        print(f"   - Train shape: {X_train_transformed.shape}")
        print(f"   - Val shape:   {X_val_transformed.shape}")
        print(f"   - Test shape:  {X_test_transformed.shape}")

        return X_train_transformed, X_val_transformed, X_test_transformed

    def transform(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        추론용 데이터 변환 (학습 시 저장된 통계 사용)
        
        Args:
            df: 원본 데이터프레임
            
        Returns:
            (변환된 피처 데이터프레임 X, 계산된 컬럼이 포함된 데이터프레임 df_proc)
        """
        # 1. 타깃 생성 (통계만 계산하고 타깃 컬럼은 무시)
        df_proc = self.create_target(df, train_stats={"gu_quantiles": self.train_gu_quantiles})
        
        # 2. 고급 피처 엔지니어링 (Test 모드로 실행)
        # 빈 데이터프레임을 train으로 전달하여 self에 저장된 bins 등을 사용하게 함
        _, df_proc = self.advanced_feature_engineering(df_proc.iloc[:0], df_proc)
        
        # 3. Tree 모델용 피처 변환
        # 빈 데이터프레임을 train/val로 전달하여 self에 저장된 label_encoders를 사용하게 함
        _, _, df_proc_tree = self.prepare_tree_features(df_proc.iloc[:0], df_proc.iloc[:0], df_proc)
        
        # 4. 최종 피처 선택
        X = df_proc_tree[self.candidate_features]
        
        return X, df_proc

