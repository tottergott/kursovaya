
from app_sql import app, init_db

if __name__ == '__main__':
    init_db()
    print("База данных инициализирована")
    print("Запуск сервера на http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)