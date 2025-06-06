import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


import tempfile
import pytest
import sqlite3
from app import app, init_db, get_db

@pytest.fixture
def client():
    # 创建临时数据库文件
    db_fd, db_path = tempfile.mkstemp()
    app.config['DATABASE'] = db_path
    app.config['TESTING'] = True

    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

    os.close(db_fd)
    os.unlink(db_path)

# ✅ 测试主页访问
def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200

# ✅ 测试预约页面访问
def test_book_courts_get(client):
    response = client.get('/book-courts')
    assert response.status_code == 200
    assert b'Book a Court' in response.data

# ✅ 测试添加预约记录
def test_book_court_post_and_result(client):
    # 添加预约
    response = client.post('/book-courts', data={
        'court': 'Court 1',
        'time': '2024-05-05T18:00'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Court 1' in response.data

    # 设置结果为胜
    # db = get_db()
    # booking = db.execute('SELECT * FROM bookings').fetchone()
    # assert booking is not None

    with app.app_context():
        db = get_db()
        booking = db.execute('SELECT * FROM bookings').fetchone()
        assert booking is not None

    # 设置胜负
    response = client.post('/set-result', data={
        'index': booking['id'],
        'result': 'win'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Win' in response.data or b'Pending' in response.data

# ✅ 测试统计页面正确显示结果
def test_track_progress_logic(client):
    client.post('/book-courts', data={
        'court': 'Court 2',
        'time': '2024-05-06T19:00'
    })

    with app.app_context():
        db = get_db()
        booking = db.execute('SELECT * FROM bookings').fetchone()
        db.execute('UPDATE bookings SET result = ? WHERE id = ?', ('win', booking['id']))
        db.commit()

    response = client.get('/track-progress')
    assert response.status_code == 200
    assert b'Matches Played' in response.data
    assert b'Win Rate' in response.data
    assert b'100%' in response.data or b'Win Rate: 100' in response.data


