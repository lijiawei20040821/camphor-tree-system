from app import app, init_app
import os

if __name__ == '__main__':
    init_app()

    env = os.environ.get('FLASK_ENV', 'development')
    debug = env == 'development'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))

    print(f"启动融合机器学习的华南樟树生态因子关联解析与碳汇功能预测系统V1.0...")
    print(f"环境: {env}")
    print(f"地址: http://{host}:{port}")
    print(f"调试模式: {debug}")

    app.run(debug=debug, host=host, port=port)