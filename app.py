from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash, send_from_directory, Response, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, TreeData, SystemLog
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import os
from datetime import datetime, timedelta
import json
import numpy as np
import io
from sqlalchemy import func
from ml_models import growth_model, carbon_model

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///camphor_tree.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化数据库
db.init_app(app)

# 初始化登录管理
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录系统'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# 记录系统日志的函数
def log_action(action_type, details='', ip_address=None):
    if ip_address is None:
        ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    
    log = SystemLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action_type=action_type,
        action_details=details,
        ip_address=ip_address
    )
    db.session.add(log)
    db.session.commit()

def allowed_file(filename):
    """检查文件格式"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls', 'csv'}

# ==================== 路由定义 ====================

@app.route('/')
def index():
    """首页"""
    return redirect(url_for('login'))

@app.route('/test')
def test_page():
    """测试页面 - 无需登录"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>系统自检页面</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .success { color: green; font-weight: bold; }
    </style>
</head>
<body>
    <h1>✅ 系统运行正常！</h1>
    <p class="success">融合机器学习的华南樟树生态因子关联解析与碳汇功能预测系统</p>
    <p>当前时间: {}</p>
    <p>系统版本: <span class="success">V1.0</span></p>
    <hr>
    <h3>核心功能模块：</h3>
    <ul>
        <li><a href="/login">用户登录</a></li>
        <li><a href="/dashboard">系统仪表盘</a></li>
        <li><a href="/data_management">数据管理</a></li>
        <li><a href="/growth_assessment">生长评估</a></li>
        <li><a href="/carbon_assessment">碳汇评估</a></li>
        <li><a href="/correlation_analysis">关联分析</a></li>
        <li><a href="/scenario_prediction">情景预测</a></li>
    </ul>
