#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест за връзка с базата данни и създаване на таблиците за МГ LIVE
"""

import sys
import os

# Добавяме текущата папка в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, create_tables, Folder, Message, SystemSettings
from config import Config

def test_database_connection():
    """Тества връзката с базата данни"""
    print("🔍 Тестване на връзката с базата данни...")
    
    try:
        with app.app_context():
            # Тестваме връзката (нов синтаксис за SQLAlchemy 2.x)
            from sqlalchemy import text
            result = db.session.execute(text('SELECT 1'))
            result.fetchone()
            print("✅ Връзката с MySQL базата данни е успешна!")
            
            # Показваме информация за базата
            result = db.session.execute(text('SELECT DATABASE()'))
            db_name = result.fetchone()[0]
            print(f"📄 Активна база данни: {db_name}")
            
            return True
            
    except Exception as e:
        print(f"❌ Грешка при свързване с базата данни: {e}")
        print("\n🔧 Възможни причини:")
        print("   - MySQL не е стартиран в XAMPP")
        print("   - Базата данни 'mg_live' не съществува")
        print("   - Грешни настройки в config.py")
        return False

def create_database_tables():
    """Създава таблиците в базата данни"""
    print("\n🔨 Създаване на таблиците...")
    
    try:
        with app.app_context():
            create_tables()
            print("✅ Всички таблици са създадени успешно!")
            
            # Показваме създадените таблици
            from sqlalchemy import text
            result = db.session.execute(text('SHOW TABLES'))
            tables = [row[0] for row in result.fetchall()]
            
            print(f"📋 Създадени таблици ({len(tables)}):")
            for table in tables:
                print(f"   - {table}")
            
            return True
            
    except Exception as e:
        print(f"❌ Грешка при създаване на таблиците: {e}")
        return False

def add_sample_data():
    """Добавя примерни данни за тестване"""
    print("\n📝 Добавяне на примерни данни...")
    
    try:
        with app.app_context():
            # Проверяваме дали вече има данни
            existing_folders = Folder.query.count()
            existing_messages = Message.query.count()
            
            if existing_folders > 0 or existing_messages > 0:
                print(f"ℹ️  Вече има данни в базата (папки: {existing_folders}, съобщения: {existing_messages})")
                return True
            
            # Добавяме примерна папка
            sample_folder = Folder(
                name='sample_images',
                display_name='Примерни снимки',
                path=os.path.join(Config.FOLDERS_PATH, 'sample_images'),
                is_active=True,
                slide_duration=5,
                priority=1
            )
            db.session.add(sample_folder)
            
            # Добавяме примерни съобщения
            welcome_message = Message(
                text='Добре дошли в МГ LIVE - система за информационни дисплеи на Математическа гимназия "Атанас Радев" - Ямбол',
                is_urgent=False,
                is_active=True,
                priority=1
            )
            db.session.add(welcome_message)
            
            test_message = Message(
                text='Това е тестово съобщение за проверка на бягащия текст',
                is_urgent=False,
                is_active=True,
                priority=0
            )
            db.session.add(test_message)
            
            urgent_message = Message(
                text='ВАЖНО: Тестово спешно съобщение',
                is_urgent=True,
                is_active=True,
                priority=2
            )
            db.session.add(urgent_message)
            
            # Записваме промените
            db.session.commit()
            
            print("✅ Примерни данни добавени успешно!")
            print("   - 1 примерна папка")
            print("   - 3 примерни съобщения")
            
            return True
            
    except Exception as e:
        print(f"❌ Грешка при добавяне на примерни данни: {e}")
        db.session.rollback()
        return False

def show_database_status():
    """Показва статуса на базата данни"""
    print("\n📊 Статус на базата данни:")
    
    try:
        with app.app_context():
            folders_count = Folder.query.count()
            active_folders = Folder.query.filter_by(is_active=True).count()
            messages_count = Message.query.count()
            active_messages = Message.query.filter_by(is_active=True).count()
            settings_count = SystemSettings.query.count()
            
            print(f"   📁 Папки: {folders_count} общо, {active_folders} активни")
            print(f"   💬 Съобщения: {messages_count} общо, {active_messages} активни")
            print(f"   ⚙️  Настройки: {settings_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Грешка при извличане на статуса: {e}")
        return False

def main():
    """Главна функция за тестване"""
    print("=" * 60)
    print("🚀 МГ LIVE - Тест на базата данни")
    print("=" * 60)
    
    # Показваме конфигурацията
    print(f"🔧 MySQL Host: {Config.MYSQL_HOST}")
    print(f"🔧 MySQL User: {Config.MYSQL_USER}")
    print(f"🔧 Database: {Config.MYSQL_DB}")
    print(f"🔧 Connection: {Config.SQLALCHEMY_DATABASE_URI}")
    
    # Тестваме връзката
    if not test_database_connection():
        print("\n❌ Тестът неуспешен! Моля, проверете настройките.")
        return False
    
    # Създаваме таблиците
    if not create_database_tables():
        print("\n❌ Неуспешно създаване на таблиците!")
        return False
    
    # Добавяме примерни данни
    if not add_sample_data():
        print("\n⚠️  Предупреждение: Проблем с примерните данни")
    
    # Показваме статуса
    show_database_status()
    
    print("\n" + "=" * 60)
    print("✅ Базата данни е готова за работа!")
    print("🌐 Можете да стартирате МГ LIVE с: python app.py")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    main()