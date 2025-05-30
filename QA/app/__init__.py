from flask import Flask

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    
    # 注册路由
    from . import routes
    app.register_blueprint(routes.bp)
    
    return app