</body>
</html>
'''.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                              'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/api/status')
def api_status():
    """API状态检查"""
    return jsonify({
        'status': 'success',
        'message': '系统运行正常',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0',
        'modules': ['数据管理', '生长评估', '碳汇评估', '关联分析', '情景预测']
    })

@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录页面"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            log_action('用户登录', f'用户 {username} 登录系统')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误', 'error')
            return render_template('login.html', error='用户名或密码错误')
    
    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """专业仪表盘 - 性能优化版"""
    # 1. 获取总数 (1次查询)
    total_trees = TreeData.query.count()

    # 2. 优化生长状态统计 (使用聚合查询替代 3 次单独查询)
    # 执行结果类似于: [('正常', 80), ('衰弱', 15), ('濒危', 5)]
    status_counts = db.session.query(
        TreeData.growth_status, func.count(TreeData.id)
    ).group_by(TreeData.growth_status).all()

    # 将结果转换为字典方便取值
    status_map = {status: count for status, count in status_counts}
    normal_trees = status_map.get('正常', 0)
    weak_trees = status_map.get('衰弱', 0)
    critical_trees = status_map.get('濒危', 0)

    # 3. 计算平均碳汇量 (已优化)
    avg_carbon_result = db.session.query(func.avg(TreeData.annual_carbon_seq)).scalar()
    avg_carbon = round(avg_carbon_result, 2) if avg_carbon_result else 0

    # 4. 今日操作次数
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_operations = SystemLog.query.filter(
        SystemLog.timestamp >= today_start,
        SystemLog.user_id == current_user.id
    ).count()

    # 5. 生长状态统计字典
    growth_stats = {
        'normal': normal_trees,
        'weak': weak_trees,
        'critical': critical_trees
    }

    # 6. 碳汇趋势数据（示例数据，实际项目中建议单独建立趋势统计表或使用缓存）
    carbon_trend = {
        'labels': ['1月', '2月', '3月', '4月', '5月', '6月'],
        'data': [85, 78, 90, 88, 92, 95]
    }

    # 7. 优化区域统计 (解决 N+1 问题，一次查询获取所有区域数据)
    # 原代码遍历列表查询数据库，改为直接分组查询
    region_counts = db.session.query(
        TreeData.region, func.count(TreeData.id)
    ).group_by(TreeData.region).all()

    # 转换为前端需要的格式 [{'region': '天河区', 'count': 120}, ...]
    # 过滤掉 region 为空的数据
    region_stats = [
        {'region': r, 'count': c}
        for r, c in region_counts
        if r and c > 0
    ]

    # 按数量降序排列，让图表更好看
    region_stats.sort(key=lambda x: x['count'], reverse=True)

    return render_template('dashboard.html',
                           total_trees=total_trees,
                           normal_trees=normal_trees,
                           weak_trees=weak_trees,
                           critical_trees=critical_trees,
                           avg_carbon=avg_carbon,
                           today_operations=today_operations,
                           growth_stats=growth_stats,
                           carbon_trend=carbon_trend,
                           region_stats=region_stats,
                           current_time=datetime.now())

@app.route('/logout')
@login_required
def logout():
    """用户登出"""
    log_action('用户登出', f'用户 {current_user.username} 登出系统')
    logout_user()
    flash('您已成功退出系统', 'success')
    return redirect(url_for('login'))

# ==================== 功能页面路由 ====================

@app.route('/growth_assessment')
@login_required
def growth_assessment():
    """生长评估页面"""
    try:
        # 获取必要的初始数据
        regions = ['天河区', '越秀区', '海珠区', '荔湾区', '白云区', '黄埔区']
        return render_template('growth_assessment.html',
                           regions=regions)
    except Exception as e:
        current_app.logger.error(f"生长评估页面错误: {str(e)}")
        return render_template('error.html', message="加载生长评估页面失败"), 500

@app.route('/carbon_assessment')
@login_required
def carbon_assessment():
    """碳汇评估页面"""
    try:
        # 获取必要的初始数据
        return render_template('carbon_assessment.html')
    except Exception as e:
        current_app.logger.error(f"碳汇评估页面错误: {str(e)}")
        return render_template('error.html', message="加载碳汇评估页面失败"), 500

@app.route('/scenario_prediction')
@login_required
def scenario_prediction():
    """情景预测页面"""
    return render_template('scenario_prediction.html')

@app.route('/correlation_analysis')
@login_required
def correlation_analysis():
    """关联分析页面"""
    return render_template('correlation_analysis.html')

@app.route('/system_management')
@login_required
def system_management():
    """系统管理页面（仅管理员）"""
    if current_user.role != 'admin':
        flash('权限不足，需要管理员权限', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    total_logs = SystemLog.query.count()
    recent_logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(10).all()
    
    return render_template('system_management.html',
                         users=users,
                         total_logs=total_logs,
                         recent_logs=recent_logs)

# ==================== 数据管理模块 ====================

@app.route('/data_management')
@login_required
def data_management():
    """数据管理页面"""
    try:
        # 获取基础数据
        total_trees = TreeData.query.count()
        recent_trees = TreeData.query.order_by(TreeData.recorded_year.desc()).limit(10).all()
        
        # 计算生长状态统计
        normal_trees = TreeData.query.filter_by(growth_status='正常').count()
        weak_trees = TreeData.query.filter_by(growth_status='衰弱').count()
        critical_trees = TreeData.query.filter_by(growth_status='濒危').count()
        
        # 构造growth_stats字典
        growth_stats = {
            'normal': normal_trees,
            'weak': weak_trees,
            'critical': critical_trees
        }
        
        return render_template('data_management.html',
                           total_trees=total_trees,
                           recent_trees=recent_trees,
                           growth_stats=growth_stats)  # 传递统计结果
                           
    except Exception as e:
        current_app.logger.error(f"数据管理页面错误: {str(e)}")
        return render_template('error.html', message="加载数据失败"), 500
    

@app.route('/api/trees')
@login_required
def api_trees():
    """获取樟树数据API - 分页优化版"""
    # 1. 获取分页参数 (默认为第1页，每页50条)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    # 2. 使用 paginate 分页查询，而不是 query.all()
    # order_by(TreeData.id.desc()) 确保最新录入的数据排在前面
    pagination = TreeData.query.order_by(TreeData.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    data = []
    for tree in pagination.items:
        data.append({
            'id': tree.id,
            'region': tree.region,
            'tree_age': tree.tree_age,
            'dbh': tree.dbh,
            'tree_height': tree.tree_height,
            'annual_carbon_seq': tree.annual_carbon_seq,
            'growth_status': tree.growth_status,
            'soil_compactness': tree.soil_compactness,
            'total_precipitation': tree.total_precipitation,
            'avg_temperature': tree.avg_temperature,
            'avg_humidity': tree.avg_humidity,
            'avg_wind_speed': tree.avg_wind_speed,
            'altitude': tree.altitude,
            'recorded_year': tree.recorded_year
        })

    # 3. 返回包含分页元数据的标准结构
    return jsonify({
        'success': True,
        'data': data,
        'pagination': {
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page
        }
    })

@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload():
    """文件上传API"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # 读取并处理上传的数据
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            # 数据验证和处理
            processed_count = 0
            for _, row in df.iterrows():
                tree = TreeData(
                    region=row.get('region', '未知'),
                    tree_age=float(row.get('tree_age', 0)),
                    dbh=float(row.get('dbh', 0)),
                    tree_height=float(row.get('tree_height', 0)),
                    annual_carbon_seq=float(row.get('annual_carbon_seq', 0)),
                    growth_status=row.get('growth_status', '正常'),
                    soil_compactness=row.get('soil_compactness', '中等'),
                    total_precipitation=float(row.get('total_precipitation', 0)),
                    avg_temperature=float(row.get('avg_temperature', 0)),
                    avg_humidity=float(row.get('avg_humidity', 0)),
                    avg_wind_speed=float(row.get('avg_wind_speed', 0)),
                    altitude=float(row.get('altitude', 0)),
                    recorded_year=int(row.get('recorded_year', datetime.now().year)),
                    created_by=current_user.id
                )
                db.session.add(tree)
                processed_count += 1
            
            db.session.commit()
            
            # 记录操作日志
            log_action('数据导入', f'成功导入 {processed_count} 条数据 from {filename}')
            
            return jsonify({
                'success': True, 
                'message': f'成功导入 {processed_count} 条数据',
                'count': processed_count
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'数据处理错误: {str(e)}'})
    
    return jsonify({'success': False, 'message': '不支持的文件格式'})

@app.route('/api/export/trees')
@login_required
def api_export_trees():
    """导出樟树数据API"""
    try:
        trees = TreeData.query.all()
        
        # 创建DataFrame
        data = []
        for tree in trees:
            data.append({
                '区域': tree.region,
                '树龄(年)': tree.tree_age,
                '胸围(cm)': tree.dbh,
                '树高(m)': tree.tree_height,
                '年固碳量(kg)': tree.annual_carbon_seq,
                '生长状态': tree.growth_status,
                '土壤紧密度': tree.soil_compactness,
                '总降水量(mm)': tree.total_precipitation,
                '平均气温(℃)': tree.avg_temperature,
                '平均湿度(%)': tree.avg_humidity,
                '平均风速(m/s)': tree.avg_wind_speed,
                '海拔(m)': tree.altitude,
                '记录年份': tree.recorded_year
            })
        
        df = pd.DataFrame(data)
        
        # 创建Excel文件
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='樟树数据', index=False)
        
        output.seek(0)
        
        # 记录操作日志
        log_action('数据导出', f'导出{len(trees)}条樟树数据')
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'樟树数据_导出_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        current_app.logger.error(f'导出失败: {str(e)}')
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'})

@app.route('/api/trees/<int:tree_id>', methods=['DELETE'])
@login_required
def api_delete_tree(tree_id):
    """删除樟树数据API"""
    try:
        tree = TreeData.query.get(tree_id)
        if tree:
            db.session.delete(tree)
            db.session.commit()
            log_action('数据删除', f'删除樟树数据 ID: {tree_id}')
            return jsonify({'success': True, 'message': '数据删除成功'})
        else:
            return jsonify({'success': False, 'message': '数据不存在'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'删除失败: {str(e)}')
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

# 添加快捷导出路由
@app.route('/api/export/csv')
@login_required
def api_export_csv():
    """导出CSV格式数据"""
    try:
        trees = TreeData.query.all()
        
        data = []
        for tree in trees:
            data.append({
                'region': tree.region,
                'tree_age': tree.tree_age,
                'dbh': tree.dbh,
                'tree_height': tree.tree_height,
                'annual_carbon_seq': tree.annual_carbon_seq,
                'growth_status': tree.growth_status
            })
        
        df = pd.DataFrame(data)
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-disposition': 'attachment; filename=tree_data.csv'}
        )
    except Exception as e:
        return jsonify({'success': False, 'message': f'CSV导出失败: {str(e)}'})

# ==================== 生长评估模块 ====================

@app.route('/api/growth/predict', methods=['POST'])
@login_required
def api_growth_predict():
    """生长状态预测API"""
    data = request.get_json()
    
    try:
        # 获取特征数据
        features = [
            float(data.get('precipitation', 0)),
            float(data.get('humidity', 0)),
            float(data.get('windSpeed', 0)),
            float(data.get('altitude', 0)),
            float(data.get('treeHeight', 0)),
            float(data.get('carbonPerAge', 0))
        ]
        
        # 使用模型预测
        status, confidence = growth_model.predict(features)
        
        # 生成分析报告
        analysis = generate_growth_analysis(features, status)
        factors = analyze_growth_factors(features)
        
        log_action('生长评估', f'预测生长状态: {status} (置信度: {confidence})')
        
        return jsonify({
            'success': True,
            'prediction': status,
            'confidence': confidence,
            'analysis': analysis,
            'factors': factors
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'预测错误: {str(e)}'})

def generate_growth_analysis(features, status):
    """生成生长状态分析报告"""
    precipitation, humidity, wind_speed, altitude, tree_height, carbon_per_age = features
    
    analysis = {
        'status': status,
        'recommendations': [],
        'risk_factors': []
    }
    
    if status == '正常':
        analysis['recommendations'].append('当前生长状态良好，继续保持现有养护措施。')
    elif status == '衰弱':
        analysis['recommendations'].append('建议加强养护管理，定期检查树木健康状况。')
    else:  # 濒危
        analysis['recommendations'].append('需要立即采取保护措施，建议联系专业林业人员。')
    
    if precipitation < 1500:
        analysis['risk_factors'].append('降水量偏低，可能影响生长。')
    if humidity < 60:
        analysis['risk_factors'].append('湿度较低，建议适当灌溉。')
    if wind_speed > 3:
        analysis['risk_factors'].append('风速较高，考虑设置防风设施。')
    
    return analysis

def analyze_growth_factors(features):
    """分析生长影响因素"""
    factors = []
    precipitation, humidity, wind_speed, altitude, tree_height, carbon_per_age = features
    
    if precipitation > 1700:
        factors.append({'factor': '降水量', 'impact': '正面', 'level': '高'})
    elif precipitation < 1500:
        factors.append({'factor': '降水量', 'impact': '负面', 'level': '中'})
        
    if humidity > 75:
        factors.append({'factor': '湿度', 'impact': '正面', 'level': '高'})
    elif humidity < 60:
        factors.append({'factor': '湿度', 'impact': '负面', 'level': '中'})
        
    if wind_speed < 2:
        factors.append({'factor': '风速', 'impact': '正面', 'level': '中'})
    elif wind_speed > 3:
        factors.append({'factor': '风速', 'impact': '负面', 'level': '高'})
        
    return factors

@app.route('/api/growth/history')
@login_required
def api_growth_history():
    """获取生长评估历史记录"""
    # 模拟历史数据
    history = [
        {
            'id': 1,
            'timestamp': datetime.now() - timedelta(days=1),
            'status': '正常',
            'confidence': 0.85,
            'keyFactors': ['降水量适宜', '湿度良好']
        },
        {
            'id': 2,
            'timestamp': datetime.now() - timedelta(days=3),
            'status': '衰弱',
            'confidence': 0.72,
            'keyFactors': ['风速偏高', '湿度偏低']
        }
    ]
    
    return jsonify(history)

# ==================== 碳汇评估模块 ====================

@app.route('/api/carbon/calculate', methods=['POST'])
@login_required
def api_carbon_calculate():
    """碳汇能力计算API"""
    data = request.get_json()
    
    try:
        # 获取特征数据
        features = [
            float(data.get('tree_age', 0)),
            float(data.get('dbh', 0)),
            float(data.get('tree_height', 0)),
            data.get('soil_compactness', '中等'),
            float(data.get('humidity', 0))
        ]
        
        # 使用模型计算碳汇量
        carbon_seq = carbon_model.predict(features)
        
        log_action('碳汇评估', f'计算碳汇量: {carbon_seq:.2f} kg')
        
        return jsonify({
            'success': True,
            'carbon_sequestration': round(carbon_seq, 2),
            'unit': 'kg/年',
            'factors': analyze_carbon_factors(features, carbon_seq)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'计算错误: {str(e)}'})

def analyze_carbon_factors(features, carbon_seq):
    """分析碳汇影响因素"""
    tree_age, dbh, tree_height, soil_compactness, humidity = features
    
    factors = []
    
    # 胸围影响
    if dbh > 100:
        factors.append({'factor': '胸围', 'impact': '强正面', 'contribution': '高'})
    elif dbh < 50:
        factors.append({'factor': '胸围', 'impact': '负面', 'contribution': '中'})
    
    # 土壤紧密度影响
    if soil_compactness == '疏松':
        factors.append({'factor': '土壤', 'impact': '正面', 'contribution': '中'})
    elif soil_compactness == '紧密':
        factors.append({'factor': '土壤', 'impact': '负面', 'contribution': '中'})
    
    # 湿度影响
    if humidity > 75:
        factors.append({'factor': '湿度', 'impact': '正面', 'contribution': '中'})
    
    return factors

# ==================== 关联分析模块 ====================

@app.route('/api/correlation/analyze', methods=['POST'])
@login_required
def api_correlation_analyze_endpoint():  # 修改函数名避免重复
    """关联分析API"""
    data = request.get_json()
    analysis_type = data.get('type', 'single')
    
    try:
        if analysis_type == 'single':
            # 单变量分析
            variable = data.get('variable')
            result = analyze_single_variable(variable)
        elif analysis_type == 'double':
            # 双变量分析
            var1 = data.get('variable1')
            var2 = data.get('variable2')
            result = analyze_double_variables(var1, var2)
        else:
            # 多变量分析
            variables = data.get('variables', [])
            result = analyze_multiple_variables(variables)
        
        log_action('关联分析', f'执行{analysis_type}分析')
        
        return jsonify({
            'success': True,
            'type': analysis_type,
            'result': result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'分析错误: {str(e)}'})

def analyze_single_variable(variable):
    """单变量分析"""
    # 模拟分析结果
    trees = TreeData.query.all()
    values = [getattr(tree, variable) for tree in trees if getattr(tree, variable) is not None]
    
    if not values:
        return {'error': '无有效数据'}
    
    return {
        'mean': round(np.mean(values), 2),
        'std': round(np.std(values), 2),
        'min': round(min(values), 2),
        'max': round(max(values), 2),
        'distribution': np.histogram(values, bins=10)[0].tolist()
    }

def analyze_double_variables(var1, var2):
    """双变量分析"""
    # 模拟相关性分析
    trees = TreeData.query.all()
    values1 = [getattr(tree, var1) for tree in trees if getattr(tree, var1) is not None]
    values2 = [getattr(tree, var2) for tree in trees if getattr(tree, var2) is not None]
    
    if len(values1) != len(values2) or len(values1) == 0:
        return {'error': '数据不匹配'}
    
    # 计算相关系数
    correlation = np.corrcoef(values1, values2)[0, 1]
    
    return {
        'correlation': round(correlation, 3),
        'sample_size': len(values1),
        'relationship': '正相关' if correlation > 0 else '负相关'
    }

def analyze_multiple_variables(variables):
    """多变量分析"""
    # 模拟多变量分析
    return {
        'heatmap_data': np.random.rand(len(variables), len(variables)).tolist(),
        'variables': variables,
        'strong_correlations': []
    }

# ==================== 情景预测模块API ====================

@app.route('/api/scenario/predict', methods=['POST'])
@login_required
def api_scenario_predict():
    """情景预测API"""
    data = request.get_json()
    scenario_type = data.get('scenario_type', 'baseline')
    years = int(data.get('years', 10))
    
    try:
        # 模拟情景预测
        predictions = simulate_scenario(scenario_type, years)
        
        log_action('情景预测', f'执行{scenario_type}情景预测 ({years}年)')
        
        return jsonify({
            'success': True,
            'scenario': scenario_type,
            'years': years,
            'predictions': predictions,
            'confidence': 0.85,
            'risk_analysis': generate_risk_analysis(scenario_type),
            'recommendations': generate_recommendations(scenario_type)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'预测错误: {str(e)}'})

def simulate_scenario(scenario_type, years):
    """模拟情景预测"""
    predictions = []
    
    # 基础数据
    current_carbon = 85  # 当前平均碳汇量
    current_normal_ratio = 0.7  # 当前正常比例
    
    for year in range(1, years + 1):
        if scenario_type == 'baseline':
            # 基准情景 - 缓慢变化
            carbon = current_carbon * (1 + 0.01 * year)
            normal_ratio = max(0.3, current_normal_ratio - 0.02 * year)
        elif scenario_type == 'warming':
            # 气候变暖情景
            carbon = current_carbon * (1 + 0.005 * year)
            normal_ratio = max(0.2, current_normal_ratio - 0.03 * year)
        else:  # extreme_rain
            # 极端降水情景
            carbon = current_carbon * (1 + 0.015 * year)
            normal_ratio = max(0.4, current_normal_ratio - 0.01 * year)
        
        predictions.append({
            'year': datetime.now().year + year,
            'carbon_sequestration': round(carbon, 1),
            'normal_ratio': round(normal_ratio, 3),
            'upper_bound': round(carbon * 1.1, 1),  # 置信区间上限
            'lower_bound': round(carbon * 0.9, 1)   # 置信区间下限
        })
    
    return predictions

def generate_risk_analysis(scenario_type):
    """生成风险分析"""
    if scenario_type == 'warming':
        return [
            {'level': '高', 'description': '高温胁迫对生长的影响'},
            {'level': '中', 'description': '水分蒸发增加风险'}
        ]
    elif scenario_type == 'extreme_rain':
        return [
            {'level': '高', 'description': '洪涝灾害风险'},
            {'level': '中', 'description': '土壤侵蚀风险'}
        ]
    else:
        return [
            {'level': '中', 'description': '气候变化适应性风险'},
            {'level': '低', 'description': '常规管理风险'}
        ]

def generate_recommendations(scenario_type):
    """生成应对建议"""
    if scenario_type == 'warming':
        return [
            '加强灌溉管理，确保水分供应',
            '适当遮荫，降低高温影响',
            '选择耐热品种进行补植'
        ]
    elif scenario_type == 'extreme_rain':
        return [
            '加强排水系统建设',
            '加固土壤，防止侵蚀',
            '建立灾害预警机制'
        ]
    else:
        return [
            '保持现有养护措施',
            '加强监测和预警',
            '定期评估生长状态'
        ]

@app.route('/api/scenario/comparison')
@login_required
def api_scenario_comparison():
    """情景对比分析API"""
    return jsonify({
        'scenarios': ['基准情景', '气候变暖', '极端降水', '优化管理'],
        'data': {
            '5年': [85.6, 82.3, 88.9, 92.1],
            '10年': [88.7, 80.1, 91.5, 96.8],
            '20年': [92.3, 76.8, 95.2, 102.5]
        }
    })

@app.route('/api/scenario/sensitivity')
@login_required
def api_scenario_sensitivity():
    """敏感性分析API"""
    return jsonify({
        'factors': ['温度变化', '降水量', '湿度', '土壤紧密度', '风速'],
        'sensitivity': [0.15, 0.12, 0.08, 0.06, 0.04],
        'impact': ['高敏感', '高敏感', '中敏感', '中敏感', '低敏感']
    })

# ==================== 关联分析API路由 ====================

@app.route('/api/correlation/distribution')
@login_required
def api_correlation_distribution():
    """单变量分布分析API"""
    variable = request.args.get('variable', 'tree_age')
    
    try:
        # 模拟分布数据
        if variable == 'tree_age':
            distribution = {
                'labels': ['0-50年', '50-100年', '100-150年', '150-200年', '200年以上'],
                'data': [15, 28, 35, 18, 4]
            }
        elif variable == 'dbh':
            distribution = {
                'labels': ['0-50cm', '50-100cm', '100-150cm', '150cm以上'],
                'data': [20, 45, 25, 10]
            }
        else:
            distribution = {
                'labels': ['低', '中低', '中等', '中高', '高'],
                'data': [10, 25, 40, 20, 5]
            }
            
        return jsonify({
            'success': True,
            'data': distribution,
            'variable': variable
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/correlation/analysis')
@login_required
def api_correlation_analysis():
    """双变量相关性分析API"""
    var_x = request.args.get('var_x', 'tree_age')
    var_y = request.args.get('var_y', 'annual_carbon_seq')
    
    try:
        # 模拟相关性数据
        import random
        points = []
        for i in range(20):
            x = random.randint(50, 300)
            y = x * 0.3 + random.randint(-10, 10)
            points.append({'x': x, 'y': max(y, 10)})
            
        return jsonify({
            'success': True,
            'data': {
                'points': points,
                'correlation': 0.89,
                'variables': [var_x, var_y]
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/correlation/multivariate', methods=['POST'])
@login_required
def api_correlation_multivariate():
    """多变量关联分析API"""
    try:
        data = request.get_json()
        variables = data.get('variables', [])
        
        # 模拟多变量分析结果
        result = {
            'labels': variables,
            'datasets': [{
                'label': '平均值',
                'data': [65, 59, 80, 81, 56, 55, 40][:len(variables)],
                'fill': True,
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgb(54, 162, 235)',
                'pointBackgroundColor': 'rgb(54, 162, 235)'
            }]
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ==================== 系统管理模块 ====================

@app.route('/api/system/users', methods=['POST'])
@login_required
def api_system_users():
    """用户管理API"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': '权限不足'})
    
    data = request.get_json()
    action = data.get('action')
    
    try:
        if action == 'create':
            # 创建用户
            username = data['username']
            password = data['password']
            department = data.get('department', '')
            role = data.get('role', 'user')
            
            if User.query.filter_by(username=username).first():
                return jsonify({'success': False, 'message': '用户名已存在'})
            
            user = User(
                username=username,
                department=department,
                role=role
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            log_action('用户管理', f'创建用户: {username}')
            return jsonify({'success': True, 'message': '用户创建成功'})
            
        elif action == 'toggle':
            # 启用/禁用用户
            user_id = data['user_id']
            user = User.query.get(user_id)
            if user:
                user.is_active = not user.is_active
                db.session.commit()
                
                status = '启用' if user.is_active else '禁用'
                log_action('用户管理', f'{status}用户: {user.username}')
                return jsonify({'success': True, 'message': f'用户已{status}'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})
    
    return jsonify({'success': False, 'message': '无效操作'})

@app.route('/api/system/logs')
@login_required
def api_system_logs():
    """获取系统日志API"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': '权限不足'})
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    log_data = []
    for log in logs.items:
        log_data.append({
            'id': log.id,
            'username': log.user.username if log.user else '系统',
            'action_type': log.action_type,
            'action_details': log.action_details,
            'ip_address': log.ip_address,
            'timestamp': log.timestamp.isoformat()
        })
    
    return jsonify({
        'success': True,
        'logs': log_data,
        'total': logs.total,
        'pages': logs.pages,
        'current_page': page
    })

# ==================== 用户个人资料 ====================

@app.route('/user/profile')
@login_required
def user_profile():
    """用户个人资料页面"""
    return render_template('user_profile.html')

@app.route('/api/user/profile', methods=['POST'])
@login_required
def api_user_profile():
    """更新用户个人资料API"""
    data = request.get_json()
    
    try:
        if 'password' in data and data['password']:
            if len(data['password']) < 6:
                return jsonify({'success': False, 'message': '密码长度至少6位'})
            current_user.set_password(data['password'])
        
        if 'department' in data:
            current_user.department = data['department']
        
        db.session.commit()
        log_action('个人设置', '更新个人资料')
        
        return jsonify({'success': True, 'message': '个人资料更新成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.errorhandler(413)
def too_large(error):
    return jsonify({'success': False, 'message': '文件大小超过限制'}), 413

# ==================== 初始化应用 ====================

def init_app():
    """初始化应用"""
    with app.app_context():
        # 创建数据库表
        db.create_all()
        
        # 创建默认管理员用户
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                department='系统管理部',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("默认管理员账户已创建: admin/admin123")
        
        # 添加示例数据（如果数据库为空）
        if TreeData.query.count() == 0:
            add_sample_data()
            print("示例数据已添加")

def add_sample_data():
    """添加示例樟树数据"""
    sample_data = [
        TreeData(
            region='天河区',
            tree_age=150,
            dbh=120.5,
            tree_height=15.2,
            annual_carbon_seq=85.6,
            growth_status='正常',
            soil_compactness='中等',
            total_precipitation=1680,
            avg_temperature=22.5,
            avg_humidity=78,
            avg_wind_speed=2.1,
            altitude=45,
            recorded_year=2024,
            created_by=1
        ),
        TreeData(
            region='越秀区',
            tree_age=200,
            dbh=150.3,
            tree_height=18.5,
            annual_carbon_seq=95.2,
            growth_status='正常',
            soil_compactness='疏松',
            total_precipitation=1720,
            avg_temperature=22.8,
            avg_humidity=76,
            avg_wind_speed=1.9,
            altitude=32,
            recorded_year=2024,
            created_by=1
        ),
        TreeData(
            region='海珠区',
            tree_age=100,
            dbh=90.7,
            tree_height=12.3,
            annual_carbon_seq=65.3,
            growth_status='衰弱',
            soil_compactness='紧密',
            total_precipitation=1550,
            avg_temperature=23.1,
            avg_humidity=72,
            avg_wind_speed=2.8,
            altitude=55,
            recorded_year=2024,
            created_by=1
        ),
        TreeData(
            region='荔湾区',
            tree_age=250,
            dbh=160.8,
            tree_height=20.1,
            annual_carbon_seq=102.1,
            growth_status='正常',
            soil_compactness='中等',
            total_precipitation=1750,
            avg_temperature=22.3,
            avg_humidity=80,
            avg_wind_speed=1.8,
            altitude=28,
            recorded_year=2024,
            created_by=1
        ),
        TreeData(
            region='白云区',
            tree_age=180,
            dbh=130.2,
            tree_height=16.7,
            annual_carbon_seq=88.7,
            growth_status='正常',
            soil_compactness='疏松',
            total_precipitation=1620,
            avg_temperature=22.6,
            avg_humidity=75,
            avg_wind_speed=2.3,
            altitude=40,
            recorded_year=2024,
            created_by=1
        ),
        TreeData(
            region='黄埔区',
            tree_age=300,
            dbh=180.5,
            tree_height=22.3,
            annual_carbon_seq=115.8,
            growth_status='濒危',
            soil_compactness='紧密',
            total_precipitation=1480,
            avg_temperature=23.5,
            avg_humidity=68,
            avg_wind_speed=3.2,
            altitude=60,
            recorded_year=2024,
            created_by=1
        )
    ]
    
    for data in sample_data:
        db.session.add(data)
    db.session.commit()

# ==================== 健康检查 ====================

@app.route('/health')
def health_check():
    """健康检查端点"""
    try:
        # 检查数据库连接
        db.session.execute('SELECT 1')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database': 'connected',
            'version': '2.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

# ==================== 主程序入口 ====================

# 记录应用启动时间
app_startup_time = datetime.now()

if __name__ == '__main__':
    # 初始化应用
    init_app()
    
    print("=" * 60)
    print("🌳 融合机器学习的华南樟树生态因子关联解析与碳汇功能预测系统 V1.0")
    print("=" * 60)
    print(f"启动时间: {app_startup_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"访问地址: http://localhost:5000")
    print(f"默认管理员账户: admin / admin123")
    print("=" * 60)
    print("核心功能模块:")
    print("  ✅ 数据管理 - 数据录入、查询、导入导出")
    print("  ✅ 生长评估 - 单株/批量生长状态评估")
    print("  ✅ 碳汇评估 - 碳汇能力计算与分析")
    print("  ✅ 关联分析 - 多变量相关性分析")
    print("  ✅ 情景预测 - 未来趋势预测")
    print("  ✅ 系统管理 - 用户权限、日志管理")
    print("=" * 60)
    
    # 运行应用
    app.run(
        debug=True, 
        host='0.0.0.0', 
        port=5000,
        threaded=True
    )