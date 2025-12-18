"""
모델 검증 분석
- 혼동 행렬 (Confusion Matrix)
- 피처-타겟 상관관계 히트맵
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
from pathlib import Path
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import learning_curve
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 파일 경로
TEMP_MODEL_PATH = "apps/reco/models/trust_model/save_models/temp_trained_models.pkl"
TRAIN_TARGET_PATH = "data/ML/trust/train_target.csv"
TEST_TARGET_PATH = "data/ML/trust/test_target.csv"


class ModelValidationAnalyzer:
    """모델 검증 분석 클래스"""
    
    def __init__(self):
        self.results_dir = Path("apps/reco/models/trust_model/results/validation")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 데이터 로드
        self.load_data()
    
    def load_data(self):
        """모델과 데이터 로드"""
        print("📂 데이터 로드 중...")
        
        # 모델 로드
        with open(TEMP_MODEL_PATH, "rb") as f:
            temp_data = pickle.load(f)
        
        self.model = temp_data["models"]["LogisticRegression"]
        self.X_test = temp_data["X_test_scaled"]
        self.y_test = temp_data["y_test"]
        self.feature_names = temp_data["feature_names"]
        
        # 피처 데이터 로드 (상관관계 분석용)
        # X_train, X_test (피처가 생성된 데이터)와 y_train, y_test (타겟) 로드
        X_train = pd.read_csv("data/ML/trust/X_train.csv", encoding="utf-8-sig")
        X_test = pd.read_csv("data/ML/trust/X_test.csv", encoding="utf-8-sig")
        y_train = pd.read_csv("data/ML/trust/y_train.csv", encoding="utf-8-sig").squeeze()
        # 피처 데이터 로드 (X_train, X_test, y_train, y_test)
        X_train = pd.read_csv("data/ML/trust/X_train.csv", encoding="utf-8-sig")
        X_test = pd.read_csv("data/ML/trust/X_test.csv", encoding="utf-8-sig")
        y_train = pd.read_csv("data/ML/trust/y_train.csv", encoding="utf-8-sig").squeeze()
        y_test = pd.read_csv("data/ML/trust/y_test.csv", encoding="utf-8-sig").squeeze()

        # [수정] 학습에 사용된 14개 피처 명시 (Leakage 방지 및 정합성 보장)
        # _02_create_features.py의 select_features와 일치해야 함
        valid_features = [
            "등록매물_log", "총거래활동량_log", "1인당_거래량_log", 
            "총_직원수", "중개보조원_비율", "자격증_보유비율", 
            "운영기간_년", "숙련도_지수", "운영_안정성", 
            "대형사무소", "대표_공인중개사", "대표_법인", 
            "지역_경쟁강도", "1층_여부"
        ]
        
        # 교집합으로 유효 피처만 선택 (안전장치)
        # 실제 저장된 파일 컬럼과 비교
        final_features = [col for col in valid_features if col in X_train.columns]
        
        X_train = X_train[final_features]
        X_test = X_test[final_features]
        
        # Train 데이터 결합
        df_train_combined = X_train.copy()
        df_train_combined['Target'] = y_train.values
        
        # Test 데이터 결합
        df_test_combined = X_test.copy()
        df_test_combined['Target'] = y_test.values
        
        # 전체 데이터 합치기
        self.df_features = pd.concat([df_train_combined, df_test_combined], ignore_index=True)
        self.feature_names = final_features
        
        print(f"   ✅ 모델 로드 완료")
        print(f"   ✅ 테스트 데이터: {len(self.X_test)}개")
        print(f"   ✅ 사용된 피처 수: {len(self.feature_names)}개")
        print(f"   ✅ 피처 목록: {self.feature_names}")
        print(f"   ✅ 전체 데이터: {len(self.df_features)}개")
    
    def analyze_all(self):
        """전체 분석 실행"""
        print("\n" + "=" * 70)
        print("🔍 모델 검증 분석 시작")
        print("=" * 70)
        
        # 1. 혼동 행렬
        self.plot_confusion_matrix()
        
        # 2. 피처-타겟 상관관계 히트맵
        self.plot_feature_target_correlation()
        
        # 3. 운영기간 분포 분석
        self.plot_operational_period_distribution()
        
        # 4. 대표자 구분 비율 분석
        self.plot_representative_distribution()
        
        # 5. 학습 곡선 (Learning Curve)
        self.plot_learning_curve()
        
        print("\n" + "=" * 70)
        print("✅ 모델 검증 분석 완료!")
        print("=" * 70)
        print(f"\n📁 결과 저장 위치: {self.results_dir}")
    
    def plot_confusion_matrix(self):
        """혼동 행렬 시각화"""
        print("\n📊 [1/2] 혼동 행렬 생성 중...")
        
        # 예측
        y_pred = self.model.predict(self.X_test)
        
        # 혼동 행렬 계산
        cm = confusion_matrix(self.y_test, y_pred)
        labels = sorted(self.y_test.unique())
        
        # 시각화
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=labels, yticklabels=labels,
                    cbar_kws={'label': '건수'})
        
        plt.title('혼동 행렬 (Confusion Matrix)', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('예측 등급', fontsize=13, fontweight='bold')
        plt.ylabel('실제 등급', fontsize=13, fontweight='bold')
        
        # 정확도 표시
        accuracy = np.trace(cm) / np.sum(cm)
        plt.text(0.5, -0.15, f'전체 정확도: {accuracy:.2%}', 
                ha='center', transform=plt.gca().transAxes, 
                fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        output_path = self.results_dir / "01_confusion_matrix.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ 저장: {output_path}")
        plt.close()
    
    def plot_feature_target_correlation(self):
        """피처-타겟 상관관계 히트맵"""
        print("\n📊 [2/2] 피처-타겟 상관관계 히트맵 생성 중...")
        
        # 타겟을 숫자로 변환 (0, 1, 2)
        # 이미 Target은 0, 1, 2로 저장되어 있음
        if 'Target' not in self.df_features.columns:
            print("   ⚠️  Target 컬럼이 없습니다. 분석을 건너뜩니다.")
            return
        
        # 피처와 타겟 선택
        feature_cols = self.feature_names
        correlation_data = self.df_features[feature_cols + ['Target']].copy()
        
        # 상관계수 계산
        correlation_matrix = correlation_data.corr()
        
        # 타겟과의 상관계수만 추출
        target_correlation = correlation_matrix['Target'].drop('Target').sort_values(ascending=False)
        
        # 시각화 1: 막대 그래프
        plt.figure(figsize=(12, 10))
        colors = ['green' if x > 0 else 'red' for x in target_correlation.values]
        plt.barh(range(len(target_correlation)), target_correlation.values, color=colors, alpha=0.7)
        plt.yticks(range(len(target_correlation)), target_correlation.index)
        plt.xlabel('상관계수 (Correlation)', fontsize=13, fontweight='bold')
        plt.ylabel('피처', fontsize=13, fontweight='bold')
        plt.title('피처-신뢰도등급 상관관계 (A=2, B=1, C=0)', fontsize=16, fontweight='bold', pad=20)
        plt.axvline(x=0, color='black', linestyle='--', linewidth=1)
        plt.grid(axis='x', alpha=0.3)
        
        # 값 표시
        for i, v in enumerate(target_correlation.values):
            plt.text(v, i, f' {v:.3f}', va='center', fontsize=9)
        
        plt.tight_layout()
        
        output_path = self.results_dir / "02_feature_target_correlation_bar.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ 저장: {output_path}")
        plt.close()
        
        # 시각화 2: 히트맵 (전체 상관관계)
        plt.figure(figsize=(16, 14))
        
        # 타겟 컬럼을 맨 아래로 이동
        cols_order = feature_cols + ['Target']
        corr_reordered = correlation_matrix.loc[cols_order, cols_order]
        
        sns.heatmap(corr_reordered, annot=True, fmt='.2f', cmap='coolwarm', 
                    center=0, vmin=-1, vmax=1,
                    square=True, linewidths=0.5,
                    cbar_kws={'label': '상관계수'})
        
        plt.title('피처 간 상관관계 히트맵 (신뢰도등급 포함)', fontsize=16, fontweight='bold', pad=20)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        
        plt.tight_layout()
        
        output_path = self.results_dir / "03_feature_correlation_heatmap.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ 저장: {output_path}")
        plt.close()
        
        # 상관계수 출력
        print("\n   📋 피처-신뢰도등급 상관계수 (상위 10개):")
        for i, (feature, corr) in enumerate(target_correlation.head(10).items(), 1):
            print(f"      {i:2d}. {feature:30s}: {corr:+.4f}")
    
    def plot_operational_period_distribution(self):
        """운영기간 분포 분석"""
        print("\n📊 [3/3] 운영기간 분포 분석 중...")
        
        # 운영기간_년 데이터 로드 (원본 데이터에서 - 등록일 정보 필요)
        df_train_orig = pd.read_csv(TRAIN_TARGET_PATH, encoding="utf-8-sig")
        df_test_orig = pd.read_csv(TEST_TARGET_PATH, encoding="utf-8-sig")
        df_target = pd.concat([df_train_orig, df_test_orig], ignore_index=True)
        
        # 운영기간 계산
        df_target['등록일'] = pd.to_datetime(df_target['등록일'], errors='coerce')
        today = pd.Timestamp.now()
        df_target['운영기간_일'] = (today - df_target['등록일']).dt.days.clip(lower=0)
        df_target['운영기간_년'] = (df_target['운영기간_일'] / 365.25).fillna(0)
        
        operational_years = df_target['운영기간_년'].dropna()
        
        # 통계 계산
        median_years = operational_years.median()
        mean_years = operational_years.mean()
        std_years = operational_years.std()
        
        # 3년 기준 비율
        stable_ratio = (operational_years >= 3).sum() / len(operational_years)
        
        print(f"\n   📊 운영기간 통계:")
        print(f"      - 평균: {mean_years:.2f}년")
        print(f"      - 중앙값: {median_years:.2f}년")
        print(f"      - 표준편차: {std_years:.2f}년")
        print(f"      - 3년 이상 비율: {stable_ratio:.1%}")
        
        # 시각화
        fig, axes = plt.subplots(2, 1, figsize=(14, 12))
        
        # 1. 히스토그램
        ax1 = axes[0]
        ax1.hist(operational_years, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
        ax1.axvline(3, color='red', linestyle='--', linewidth=2, label=f'3년 기준 (안정성)')
        ax1.axvline(median_years, color='green', linestyle='--', linewidth=2, label=f'중앙값: {median_years:.1f}년')
        ax1.axvline(mean_years, color='orange', linestyle='--', linewidth=2, label=f'평균: {mean_years:.1f}년')
        
        ax1.set_xlabel('운영기간 (년)', fontsize=13, fontweight='bold')
        ax1.set_ylabel('중개사무소 수', fontsize=13, fontweight='bold')
        ax1.set_title('중개사무소 운영기간 분포', fontsize=16, fontweight='bold', pad=20)
        ax1.legend(fontsize=11)
        ax1.grid(alpha=0.3)
        
        # 통계 정보 텍스트 박스
        stats_text = f'총 {len(operational_years)}개 사무소\n'
        stats_text += f'3년 이상: {(operational_years >= 3).sum()}개 ({stable_ratio:.1%})\n'
        stats_text += f'3년 미만: {(operational_years < 3).sum()}개 ({1-stable_ratio:.1%})'
        ax1.text(0.98, 0.97, stats_text, transform=ax1.transAxes,
                fontsize=11, verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 2. 등급별 박스플롯
        ax2 = axes[1]
        
        # 등급별 데이터 준비
        df_with_grade = df_target[['운영기간_년', 'Target']].dropna()
        grade_order = [0, 1, 2]  # C, B, A
        grade_labels = ['C', 'B', 'A']
        
        # 박스플롯
        box_data = [df_with_grade[df_with_grade['Target'] == grade]['운영기간_년'].values 
                    for grade in grade_order]
        
        bp = ax2.boxplot(box_data, labels=grade_labels, patch_artist=True,
                        widths=0.6, showmeans=True,
                        meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
        
        # 색상 설정
        colors = ['#ff9999', '#ffcc99', '#99ff99']  # C, B, A
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax2.axhline(3, color='red', linestyle='--', linewidth=2, label='3년 기준 (안정성)')
        ax2.set_xlabel('신뢰도 등급', fontsize=13, fontweight='bold')
        ax2.set_ylabel('운영기간 (년)', fontsize=13, fontweight='bold')
        ax2.set_title('신뢰도 등급별 운영기간 분포', fontsize=16, fontweight='bold', pad=20)
        ax2.legend(fontsize=11)
        ax2.grid(alpha=0.3, axis='y')
        
        # 등급별 평균 표시
        for i, (grade, label) in enumerate(zip(grade_order, grade_labels), 1):
            grade_mean = df_with_grade[df_with_grade['Target'] == grade]['운영기간_년'].mean()
            ax2.text(i, grade_mean, f'{grade_mean:.1f}년', 
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.tight_layout()
        
        output_path = self.results_dir / "04_operational_period_distribution.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ 저장: {output_path}")
        plt.close()
    
    def plot_representative_distribution(self):
        """대표자 구분 비율 분석"""
        print("\n📊 [4/4] 대표자 구분 비율 분석 중...")
        
        # 타겟 데이터 로드 (대표자구분명 정보 필요)
        df_train_orig = pd.read_csv(TRAIN_TARGET_PATH, encoding="utf-8-sig")
        df_test_orig = pd.read_csv(TEST_TARGET_PATH, encoding="utf-8-sig")
        df_target = pd.concat([df_train_orig, df_test_orig], ignore_index=True)
        
        # 대표자구분명 분포 계산
        rep_counts = df_target['대표자구분명'].value_counts()
        rep_percentages = df_target['대표자구분명'].value_counts(normalize=True) * 100
        
        # 통계 출력
        print(f"\n   📊 대표자 구분 통계:")
        for rep_type in rep_counts.index:
            count = rep_counts[rep_type]
            percentage = rep_percentages[rep_type]
            print(f"      - {rep_type}: {count}개 ({percentage:.1f}%)")
        
        # 시각화
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        
        # 1. 파이 차트
        colors = ['#66b3ff', '#99ff99', '#ffcc99', '#ff9999']
        wedges, texts, autotexts = ax1.pie(
            rep_counts.values,
            labels=rep_counts.index,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90,
            textprops={'fontsize': 12, 'fontweight': 'bold'}
        )
        
        # 파이 차트 스타일
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(14)
            autotext.set_fontweight('bold')
        
        ax1.set_title('대표자 구분 비율', fontsize=16, fontweight='bold', pad=20)
        
        # 2. 막대 그래프 (가중치 포함)
        weights = {
            '공인중개사': 0.0,
            '법인': 0.2,
            '중개인': -0.3,
            '중개보조원': -0.1
        }
        
        # 데이터 정렬 (가중치 순)
        sorted_reps = sorted(rep_counts.index, key=lambda x: weights.get(x, 0), reverse=True)
        sorted_counts = [rep_counts[rep] for rep in sorted_reps]
        sorted_weights = [weights.get(rep, 0) for rep in sorted_reps]
        
        # 막대 색상 (가중치에 따라)
        bar_colors = ['green' if w > 0 else 'gray' if w == 0 else 'red' for w in sorted_weights]
        
        bars = ax2.bar(range(len(sorted_reps)), sorted_counts, color=bar_colors, alpha=0.7, edgecolor='black')
        ax2.set_xticks(range(len(sorted_reps)))
        ax2.set_xticklabels(sorted_reps, fontsize=11, fontweight='bold')
        ax2.set_ylabel('중개사무소 수', fontsize=13, fontweight='bold')
        ax2.set_title('대표자 구분별 개수 및 가중치', fontsize=16, fontweight='bold', pad=20)
        ax2.grid(axis='y', alpha=0.3)
        
        # 막대 위에 개수와 가중치 표시
        for i, (bar, count, weight) in enumerate(zip(bars, sorted_counts, sorted_weights)):
            height = bar.get_height()
            # 개수 표시
            ax2.text(bar.get_x() + bar.get_width()/2, height,
                    f'{count}개\n({rep_percentages[sorted_reps[i]]:.1f}%)',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
            # 가중치 표시
            weight_text = f'가중치: {weight:+.1f}' if weight != 0 else '기준 (0.0)'
            weight_color = 'green' if weight > 0 else 'gray' if weight == 0 else 'red'
            ax2.text(bar.get_x() + bar.get_width()/2, height * 0.5,
                    weight_text,
                    ha='center', va='center', fontsize=9, fontweight='bold',
                    color=weight_color,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        
        output_path = self.results_dir / "05_representative_distribution.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ 저장: {output_path}")
        plt.close()

    def plot_learning_curve(self):
        """학습 곡선 (Learning Curve) 시각화"""
        print("\n📊 [5/5] 학습 곡선 생성 중...")
        
        # 최신 모델 설정 (사용자 요청 반영: C=1, penalty='l1', solver='saga')
        best_model = LogisticRegression(
            C=1, 
            penalty='l1', 
            solver='saga', 
            class_weight='balanced', 
            max_iter=1000, 
            random_state=42
        )
        
        # 파이프라인 구성
        pipeline_steps = [
            ('imputer', SimpleImputer(strategy='mean')),
            ('scaler', StandardScaler()),
            ('clf', best_model)
        ]
        pipeline = Pipeline(pipeline_steps)
        
        # 데이터 준비 (전체 데이터 사용)
        if 'Target' in self.df_features.columns:
            target_col = 'Target'
            feature_cols = [c for c in self.df_features.columns if c != target_col]
            X = self.df_features[feature_cols]
            y = self.df_features[target_col]
        else:
            print("   ⚠️  Target 컬럼 부재로 학습 곡선 생성을 건너뜁니다.")
            return

        # Learning Curve 계산
        train_sizes, train_scores, test_scores = learning_curve(
            pipeline, X, y, cv=5, scoring='accuracy', n_jobs=-1, 
            train_sizes=np.linspace(0.1, 1.0, 10), shuffle=True, random_state=42
        )

        # 평균 및 표준편차 계산
        train_mean = np.mean(train_scores, axis=1)
        train_std = np.std(train_scores, axis=1)
        test_mean = np.mean(test_scores, axis=1)
        test_std = np.std(test_scores, axis=1)

        # 시각화
        plt.figure(figsize=(10, 6))
        plt.plot(train_sizes, train_mean, 'o-', color="r", label="Train score")
        plt.plot(train_sizes, test_mean, 'o-', color="g", label="Cross-validation score")
        plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color="r")
        plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.1, color="g")

        plt.title("학습 곡선 (Learning Curve)", fontsize=15, fontweight='bold')
        plt.xlabel("학습 데이터 샘플 수", fontsize=12)
        plt.ylabel("정확도 (Accuracy)", fontsize=12)
        plt.legend(loc="best")
        plt.grid(True, linestyle='--', alpha=0.6)
        
        output_path = self.results_dir / "06_learning_curve.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"   ✅ 저장: {output_path}")
        plt.close()
        
        print("   ➕ 해석 Point: Train(Red)과 CV(Green) 곡선이 서로 비슷한 높이로 수렴해야 과적합이 없는 것입니다.")




def main():
    """메인 실행 함수"""
    analyzer = ModelValidationAnalyzer()
    analyzer.analyze_all()


if __name__ == "__main__":
    main()