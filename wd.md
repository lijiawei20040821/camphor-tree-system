这是一个基于您提供的所有代码文件生成的完整 `README.md` 文档。它涵盖了项目介绍、技术栈、安装运行指南、功能模块说明以及项目结构。

您可以将以下内容保存为项目根目录下的 `README.md` 文件。

---

# 🌳 广东樟树生态监测与碳汇评估系统 (V2.0)

这是一个现代化的生态监测 Web 平台，专为广东樟树林业管理设计。系统集成了数据可视化、机器学习预测（RandomForest & XGBoost）、碳汇计算以及情景模拟功能，旨在实现科学监测、精准评估与智能预测。

---

## ✨ 核心功能

1. **📊 系统仪表盘 (Dashboard)**
* 实时展示树木总数、生长状态分布（正常/衰弱/濒危）、平均碳汇量。
* 基于 `Chart.js` 的动态碳汇趋势图和区域统计。
* 数据库聚合查询优化，解决 N+1 问题，高性能加载。


2. **🗃️ 数据管理 (Data Management)**
* 支持 Excel/CSV 文件的批量导入与导出。
* 提供 CRUD（增删改查）操作，支持分页浏览。
* 自动数据清洗与异常值检测。


3. **📈 生长评估 (Growth Assessment)**
* **AI 驱动**：利用随机森林 (Random Forest) 模型预测树木生长状态。
* 支持单株精细评估与批量文件评估。
* 提供置信度分析与针对性的养护建议。


4. **🍃 碳汇评估 (Carbon Sequestration)**
* 基于 XGBoost 回归模型的高精度碳汇量计算。
* 分析环境因子（湿度、土壤紧密度等）对固碳能力的影响。
* 生态价值转化（等效植树量、经济价值估算）。


5. **🔗 关联分析 (Correlation Analysis)**
* **科学实验室风格**：单变量分布、双变量相关性、多变量热力图矩阵。
* 支持 Pearson/Spearman/Kendall 相关系数计算。
* 后端生成 Base64 格式的高清统计图表。


6. **🔮 情景预测 (Scenario Prediction)**
* 模拟未来气候变化（如气温升高、极端降水）对生态系统的影响。
* 提供未来 10-30 年的碳汇趋势预测与风险预警。
* 交互式参数调节滑块。


7. **⚙️ 系统管理 (System Management)**
* 基于 RBAC 的用户权限管理（管理员/普通用户/科研人员）。
* 安全审计日志：记录登录、删除、导出等关键操作。
* 系统维护：数据库备份、缓存清理、模型重训练。



---

## 🛠️ 技术栈

### 后端 (Backend)

* **核心框架**: Flask 2.3
* **数据库**: SQLite (默认) / SQLAlchemy (ORM)
* **数据分析**: Pandas, NumPy
* **机器学习**: Scikit-learn (RandomForest), XGBoost
* **绘图库**: Matplotlib, Seaborn (配置为非交互式后端 'Agg')
* **安全**: BCrypt 密码加密, Flask-Login 认证

### 前端 (Frontend)

* **UI 框架**: Bootstrap 5 (定制 Eco-Theme 主题)
* **图表库**: Chart.js
* **模板引擎**: Jinja2
* **交互**: 原生 JavaScript (Fetch API), 响应式设计

### 部署与运维

* **容器化**: Docker, Docker Compose
* **测试**: Unittest

---

## 🚀 快速开始

### 方式一：本地直接运行

1. **克隆项目**
```bash
git clone <repository_url>
cd camphor-system

```


2. **创建并激活虚拟环境**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/MacOS
python3 -m venv venv
source venv/bin/activate

```


3. **安装依赖**
```bash
pip install -r requirements.txt

```


4. **初始化静态资源**
确保目录下存在 `static/css/style.css` 和 `static/js/main.js`（如未创建，请手动创建空文件或从之前的步骤中复制）。
5. **运行应用**
```bash
python run.py

```


* 系统会自动初始化数据库并创建默认管理员账户。
* 系统会自动使用示例数据训练 AI 模型。
* 访问地址: `http://localhost:5000`


6. **登录**
* **用户名**: `admin`
* **密码**: `admin123`



---

### 方式二：使用 Docker 部署 (推荐)

1. **构建并启动容器**
确保已安装 Docker 和 Docker Compose。
```bash
docker-compose up --build -d

```


2. **访问系统**
在浏览器中打开 `http://localhost:5000`。
3. **查看日志**
```bash
docker-compose logs -f

```


4. **停止服务**
```bash
docker-compose down

```



---

## 📂 项目结构

```text
.
├── app.py                  # Flask 主程序入口，包含路由和视图逻辑
├── models.py               # 数据库模型 (User, TreeData, SystemLog)
├── ml_models.py            # 机器学习模型类 (GrowthStatusModel, CarbonSequestrationModel)
├── utils.py                # 工具函数 (数据清洗, 绘图, 报告生成)
├── config.py               # 配置文件 (Dev/Prod/Test)
├── run.py                  # 启动脚本
├── requirements.txt        # Python 依赖列表
├── docker-compose.yml      # Docker 编排文件
├── Dockerfile              # Docker 镜像构建文件
├── test_system.py          # 单元测试
├── static/                 # 静态资源
│   ├── css/                # 样式表
│   ├── js/                 # JavaScript 脚本
│   └── img/                # 图片资源
├── templates/              # HTML 模板
│   ├── base.html           # 基础布局
│   ├── login.html          # 登录页
│   ├── dashboard.html      # 仪表盘
│   ├── data_management.html # 数据管理
│   ├── growth_assessment.html # 生长评估
│   ├── carbon_assessment.html # 碳汇评估
│   ├── correlation_analysis.html # 关联分析
│   ├── scenario_prediction.html  # 情景预测
│   ├── system_management.html    # 系统管理
│   ├── 404.html            # 404 错误页
│   └── 500.html            # 500 错误页
└── uploads/                # 上传文件存储目录

```

---

## 🧪 测试

项目包含完整的单元测试，覆盖了用户认证、数据导入等核心功能。

```bash
python test_system.py

```

---

## ⚠️ 注意事项

1. **首次启动**: 系统首次启动时会检查 `models/` 目录下是否存在 `.pkl` 模型文件。如果不存在，会自动使用内置的样本数据训练模型。这可能需要几秒钟。
2. **生产环境**: 在部署到生产环境前，请务必在 `config.py` 或环境变量中修改 `SECRET_KEY`。
3. **文件上传**: 默认支持 `.xlsx`, `.xls`, `.csv` 格式，最大文件大小限制为 16MB。

---

## 📝 版权信息

© 2024 广东林业科学研究院 - 樟树生态监测系统 V2.0
保留所有权利。