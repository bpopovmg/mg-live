from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import requests
from functools import wraps
import json
import re

# ============================================================================
# FLASK КОНФИГУРАЦИЯ
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mglive.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['JSON_AS_ASCII'] = False  # Позволява Unicode в JSON отговори

# Инициализация на базата данни
db = SQLAlchemy(app)

# Създаване на upload папката ако не съществува
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ============================================================================
# МОДЕЛИ НА БАЗАТА ДАННИ
# ============================================================================

class User(db.Model):
    """Модел за потребители"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Folder(db.Model):
    """Модел за папки с изображения"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(150), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def image_count(self):
        """Брой изображения в папката"""
        folder_path = os.path.join('static', 'uploads', self.name)
        if os.path.exists(folder_path):
            return len([f for f in os.listdir(folder_path) 
                       if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))])
        return 0

class Message(db.Model):
    """Модел за бягащи съобщения"""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_urgent = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=0)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80), nullable=False, default='admin')

    def is_current(self):
        """Проверява дали съобщението е активно в момента"""
        now = datetime.utcnow()
        
        # Проверка за начална дата
        if self.start_date and now < self.start_date:
            return False
            
        # Проверка за крайна дата
        if self.end_date and now > self.end_date:
            return False
            
        return True

# ============================================================================
# ДЕКОРАТОРИ
# ============================================================================

