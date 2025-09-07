import os
import logging
from datetime import timedelta
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.permanent_session_lifetime = timedelta(minutes=15)

# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///vehicle_marketplace.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Upload folder for vehicle images
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Import and initialize db
from models import db
db.init_app(app)

# Apply proxy fix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize database and create admin user
with app.app_context():
    # Create all tables
    db.create_all()
    
    # Create admin user if not exists
    from models import Admin
    from werkzeug.security import generate_password_hash
    
    admin = Admin.query.first()
    if not admin:
        admin_password = os.environ.get("ADMIN_PASSWORD", "DiegoPortaz7")
        admin = Admin(
            username="Ryoma94",
            password_hash=generate_password_hash(admin_password)
        )
        db.session.add(admin)
        db.session.commit()
        logging.info("Admin user created with password: " + admin_password)

# Import routes after db is initialized
import routes

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)