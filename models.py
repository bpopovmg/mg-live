from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Инициализация на базата данни
db = SQLAlchemy()

class Folder(db.Model):
    """Таблица за папки със снимки"""
    __tablename__ = 'folders'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    display_name = db.Column(db.String(200), nullable=False)  # Име за показване
    path = db.Column(db.String(255), nullable=False)  # Път до папката
    is_active = db.Column(db.Boolean, default=True)  # Дали се показва в slideshow
    slide_duration = db.Column(db.Integer, default=5)  # Секунди за показване на снимка
    priority = db.Column(db.Integer, default=0)  # Приоритет на папката (по-високо = първо)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Folder {self.name}>'
    
    def get_images(self):
        """Връща всички валидни снимки от папката"""
        from config import Config
        
        if not os.path.exists(self.path):
            return []
        
        images = []
        allowed_extensions = Config.ALLOWED_EXTENSIONS
        
        for filename in os.listdir(self.path):
            if filename.lower().split('.')[-1] in allowed_extensions:
                images.append({
                    'filename': filename,
                    'path': os.path.join(self.path, filename).replace('\\', '/'),
                    'url': f'/uploads/folders/{self.name}/{filename}'
                })
        
        # Сортиране по име на файла
        images.sort(key=lambda x: x['filename'])
        return images
    
    def get_image_count(self):
        """Връща броя снимки в папката"""
        return len(self.get_images())

class Message(db.Model):
    """Таблица за съобщения (бягащ текст)"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    is_urgent = db.Column(db.Boolean, default=False)  # Спешно съобщение (мига)
    is_active = db.Column(db.Boolean, default=True)  # Дали се показва
    priority = db.Column(db.Integer, default=0)  # Приоритет (по-високо = първо)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)  # От кога да се показва
    end_date = db.Column(db.DateTime, nullable=True)  # До кога да се показва
    created_by = db.Column(db.String(50), default='admin')  # Кой е създал съобщението
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message {self.id}: {self.text[:50]}...>'
    
    def is_current(self):
        """Проверява дали съобщението трябва да се показва сега"""
        now = datetime.utcnow()
        
        # Проверка за активност
        if not self.is_active:
            return False
        
        # Проверка за начална дата
        if self.start_date and now < self.start_date:
            return False
        
        # Проверка за крайна дата
        if self.end_date and now > self.end_date:
            return False
        
        return True

class SystemSettings(db.Model):
    """Таблица за системни настройки"""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Setting {self.key}: {self.value}>'

class WeatherCache(db.Model):
    """Таблица за кеширане на времето"""
    __tablename__ = 'weather_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float, nullable=False)
    weather_code = db.Column(db.Integer, nullable=False)  # Open-Meteo weather code
    weather_description = db.Column(db.String(100), nullable=False)
    wind_speed = db.Column(db.Float, default=0)
    humidity = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Weather {self.temperature}°C, {self.weather_description}>'
    
    def is_expired(self, minutes=30):
        """Проверява дали данните за времето са остарели"""
        from datetime import timedelta
        return (datetime.utcnow() - self.last_updated) > timedelta(minutes=minutes)

def init_default_settings():
    """Инициализира настройките по подразбиране"""
    default_settings = [
        ('slideshow_speed', '50', 'Скорост на бягащия текст (пиксели/сек)'),
        ('slide_duration', '5', 'Времетраене на снимка (секунди)'),
        ('weather_update_interval', '30', 'Интервал за обновяване на времето (минути)'),
        ('display_clock', 'true', 'Показване на часовник'),
        ('display_weather', 'true', 'Показване на времето'),
        ('theme', 'default', 'Тема на интерфейса'),
        ('emergency_message', '', 'Спешно съобщение (празно = не се показва)'),
        ('school_name', 'МГ "Атанас Радев" - Ямбол', 'Име на училището'),
        ('admin_password_hash', '', 'Hash на администраторската парола')
    ]
    
    for key, value, description in default_settings:
        if not SystemSettings.query.filter_by(key=key).first():
            setting = SystemSettings(key=key, value=value, description=description)
            db.session.add(setting)
    
    db.session.commit()

def create_tables():
    """Създава всички таблици в базата данни"""
    db.create_all()
    init_default_settings()
    print("✅ База данни и таблици са създадени успешно!")

def get_setting(key, default=None):
    """Взема настройка от базата данни"""
    setting = SystemSettings.query.filter_by(key=key).first()
    return setting.value if setting else default

def set_setting(key, value, description=None):
    """Записва настройка в базата данни"""
    setting = SystemSettings.query.filter_by(key=key).first()
    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = SystemSettings(key=key, value=value, description=description)
        db.session.add(setting)
    
    db.session.commit()
    return setting