def login_required(f):
    """Декоратор за проверка на логин"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# MAIN ROUTE
# ============================================================================

@app.route('/')
def display():
    """Главен дисплей за показване на съдържание"""
    # Вземаме активни папки
    active_folders = Folder.query.filter_by(is_active=True).order_by(Folder.priority.desc()).all()
    
    # Подготвяме структурата за изображения
    slideshow_data = []
    for folder in active_folders:
        folder_images = []
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder.name)
        
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    image_url = url_for('static', filename=f'uploads/{folder.name}/{filename}')
                    folder_images.append({
                        'url': image_url,
                        'caption': f"{folder.name} - {filename}"
                    })
        
        if folder_images:
            slideshow_data.extend(folder_images)
    
    # Вземаме активни съобщения
    current_messages = []
    try:
        all_messages = Message.query.filter_by(is_active=True).all()
        current_messages = [msg for msg in all_messages if msg.is_current()]
        current_messages.sort(key=lambda x: x.priority, reverse=True)
    except Exception as e:
        print(f"Грешка при зареждане на съобщения: {e}")
        current_messages = []
    
    return render_template('display.html', 
                         slideshow_data=slideshow_data,
                         messages=current_messages)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/weather')
def api_weather():
    """API за времето използвайки Open-Meteo"""
    try:
        # Координати на Ямбол
        lat = 42.4833
        lon = 26.5000
        
        # Open-Meteo API за текущо време
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=Europe/Sofia"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current = data.get('current', {})
            
            # Weather code към описание
            weather_descriptions = {
                0: "Ясно небе",
                1: "Предимно ясно", 
                2: "Частично облачно",
                3: "Облачно",
                45: "Мъгла",
                48: "Заскрежаваща мъгла",
                51: "Слаб дъжд",
                53: "Умерен дъжд", 
                55: "Силен дъжд",
                61: "Слаб дъжд",
                63: "Умерен дъжд",
                65: "Силен дъжд",
                71: "Слаб снеговалеж",
                73: "Умерен снеговалеж",
                75: "Силен снеговалеж",
                80: "Слаби превалявания",
                81: "Умерени превалявания",
                82: "Силни превалявания",
                95: "Гръмотевици"
            }
            
            weather_code = current.get('weather_code', 0)
            description = weather_descriptions.get(weather_code, "Ясно")
            
            result = {
                'temperature': int(round(current.get('temperature_2m', 22))),
                'description': description,
                'humidity': int(current.get('relative_humidity_2m', 45)),
                'wind_speed': round(current.get('wind_speed_10m', 3.2), 1),
                'icon': '01d'
            }
            
            # Връщаме с правилно Unicode кодиране
            json_str = json.dumps(result, ensure_ascii=False, indent=2)
            return Response(json_str, content_type='application/json; charset=utf-8')
        else:
            # Fallback
            result = {
                'temperature': 22,
                'description': 'Слънчево',
                'humidity': 45,
                'wind_speed': 3.2,
                'icon': '01d'
            }
            json_str = json.dumps(result, ensure_ascii=False, indent=2)
            return Response(json_str, content_type='application/json; charset=utf-8')
        
    except Exception as e:
        print(f"Weather API error: {e}")
        result = {
            'temperature': 22,
            'description': 'Слънчево', 
            'humidity': 45,
            'wind_speed': 3.2,
            'icon': '01d'
        }
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        return Response(json_str, content_type='application/json; charset=utf-8')

@app.route('/api/messages')
def api_messages():
    """API за активни съобщения"""
    try:
        all_messages = Message.query.filter_by(is_active=True).all()
        current_messages = [msg for msg in all_messages if msg.is_current()]
        current_messages.sort(key=lambda x: x.priority, reverse=True)
        
        return jsonify([{
            'id': msg.id,
            'text': msg.text,
            'is_urgent': msg.is_urgent,
            'priority': msg.priority
        } for msg in current_messages])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# АДМИНИСТРАТОРСКИ ROUTES - ПАПКИ И ИЗОБРАЖЕНИЯ
# ============================================================================

@app.route('/admin/folders')
@login_required
def admin_folders():
    """Управление на папки"""
    folders = Folder.query.order_by(Folder.priority.desc(), Folder.name).all()
    return render_template('admin/folders.html', folders=folders)

@app.route('/admin/folders/new', methods=['GET', 'POST'])
@login_required
def admin_folders_new():
    """Създаване на нова папка"""
    if request.method == 'POST':
        try:
            name = request.form['name'].strip().lower()
            display_name = request.form['display_name'].strip()
            priority = int(request.form.get('priority', 0))
            
            # Валидация на името
            if not re.match(r'^[a-z0-9_-]+$', name):
                flash('Името на папката може да съдържа само малки букви, цифри, тире и долна черта!', 'error')
                return redirect(request.url)
            
            if not name or not display_name:
                flash('Името и показваното име са задължителни!', 'error')
                return redirect(request.url)
            
            # Проверка дали папката вече съществува
            if Folder.query.filter_by(name=name).first():
                flash('Папка с това име вече съществува!', 'error')
                return redirect(request.url)
            
            # Създаване на папката в базата данни
            folder = Folder(
                name=name,
                display_name=display_name,
                priority=priority,
                is_active=True
            )
            
            db.session.add(folder)
            db.session.commit()
            
            # Създаване на папката в файловата система
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], name)
            os.makedirs(folder_path, exist_ok=True)
            
            flash('Папката е създадена успешно!', 'success')
            return redirect(url_for('admin_folders'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Грешка при създаване на папката: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('admin/folder_form.html', action='new')

@app.route('/admin/folders/edit/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def admin_folders_edit(folder_id):
    """Редактиране на папка"""
    folder = Folder.query.get_or_404(folder_id)
    
    if request.method == 'POST':
        try:
            display_name = request.form['display_name'].strip()
            priority = int(request.form.get('priority', 0))
            
            if not display_name:
                flash('Показваното име е задължително!', 'error')
                return redirect(request.url)
            
            folder.display_name = display_name
            folder.priority = priority
            
            db.session.commit()
            
            flash('Папката е обновена успешно!', 'success')
            return redirect(url_for('admin_folders'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Грешка при обновяване на папката: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('admin/folder_form.html', action='edit', folder=folder)

@app.route('/admin/folders/toggle/<int:folder_id>')
@login_required
def admin_folders_toggle(folder_id):
    """Превключване на активност на папка"""
    try:
        folder = Folder.query.get_or_404(folder_id)
        folder.is_active = not folder.is_active
        db.session.commit()
        
        status = "активирана" if folder.is_active else "деактивирана"
        flash(f'Папката е {status} успешно!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Грешка при промяна на статуса: {str(e)}', 'error')
    
    return redirect(url_for('admin_folders'))

@app.route('/admin/folders/delete/<int:folder_id>')
@login_required
def admin_folders_delete(folder_id):
    """Изтриване на папка"""
    try:
        folder = Folder.query.get_or_404(folder_id)
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder.name)
        
        # Изтриване на папката от файловата система
        import shutil
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        
        # Изтриване от базата данни
        db.session.delete(folder)
        db.session.commit()
        
        flash('Папката и всички нейни файлове са изтрити успешно!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Грешка при изтриване на папката: {str(e)}', 'error')
    
    return redirect(url_for('admin_folders'))

@app.route('/admin/folders/<int:folder_id>/images')
@login_required
def admin_folder_images(folder_id):
    """Управление на изображения в папка"""
    folder = Folder.query.get_or_404(folder_id)
    
    # Вземаме всички изображения от папката
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder.name)
    images = []
    
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                file_path = os.path.join(folder_path, filename)
                file_size = os.path.getsize(file_path)
                file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                images.append({
                    'filename': filename,
                    'url': url_for('static', filename=f'uploads/{folder.name}/{filename}'),
                    'size': file_size,
                    'modified': file_modified
                })
    
    # Сортираме по дата на модификация (най-новите първо)
    images.sort(key=lambda x: x['modified'], reverse=True)
    
    return render_template('admin/folder_images.html', folder=folder, images=images)

@app.route('/admin/folders/<int:folder_id>/upload', methods=['GET', 'POST'])
@login_required
def admin_folder_upload(folder_id):
    """Upload на изображения в папка"""
    folder = Folder.query.get_or_404(folder_id)
    
    if request.method == 'POST':
        try:
            # Проверяваме дали са качени файлове
            if 'files' not in request.files:
                flash('Няма избрани файлове!', 'error')
                return redirect(request.url)
            
            files = request.files.getlist('files')
            if not files or files[0].filename == '':
                flash('Няма избрани файлове!', 'error')
                return redirect(request.url)
            
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder.name)
            os.makedirs(folder_path, exist_ok=True)
            
            uploaded_count = 0
            allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
            
            for file in files:
                if file and file.filename:
                    # Проверяваме разширението
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    if file_ext not in allowed_extensions:
                        continue
                    
                    # Сигурно име на файла
                    import uuid
                    safe_filename = f"{uuid.uuid4().hex}{file_ext}"
                    
                    # Запазваме файла
                    file_path = os.path.join(folder_path, safe_filename)
                    file.save(file_path)
                    uploaded_count += 1
            
            if uploaded_count > 0:
                flash(f'Успешно качени {uploaded_count} изображения!', 'success')
            else:
                flash('Няма валидни изображения за качване!', 'warning')
            
            return redirect(url_for('admin_folder_images', folder_id=folder.id))
            
        except Exception as e:
            flash(f'Грешка при качване на файловете: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('admin/upload_form.html', folder=folder)

@app.route('/admin/folders/<int:folder_id>/delete-image/<filename>')
@login_required
def admin_delete_image(folder_id, filename):
    """Изтриване на изображение"""
    try:
        folder = Folder.query.get_or_404(folder_id)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], folder.name, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('Изображението е изтрито успешно!', 'success')
        else:
            flash('Файлът не съществува!', 'error')
        
    except Exception as e:
        flash(f'Грешка при изтриване на файла: {str(e)}', 'error')
    
    return redirect(url_for('admin_folder_images', folder_id=folder_id))

# ============================================================================
# АДМИНИСТРАТОРСКИ ROUTES - СЪОБЩЕНИЯ
# ============================================================================

@app.route('/admin/messages')
@login_required
def admin_messages():
    """Управление на съобщения"""
    messages = Message.query.order_by(Message.priority.desc(), Message.created_at.desc()).all()
    return render_template('admin/messages.html', messages=messages)

@app.route('/admin/messages/new', methods=['GET', 'POST'])
@login_required
def admin_messages_new():
    """Създаване на ново съобщение"""
    if request.method == 'POST':
        try:
            text = request.form['text'].strip()
            is_urgent = 'is_urgent' in request.form
            priority = int(request.form.get('priority', 0))
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            
            if not text:
                flash('Текстът на съобщението не може да бъде празен!', 'error')
                return redirect(request.url)
            
            # Парсиране на датите
            start_datetime = None
            end_datetime = None
            
            if start_date:
                try:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            
            if end_date:
                try:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Създаване на съобщението
            message = Message(
                text=text,
                is_urgent=is_urgent,
                is_active=True,
                priority=priority,
                start_date=start_datetime,
                end_date=end_datetime,
                created_by=session.get('username', 'admin')
            )
            
            db.session.add(message)
            db.session.commit()
            
            flash('Съобщението е създадено успешно!', 'success')
            return redirect(url_for('admin_messages'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Грешка при създаване на съобщението: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('admin/message_form.html', action='new')

@app.route('/admin/messages/edit/<int:message_id>', methods=['GET', 'POST'])
@login_required
def admin_messages_edit(message_id):
    """Редактиране на съобщение"""
    message = Message.query.get_or_404(message_id)
    
    if request.method == 'POST':
        try:
            text = request.form['text'].strip()
            is_urgent = 'is_urgent' in request.form
            priority = int(request.form.get('priority', 0))
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            
            if not text:
                flash('Текстът на съобщението не може да бъде празен!', 'error')
                return redirect(request.url)
            
            # Парсиране на датите
            start_datetime = None
            end_datetime = None
            
            if start_date:
                try:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            
            if end_date:
                try:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Обновяване на съобщението
            message.text = text
            message.is_urgent = is_urgent
            message.priority = priority
            message.start_date = start_datetime
            message.end_date = end_datetime
            
            db.session.commit()
            
            flash('Съобщението е обновено успешно!', 'success')
            return redirect(url_for('admin_messages'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Грешка при обновяване на съобщението: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('admin/message_form.html', action='edit', message=message)

@app.route('/admin/messages/toggle/<int:message_id>')
@login_required
def admin_messages_toggle(message_id):
    """Превключване на активност на съобщение"""
    try:
        message = Message.query.get_or_404(message_id)
        message.is_active = not message.is_active
        db.session.commit()
        
        status = "активирано" if message.is_active else "деактивирано"
        flash(f'Съобщението е {status} успешно!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Грешка при промяна на статуса: {str(e)}', 'error')
    
    return redirect(url_for('admin_messages'))

@app.route('/admin/messages/delete/<int:message_id>')
@login_required
def admin_messages_delete(message_id):
    """Изтриване на съобщение"""
    try:
        message = Message.query.get_or_404(message_id)
        db.session.delete(message)
        db.session.commit()
        
        flash('Съобщението е изтрито успешно!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Грешка при изтриване на съобщението: {str(e)}', 'error')
    
    return redirect(url_for('admin_messages'))

# ============================================================================
# АДМИНИСТРАТОРСКИ ROUTES - ОСНОВНИ
# ============================================================================

@app.route('/admin')
@login_required
def admin_dashboard():
    """Администраторски панел"""
    # Статистики
    stats = {
        'total_folders': Folder.query.count(),
        'active_folders': Folder.query.filter_by(is_active=True).count(),
        'total_images': sum([folder.image_count for folder in Folder.query.all()]),
        'total_messages': Message.query.count(),
        'active_messages': Message.query.filter_by(is_active=True).count()
    }
    
    # Последни съобщения
    messages = Message.query.order_by(Message.created_at.desc()).limit(5).all()
    
    # Последни папки
    folders = Folder.query.order_by(Folder.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', stats=stats, messages=messages, folders=folders)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Администраторски вход"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Твърдо кодирани credentials за демо
        if username == 'admin' and password == 'mglive2025':
            session['logged_in'] = True
            session['username'] = username
            flash('Успешно влизане!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Грешно потребителско име или парола!', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    """Администраторски изход"""
    session.clear()
    flash('Успешно излизане!', 'success')
    return redirect(url_for('display'))

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ НА БАЗАТА ДАННИ
# ============================================================================

def init_database():
    """Инициализация на базата данни с примерни данни"""
    
    # Създаване на таблиците
    db.create_all()
    
    # Проверка дали има съществуващи данни
    if Folder.query.first() is None:
        # Създаване на примерни папки
        folders = [
            Folder(name='gallery1', display_name='Галерия 1', is_active=True, priority=1),
            Folder(name='announcements', display_name='Обявления', is_active=True, priority=2),
            Folder(name='events', display_name='Събития', is_active=False, priority=0)
        ]
        
        for folder in folders:
            db.session.add(folder)
            # Създаване на папките в файловата система
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder.name)
            os.makedirs(folder_path, exist_ok=True)
    
    # Създаване на примерно съобщение ако няма
    if Message.query.first() is None:
        sample_message = Message(
            text='Добре дошли в МГ LIVE - информационната система на Математическа гимназия "Атанас Радев", гр. Ямбол',
            is_active=True,
            is_urgent=False,
            priority=1,
            created_by='system'
        )
        db.session.add(sample_message)
    
    # Създаване на админ потребител ако няма
    if User.query.first() is None:
        admin_user = User(username='admin', is_admin=True)
        admin_user.set_password('mglive2025')
        db.session.add(admin_user)
    
    # Запис на промените
    db.session.commit()

# ============================================================================
# СТАРТИРАНЕ НА ПРИЛОЖЕНИЕТО
# ============================================================================

if __name__ == '__main__':
    # Инициализация на базата данни
    with app.app_context():
        init_database()
    
    # Стартиране на Flask приложението
    app.run(debug=True, host='0.0.0.0', port=5000)