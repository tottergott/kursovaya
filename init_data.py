# Скрипт для создания тестовых данных
from app import app, db, User, Message
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def create_test_data():
    with app.app_context():
        # Создаем таблицы
        db.create_all()
        
        # Проверяем, есть ли уже пользователи
        if User.query.first():
            print("Тестовые данные уже существуют")
            return
        
        # Создаем тестовых пользователей
        users_data = [
            {
                'username': 'ivanov_doctor',
                'email': 'ivanov@hospital.ru',
                'password': 'password123',
                'department': 'Кардиология',
                'position': 'Врач'
            },
            {
                'username': 'petrov_nurse',
                'email': 'petrov@hospital.ru',
                'password': 'password123',
                'department': 'Кардиология',
                'position': 'Медсестра'
            },
            {
                'username': 'sidorova_head',
                'email': 'sidorova@hospital.ru',
                'password': 'password123',
                'department': 'Неврология',
                'position': 'Заведующий отделением'
            },
            {
                'username': 'admin',
                'email': 'admin@hospital.ru',
                'password': 'admin123',
                'department': 'Администрация',
                'position': 'Администратор'
            }
        ]
        
        created_users = []
        for user_data in users_data:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                password_hash=generate_password_hash(user_data['password']),
                department=user_data['department'],
                position=user_data['position']
            )
            db.session.add(user)
            created_users.append(user)
        
        db.session.commit()
        
        # Создаем тестовые сообщения
        messages_data = [
            {
                'sender': created_users[0],  # ivanov_doctor
                'recipient': created_users[1],  # petrov_nurse
                'content': 'Пожалуйста, подготовьте палату 205 для нового пациента с диагнозом ИБС.',
                'priority': 'urgent',
                'timestamp': datetime.utcnow() - timedelta(hours=2)
            },
            {
                'sender': created_users[1],  # petrov_nurse
                'recipient': created_users[0],  # ivanov_doctor
                'content': 'Палата готова. Все необходимое оборудование проверено.',
                'priority': 'normal',
                'timestamp': datetime.utcnow() - timedelta(hours=1, minutes=30)
            },
            {
                'sender': created_users[2],  # sidorova_head
                'recipient': created_users[0],  # ivanov_doctor
                'content': 'ЭКСТРЕННО: Требуется консультация кардиолога в отделении неврологии. Пациент с подозрением на инфаркт.',
                'priority': 'emergency',
                'timestamp': datetime.utcnow() - timedelta(minutes=15)
            },
            {
                'sender': created_users[3],  # admin
                'recipient': created_users[0],  # ivanov_doctor
                'content': 'Напоминание: завтра в 14:00 планерка заведующих отделениями.',
                'priority': 'normal',
                'timestamp': datetime.utcnow() - timedelta(hours=3)
            }
        ]
        
        for msg_data in messages_data:
            message = Message(
                sender_id=msg_data['sender'].id,
                recipient_id=msg_data['recipient'].id,
                content=msg_data['content'],
                priority=msg_data['priority'],
                timestamp=msg_data['timestamp']
            )
            db.session.add(message)
        
        db.session.commit()
        
        print("Тестовые данные созданы успешно!")
        print("\nТестовые пользователи:")
        for user_data in users_data:
            print(f"- {user_data['username']} / {user_data['password']} ({user_data['position']}, {user_data['department']})")

if __name__ == '__main__':
    create_test_data()