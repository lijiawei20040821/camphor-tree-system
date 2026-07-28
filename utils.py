import pandas as pd
import numpy as np
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64


def calculate_basal_area(dbh):
    """计算胸高断面积（cm²），樟树生物量学基础指标"""
    return np.pi * (dbh / 2.0) ** 2


def classify_growth_status(score):
    """根据综合评分判定樟树生长状态"""
    if score >= 4:
        return '正常'
    elif score >= 2:
        return '衰弱'
    else:
        return '濒危'


def normalize_ecological_factors(df):
    """生态因子数据标准化处理"""
    df_norm = df.copy()
    numeric_cols = df_norm.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        col_min = df_norm[col].min()
        col_max = df_norm[col].max()
        if col_max - col_min > 1e-10:
            df_norm[col] = (df_norm[col] - col_min) / (col_max - col_min)
        else:
            df_norm[col] = 0.5
    return df_norm


def calculate_hydro_thermal_index(precipitation, humidity):
    """计算水热综合指数"""
    return precipitation * humidity / 100.0


def calculate_carbon_storage_per_year(avg_carbon, tree_age):
    """计算单位树龄年固碳量"""
    if tree_age > 0:
        return avg_carbon / tree_age
    return 0


def assess_soil_health(compactness, organic_content=None):
    """评估土壤健康等级"""
    if compactness == '疏松':
        score = 0.85
    elif compactness == '中等':
        score = 0.70
    elif compactness == '紧密':
        score = 0.45
    else:
        score = 0.60

    if organic_content is not None and organic_content > 3:
        score += 0.1
    return min(score, 1.0)


def clean_data(df):
    """对导入的樟树监测数据进行清洗"""
    df_cleaned = df.copy()

    numeric_fields = [
        'tree_age', 'dbh', 'tree_height', 'annual_carbon_seq',
        'total_precipitation', 'avg_temperature', 'avg_humidity',
        'avg_wind_speed', 'altitude'
    ]

    for field in numeric_fields:
        if field in df_cleaned.columns:
            df_cleaned[field] = pd.to_numeric(df_cleaned[field], errors='coerce')

    anomalies = []
    if 'annual_carbon_seq' in df_cleaned.columns:
        carbon_anomalies = df_cleaned[
            (df_cleaned['annual_carbon_seq'] < 12.3) |
            (df_cleaned['annual_carbon_seq'] > 215.6)
        ].index.tolist()
        anomalies.extend(carbon_anomalies)

    missing_report = {}
    for col in df_cleaned.columns:
        missing_count = df_cleaned[col].isna().sum()
        if missing_count > 0:
            missing_report[col] = {
                'count': missing_count,
                'percentage': round(missing_count / len(df_cleaned) * 100, 2)
            }

    return df_cleaned, anomalies, missing_report


def validate_data_format(file_path):
    """验证上传文件的格式是否符合樟树数据导入要求"""
    allowed_extensions = {'xlsx', 'xls', 'csv'}
    file_ext = file_path.split('.')[-1].lower()

    if file_ext not in allowed_extensions:
        return False, "不支持的文件格式，请上传Excel或CSV文件"

    try:
        if file_ext == 'csv':
            df = pd.read_csv(file_path, nrows=1)
        else:
            df = pd.read_excel(file_path, nrows=1)

        required_columns = ['region', 'tree_age', 'dbh', 'tree_height']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return False, f"缺少必要的列: {', '.join(missing_columns)}"

        return True, "文件格式正确"

    except Exception as e:
        return False, f"文件读取错误: {str(e)}"


def _save_plot_to_base64():
    """将当前 matplotlib 图表保存为 base64 编码字符串"""
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    graphic = base64.b64encode(image_png).decode('utf-8')
    plt.close()
    return graphic


def create_histogram(data, variable, bins=20):
    """创建生态数据分布直方图"""
    plt.figure(figsize=(10, 6))
    plt.hist(data[variable].dropna(), bins=bins, alpha=0.7, color='forestgreen', edgecolor='black')
    plt.title(f'{variable} 分布')
    plt.xlabel(variable)
    plt.ylabel('频数')
    plt.grid(True, alpha=0.3)
    return _save_plot_to_base64()


def create_scatter_plot(data, x_var, y_var):
    """创建生态因子散点图"""
    plt.figure(figsize=(10, 6))
    plt.scatter(data[x_var], data[y_var], alpha=0.6, color='darkgreen')
    plt.title(f'{x_var} 与 {y_var} 的关系')
    plt.xlabel(x_var)
    plt.ylabel(y_var)
    plt.grid(True, alpha=0.3)

    correlation = data[[x_var, y_var]].corr().iloc[0, 1]
    plt.text(0.05, 0.95, f'相关系数: {correlation:.3f}',
             transform=plt.gca().transAxes, fontsize=12,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    graphic = _save_plot_to_base64()
    return graphic, correlation


def create_correlation_heatmap(data, variables):
    """创建生态因子相关性热力图"""
    plt.figure(figsize=(12, 8))
    correlation_matrix = data[variables].corr()
    sns.heatmap(correlation_matrix, annot=True, cmap='YlGnBu', center=0,
                square=True, fmt='.2f', cbar_kws={"shrink": .8})
    plt.title('生态变量相关性热力图')
    plt.tight_layout()
    graphic = _save_plot_to_base64()
    return graphic, correlation_matrix


def monte_carlo_simulation(model, X, n_simulations=10):
    """执行蒙特卡洛模拟，计算生态预测置信区间"""
    predictions = []
    for _ in range(n_simulations):
        X_noisy = X + np.random.normal(0, 0.01, X.shape)
        pred = model.predict(X_noisy)
        predictions.append(pred)

    predictions = np.array(predictions)
    mean_pred = np.mean(predictions, axis=0)
    lower_bound = np.percentile(predictions, 2.5, axis=0)
    upper_bound = np.percentile(predictions, 97.5, axis=0)

    return mean_pred, lower_bound, upper_bound


def generate_growth_assessment_report(tree_data, prediction, confidence, factors):
    """生成樟树生长状态评估报告"""
    report = {
        'tree_info': tree_data,
        'prediction': prediction,
        'confidence': confidence,
        'factors': factors,
        'assessment_date': datetime.now().strftime('%Y-%m-%d'),
        'recommendations': generate_recommendations(prediction, factors)
    }
    return report


def generate_recommendations(prediction, factors):
    """根据预测结果和影响因素生成樟树养护建议"""
    recommendations = []

    if prediction == '衰弱':
        recommendations.append("建议增加养护频次，定期检查树木健康状况")
        if 'avg_wind_speed' in factors and factors['avg_wind_speed'] == 'high':
            recommendations.append("考虑设置防风设施，减少强风对树木的影响")
    elif prediction == '濒危':
        recommendations.append("需要立即采取保护措施，建议联系专业林业人员")
        recommendations.append("建议联系林业专家进行现场评估")
    else:
        recommendations.append("继续保持现有养护措施")
        recommendations.append("定期监测生长状态变化")

    return recommendations