"""生产环境部署脚本 - 支持 Render.com / 本地 / Docker"""
import os
from app import app, init_app

if __name__ == '__main__':
    init_app()
    
    from waitress import serve
    
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))
    threads = int(os.environ.get('THREADS', 4))
    
    print(f"=" * 60)
    print(f"  融合机器学习的华南樟树生态因子关联解析与碳汇功能预测系统")
    print(f"  生产模式启动")
    print(f"=" * 60)
    print(f"  服务地址: http://{host}:{port}")
    print(f"  工作线程: {threads}")
    print(f"  调试模式: 关闭")
    print(f"  按 Ctrl+C 停止服务")
    print(f"=" * 60)
    
    serve(app, host=host, port=port, threads=threads)
