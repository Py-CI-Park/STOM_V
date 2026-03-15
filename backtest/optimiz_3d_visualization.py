
import matplotlib.pyplot as plt
from utility.lazy_imports import get_np
from utility.setting_base import GRAPH_PATH


class Visualization3D:
    def __init__(self):
        self.top_3_params = None
        self.optimization_3d_history = []

    def update_3d_visualization(self, dict_turn_hvar_hstd, k):
        """
        dict_turn_hvar_hstd 데이터를 활용한 3D 최적화 진화 시각화

        Args:
            dict_turn_hvar_hstd: {파라미터인덱스: [최적값, 최고기준값]}
            k: 현재 최적화 단계
        """
        current_data = {
            'step': k,
            'params': dict_turn_hvar_hstd
        }
        self.optimization_3d_history.append(current_data)

    def plot_3d_visualization(self, schedul, save_file_name):
        if len(self.optimization_3d_history) < 3:
            return

        # 3D 시각화 생성
        fig = plt.figure(figsize=(18, 12))
        fig.suptitle(f'최적화 진화 3D 분석', fontsize=16, fontweight='bold')

        # 1. 파라미터 진화 3D 라인 플롯
        ax1 = fig.add_subplot(2, 3, 1, projection='3d')
        self._plot_param_evolution_3d(ax1)

        # 2. 최적값 변화 3D 서피스
        ax2 = fig.add_subplot(2, 3, 2, projection='3d')
        self._plot_optimal_value_surface(ax2)

        # 3. 파라미터 상관관계 3D 산점도
        ax3 = fig.add_subplot(2, 3, 3, projection='3d')
        self._plot_param_correlation_3d(ax3)

        # 4. 수렴 패턴 2D 히트맵
        ax4 = fig.add_subplot(2, 3, 4)
        self._plot_convergence_heatmap(ax4)

        # 5. 파라미터 민감도 진화
        ax5 = fig.add_subplot(2, 3, 5)
        self._plot_sensitivity_evolution(ax5)

        # 6. 최적화 효율성 분석
        ax6 = fig.add_subplot(2, 3, 6)
        self._plot_optimization_efficiency(ax6)

        plt.tight_layout()

        # 저장
        save_path = f"{GRAPH_PATH}/{save_file_name}.png"
        plt.savefig(save_path, dpi=150, bbox_inches='tight')

        if not schedul:
            plt.show()

    def _plot_param_evolution_3d(self, ax):
        """파라미터 진화 3D 라인 플롯"""

        # 파라미터별 진화 궤적 추출
        param_evolution = {}
        n_params = len(self.optimization_3d_history[0]['params'])

        for i in range(n_params):
            param_evolution[i] = {
                'steps': [],
                'values': [],
                'scores': []
            }

        for history in self.optimization_3d_history:
            step = history['step']
            for param_idx, (optimal_value, score) in history['params'].items():
                param_evolution[param_idx]['steps'].append(step)
                param_evolution[param_idx]['values'].append(optimal_value)
                param_evolution[param_idx]['scores'].append(score)

        # 3D 라인 플롯 생성
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
        param_names = ['파라미터1', '파라미터2', '파라미터3', '파라미터4', '파라미터5']

        for i, evolution in param_evolution.items():
            if len(evolution['steps']) > 1:
                # X: 단계, Y: 파라미터값, Z: 최적화 점수
                ax.plot(evolution['steps'], evolution['values'], evolution['scores'],
                        linewidth=3, marker='o', markersize=6,
                        label=param_names[i], color=colors[i % len(colors)])

                # 최신 지점 강조
                ax.scatter([evolution['steps'][-1]], [evolution['values'][-1]],
                           [evolution['scores'][-1]], s=100, c=colors[i % len(colors)],
                           edgecolors='black', linewidth=2)

        ax.set_xlabel('최적화 단계')
        ax.set_ylabel('파라미터 최적값')
        ax.set_zlabel('최적화 기준값')
        ax.set_title('파라미터 진화 궤적 (3D)')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

    def _get_top_score_variance_params(self, n):
        """
        스코어 변화량이 가장 큰 파라미터 인덱스들을 반환

        Args:
            n: 반환할 파라미터 개수

        Returns:
            list: 스코어 변화량이 큰 파라미터 인덱스 리스트 (내림차순)
        """

        # 파라미터별 스코어 변화량 계산
        param_variances = {}

        # 첫 번째 히스토리에서 파라미터 인덱스 추출
        first_params = self.optimization_3d_history[0]['params']

        for param_idx in first_params.keys():
            scores = []
            for history in self.optimization_3d_history:
                if param_idx in history['params']:
                    scores.append(history['params'][param_idx][1])  # 스코어 값

            if len(scores) > 1:
                # 스코어의 분산 계산 (변화량 측정)
                variance = get_np().var(scores)
                param_variances[param_idx] = variance

        # 분산이 큰 순서대로 정렬하여 상위 n개 반환
        sorted_params = sorted(param_variances.items(), key=lambda x: x[1], reverse=True)
        return [param_idx for param_idx, _ in sorted_params[:n]]

    def _plot_optimal_value_surface(self, ax):
        """최적값 변화 3D 서피스"""

        # 스코어 변화량이 가장 큰 파라미터 3개 구하기
        self.top_3_params = self._get_top_score_variance_params(3)
        param1_idx, param2_idx = self.top_3_params[0], self.top_3_params[1]

        # 선택된 파라미터로 데이터 수집
        history_data = []
        for history in self.optimization_3d_history:
            params = dict(history['params'])
            if param1_idx in params and param2_idx in params:
                param1_val = params[param1_idx][0]  # 첫 번째 선택 파라미터 최적값
                param2_val = params[param2_idx][0]  # 두 번째 선택 파라미터 최적값
                score = params[param1_idx][1]  # 최적화 기준값
                history_data.append([param1_val, param2_val, score])

        if len(history_data) < 3:
            return

        history_data = get_np().array(history_data)

        # 보간을 위한 그리드 생성
        from scipy.interpolate import griddata

        xi = get_np().linspace(history_data[:, 0].min(), history_data[:, 0].max(), 20)
        yi = get_np().linspace(history_data[:, 1].min(), history_data[:, 1].max(), 20)
        X, Y = get_np().meshgrid(xi, yi)

        # Z 값 보간
        # noinspection PyTypeChecker
        Z = griddata((history_data[:, 0], history_data[:, 1]), history_data[:, 2], (X, Y), method='cubic')

        # 3D 서피스 플롯
        surf = ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.8)

        # 실제 데이터 포인트 표시
        ax.scatter(history_data[:, 0], history_data[:, 1], history_data[:, 2], c='red', s=50, marker='o')

        # 변화량 다시 계산하지 않고 공통 함수에서 구한 값 사용
        ax.set_xlabel(f'파라미터{param1_idx} 최적값')
        ax.set_ylabel(f'파라미터{param2_idx} 최적값')
        ax.set_zlabel('최적화 기준값')
        ax.set_title(f'최적값 조합 서피스 (스코어 변화가 큰 파라미터: {param1_idx}, {param2_idx})')

        # 컬러바
        plt.colorbar(surf, ax=ax, shrink=0.5, aspect=5)

    def _plot_param_correlation_3d(self, ax):
        """파라미터 상관관계 3D 산점도"""

        # 선택된 파라미터들로 데이터 수집
        all_params = []
        all_scores = []

        for history in self.optimization_3d_history:
            param_values = []
            scores_in_step = []
            for param_idx, (optimal_value, current_score) in history['params'].items():
                if param_idx in self.top_3_params:
                    param_values.append(optimal_value)
                    scores_in_step.append(current_score)
            all_params.append(param_values)
            all_scores.append(max(scores_in_step))

        # 선택된 3개 파라미터로 3D 산점도
        param_array = get_np().array(all_params)
        scores_array = get_np().array(all_scores)

        # 색상 (점수에 따른 색상)
        scatter = ax.scatter(param_array[:, 0], param_array[:, 1], param_array[:, 2],
                             c=scores_array, cmap='plasma', s=100, alpha=0.7)

        # 진화 방향 화살표
        if len(param_array) > 1:
            for i in range(len(param_array) - 1):
                ax.quiver(param_array[i, 0], param_array[i, 1], param_array[i, 2],
                          param_array[i + 1, 0] - param_array[i, 0],
                          param_array[i + 1, 1] - param_array[i, 1],
                          param_array[i + 1, 2] - param_array[i, 2],
                          color='red', alpha=0.6, arrow_length_ratio=0.1)

        ax.set_xlabel(f'파라미터{self.top_3_params[0]}')
        ax.set_ylabel(f'파라미터{self.top_3_params[1]}')
        ax.set_zlabel(f'파라미터{self.top_3_params[2]}')
        ax.set_title(f'파라미터 상관관계 3D, 스코어 변화가 큰 파라미터 3개: {self.top_3_params}')

        # 컬러바
        plt.colorbar(scatter, ax=ax, shrink=0.5, aspect=5)

    def _plot_convergence_heatmap(self, ax):
        """수렴 패턴 2D 히트맵"""

        # 파라미터 변화율 계산
        n_steps = len(self.optimization_3d_history)
        n_params = len(self.optimization_3d_history[0]['params'])

        convergence_matrix = get_np().zeros((n_params, n_steps))

        for step_idx, history in enumerate(self.optimization_3d_history):
            for param_idx, (optimal_value, score) in history['params'].items():
                convergence_matrix[param_idx, step_idx] = optimal_value

        # 히트맵 생성
        im = ax.imshow(convergence_matrix, cmap='coolwarm', aspect='auto')

        # 축 레이블
        ax.set_xlabel('최적화 단계')
        ax.set_ylabel('파라미터 인덱스')
        ax.set_title('파라미터 수렴 패턴')

        # 값 표시
        for i in range(n_params):
            for j in range(n_steps):
                ax.text(j, i, f'{convergence_matrix[i, j]:.1f}', ha="center", va="center", color="black", fontsize=8)

        # 컬러바
        plt.colorbar(im, ax=ax)

    def _plot_sensitivity_evolution(self, ax):
        """파라미터 민감도 진화"""

        steps = []
        sensitivity_scores = []

        for history in self.optimization_3d_history:
            step = history['step']
            params = history['params']

            # 파라미터별 변화율 계산 (민감도)
            sensitivities = []
            for param_idx, (optimal_value, score) in params.items():
                # 이전 단계와의 변화율
                if step > 0:
                    prev_history = self.optimization_3d_history[step - 1]
                    prev_value = prev_history['params'][param_idx][0]
                    if prev_value != 0:
                        sensitivity = abs((optimal_value - prev_value) / prev_value) * 100
                    else:
                        sensitivity = 0
                else:
                    sensitivity = 0
                sensitivities.append(sensitivity)

            steps.append(step)
            sensitivity_scores.append(get_np().mean(sensitivities))

        # 민감도 진화 플롯
        ax.plot(steps, sensitivity_scores, 'b-', linewidth=2, marker='o', markersize=6)
        ax.fill_between(steps, sensitivity_scores, alpha=0.3)

        ax.set_xlabel('최적화 단계')
        ax.set_ylabel('평균 파라미터 민감도 (%)')
        ax.set_title('파라미터 민감도 진화')
        ax.grid(True, alpha=0.3)

    def _plot_optimization_efficiency(self, ax):
        """최적화 효율성 분석"""

        steps = []
        scores = []
        improvements = []

        prev_score = None
        for history in self.optimization_3d_history:
            step = history['step']
            current_score = list(history['params'].values())[0][1]  # 최고 기준값

            steps.append(step)
            scores.append(current_score)

            if prev_score is not None:
                improvement = ((current_score - prev_score) / prev_score) * 100
                improvements.append(improvement)
            else:
                improvements.append(0)

            prev_score = current_score

        # 효율성 플롯
        ax2 = ax.twinx()

        # 기준값 변화
        line1 = ax.plot(steps, scores, 'b-', linewidth=2, marker='o', label='최적화 기준값')
        ax.set_xlabel('최적화 단계')
        ax.set_ylabel('최적화 기준값', color='b')
        ax.tick_params(axis='y', labelcolor='b')

        # 개선율 변화
        line2 = ax2.plot(steps, improvements, 'r-', linewidth=2, marker='s', alpha=0.7, label='개선율(%)')
        ax2.set_ylabel('개선율 (%)', color='r')
        ax2.tick_params(axis='y', labelcolor='r')

        # 제로라인
        ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

        ax.set_title('최적화 효율성 분석')
        ax.grid(True, alpha=0.3)

        # 범례
        lines = line1 + line2
        labels = [line.get_label() for line in lines]
        ax.legend(lines, labels, loc='best')
