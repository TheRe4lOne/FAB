from src.api import *
from src.app import app

def register_routes():
    app.register_blueprint(users, url_prefix="/api/users")
    app.register_blueprint(ea_accounts, url_prefix="/api/accounts")
    app.register_blueprint(auth, url_prefix="/api/auth")
    app.register_blueprint(web_app, url_prefix="/api/web-app")
