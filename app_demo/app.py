import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
DATABASE = 'database.db'

# ---------- 数据库连接 ---------- #
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # 让结果支持 dict-like 访问
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db:
        db.close()

# ---------- 初始化数据库（仅运行一次）---------- #
def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                court TEXT NOT NULL,
                time TEXT NOT NULL,
                result TEXT DEFAULT ''
            );
        ''')
        db.commit()

# ---------- 首页 ---------- #
@app.route('/')
def home():
    return render_template('index.html')

# ---------- Book Courts ---------- #
@app.route('/book-courts', methods=['GET', 'POST'])
def book_courts():
    db = get_db()
    if request.method == 'POST':
        court = request.form['court']
        time = request.form['time']
        db.execute('INSERT INTO bookings (court, time) VALUES (?, ?)', (court, time))
        db.commit()
        return redirect(url_for('book_courts'))

    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
    bookings = db.execute('SELECT * FROM bookings ORDER BY id DESC').fetchall()
    return render_template('book_courts.html', bookings=bookings, now=now)

# ---------- 设置比赛结果 ---------- #
@app.route('/set-result', methods=['POST'])
def set_result():
    index = request.form['index']
    result = request.form['result']
    db = get_db()
    db.execute('UPDATE bookings SET result = ? WHERE id = ?', (result, index))
    db.commit()
    return redirect(url_for('book_courts'))

# ---------- Track Progress ---------- #
@app.route('/track-progress')
def track_progress():
    db = get_db()
    rows = db.execute('SELECT * FROM bookings WHERE result IN ("win", "loss")').fetchall()

    played = list(rows)
    wins = sum(1 for b in played if b['result'] == 'win')
    losses = sum(1 for b in played if b['result'] == 'loss')
    total = len(played)
    win_rate = round((wins / total) * 100) if total > 0 else 0

    monthly_played = defaultdict(int)
    monthly_wins = defaultdict(int)

    for b in played:
        try:
            dt = datetime.strptime(b['time'], '%Y-%m-%dT%H:%M')
            label = dt.strftime('%b')
            monthly_played[label] += 1
            if b['result'] == 'win':
                monthly_wins[label] += 1
        except Exception as e:
            print("Time parse error:", b['time'], e)

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    labels, match_counts, win_counts = [], [], []
    for m in months:
        if monthly_played[m] > 0:
            labels.append(m)
            match_counts.append(monthly_played[m])
            win_counts.append(monthly_wins[m])

    return render_template('track_progress.html',
                           wins=wins, losses=losses, total=total, win_rate=win_rate,
                           labels=labels, match_counts=match_counts, win_counts=win_counts)

if __name__ == '__main__':
    init_db()  # 初始化数据库（仅创建一次）
    app.run(debug=True)
