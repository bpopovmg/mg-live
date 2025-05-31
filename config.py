import os
from dotenv import load_dotenv

# Зареди настройки от .env файл (ако съществува)
load_dotenv()

class Config:
    """Основни настройки за МГ LIVE системата"""
    
    # Основни Flask настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mg-live-secret-key-2025'
    
    # MySQL Database настройки
    MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
    MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or ''  # Празна парола за XAMPP
    MYSQL_DB = os.environ.get('MYSQL_DB') or 'mg_live'
    
    # SQLAlchemy настройки
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Папки за файлове
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    FOLDERS_PATH = os.path.join(UPLOAD_FOLDER, 'folders')
    
    # Позволени файлови формати за снимки
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    
    # Slideshow настройки
    SLIDESHOW_SPEED = 50  # пиксели в секунда за бягащия текст
    DEFAULT_SLIDE_DURATION = 5  # секунди за показване на снимка
    
    # Weather API настройки (Open-Meteo - безплатно, няма нужда от API ключ)
    WEATHER_API_URL = 'https://api.open-meteo.com/v1/forecast'
    WEATHER_LATITUDE = 42.4833  # Ямбол координати
    WEATHER_LONGITUDE = 26.5167
    WEATHER_UPDATE_INTERVAL = 30  # минути
    
    # Администраторски достъп
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'mglive2025'
    
    # Максимален размер на файл (16MB)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# Развойна среда настройки
class DevelopmentConfig(Config):
    DEBUG = True
    
# Продукционна среда настройки  
class ProductionConfig(Config):
    DEBUG = False

# Избор на конфигурация
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}