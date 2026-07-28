from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import bcrypt

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(100), nullable=False, default='未设置')
    role = db.Column(db.String(20), nullable=False, default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))


class TreeData(db.Model):
    __tablename__ = 'tree_data'
    id = db.Column(db.Integer, primary_key=True)
    region = db.Column(db.String(50), nullable=False, index=True)
    tree_age = db.Column(db.Float, nullable=False)
    dbh = db.Column(db.Float, nullable=False)
    tree_height = db.Column(db.Float, nullable=False)
    annual_carbon_seq = db.Column(db.Float)
    growth_status = db.Column(db.String(20), index=True)
    soil_compactness = db.Column(db.String(20))
    total_precipitation = db.Column(db.Float)
    avg_temperature = db.Column(db.Float)
    avg_humidity = db.Column(db.Float)
    avg_wind_speed = db.Column(db.Float)
    altitude = db.Column(db.Float)
    recorded_year = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))


class SystemLog(db.Model):
    __tablename__ = 'system_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    action_type = db.Column(db.String(50), nullable=False, index=True)
    action_details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref='logs')