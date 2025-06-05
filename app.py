import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, jsonify, flash, session
from datetime import datetime
from collections import defaultdict
from werkzeug.security import generate_password_hash, check_password_hash
import os
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Required for session management
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

# ---------- 安全更新数据库 ---------- #
def migrate_db():
    with app.app_context():
        db = get_db()
        
        # Create users table if it doesn't exist
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                level TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Check if matched_player columns exist in bookings table
        cursor = db.execute('PRAGMA table_info(bookings)')
        columns = {row['name'] for row in cursor.fetchall()}
        
        # Add new columns to bookings table if they don't exist
        if 'matched_player' not in columns:
            db.execute('ALTER TABLE bookings ADD COLUMN matched_player TEXT')
        if 'matched_player_level' not in columns:
            db.execute('ALTER TABLE bookings ADD COLUMN matched_player_level TEXT')
        if 'user_id' not in columns:
            db.execute('ALTER TABLE bookings ADD COLUMN user_id INTEGER REFERENCES users(id)')
        if 'scores' not in columns:
            db.execute('ALTER TABLE bookings ADD COLUMN scores TEXT')
        
        # Create players table if it doesn't exist
        db.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                level TEXT NOT NULL,
                win_rate REAL DEFAULT 0,
                recent_matches INTEGER DEFAULT 0
            );
        ''')
        
        # Insert sample players if none exist
        if not db.execute('SELECT * FROM players').fetchall():
            sample_players = [
                ('John Smith', 'Intermediate', 65, 15),
                ('Sarah Johnson', 'Advanced', 78, 22),
                ('Mike Chen', 'Beginner', 45, 8),
                ('Emma Wilson', 'Intermediate', 70, 12),
                ('Alex Brown', 'Advanced', 82, 25)
            ]
            db.executemany('INSERT INTO players (name, level, win_rate, recent_matches) VALUES (?, ?, ?, ?)', 
                          sample_players)
        
        db.commit()

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

# ---------- Find Players ---------- #
@app.route('/find-players')
def find_players():
    return render_template('find_player.html')

# ---------- Book Courts ---------- #
@app.route('/book-courts', methods=['GET', 'POST'])
def book_courts():
    db = get_db()
    if request.method == 'POST':
        court = request.form['court']
        time = request.form['time']
        
        # Validate booking time is not in the past
        booking_time = datetime.strptime(time, '%Y-%m-%dT%H:%M')
        if booking_time < datetime.now():
            flash('Cannot book a time in the past')
            return redirect(url_for('book_courts'))
            
        # Get matched player info from query parameters
        matched_player = request.args.get('playerName')
        matched_player_level = request.args.get('playerLevel')
        
        db.execute('''
            INSERT INTO bookings (court, time, matched_player, matched_player_level) 
            VALUES (?, ?, ?, ?)
        ''', (court, time, matched_player, matched_player_level))
        db.commit()
        return redirect(url_for('book_courts'))

    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
    bookings = db.execute('SELECT * FROM bookings ORDER BY id DESC').fetchall()
    return render_template('book_courts.html', bookings=bookings, now=now)

# ---------- Get Available Players API ---------- #
@app.route('/api/available-players')
def get_available_players():
    db = get_db()
    players = db.execute('SELECT * FROM players').fetchall()
    return jsonify([{
        'id': p['id'],
        'name': p['name'],
        'level': p['level'],
        'winRate': f"{p['win_rate']}%",
        'recentMatches': p['recent_matches']
    } for p in players])

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

    # Calculate skill metrics based on match results and scores
    skill_metrics = {
        'Consistency': 0,
        'Power': 0,
        'Speed': 0,
        'Technique': 0,
        'Strategy': 0,
        'Endurance': 0
    }

    # Analyze scores to determine skill metrics
    for booking in played:
        if booking['scores']:
            scores = booking['scores'].split('<br>')
            total_games = len(scores)
            if total_games > 0:
                # Consistency: Based on score differences
                score_diffs = []
                for score in scores:
                    try:
                        my_score = int(score.split('Me ')[1].split(' ')[0])
                        opp_score = int(score.split('Opponent ')[1])
                        score_diffs.append(abs(my_score - opp_score))
                    except:
                        continue
                
                if score_diffs:
                    avg_diff = sum(score_diffs) / len(score_diffs)
                    skill_metrics['Consistency'] += (1 / (1 + avg_diff)) * 20

                # Power: Based on winning games with high scores
                for score in scores:
                    try:
                        my_score = int(score.split('Me ')[1].split(' ')[0])
                        if my_score >= 21:  # Won with high score
                            skill_metrics['Power'] += 5
                    except:
                        continue

                # Speed: Based on quick wins
                for score in scores:
                    try:
                        my_score = int(score.split('Me ')[1].split(' ')[0])
                        opp_score = int(score.split('Opponent ')[1])
                        if my_score >= 21 and opp_score <= 15:  # Quick win
                            skill_metrics['Speed'] += 5
                    except:
                        continue

                # Technique: Based on close wins
                for score in scores:
                    try:
                        my_score = int(score.split('Me ')[1].split(' ')[0])
                        opp_score = int(score.split('Opponent ')[1])
                        if abs(my_score - opp_score) <= 2:  # Close game
                            skill_metrics['Technique'] += 5
                    except:
                        continue

                # Strategy: Based on overall win rate
                skill_metrics['Strategy'] += (wins / total) * 20

                # Endurance: Based on number of games played and maintaining performance
                if total_games >= 3:  # Only count matches with multiple games
                    skill_metrics['Endurance'] += min(20, total_games * 5)  # Cap at 20 points per match
                    # Bonus for maintaining performance in later games
                    if total_games >= 3:
                        last_game_score = scores[-1].split('Me ')[1].split(' ')[0]
                        if int(last_game_score) >= 21:  # Won the last game
                            skill_metrics['Endurance'] += 5

    # Normalize all metrics to be between 0 and 100
    for key in skill_metrics:
        skill_metrics[key] = min(100, round(skill_metrics[key]))

    # 初始化统计容器
    from collections import defaultdict
    monthly_played = defaultdict(int)
    monthly_wins = defaultdict(int)

    for b in played:
        try:
            dt = datetime.strptime(b['time'], '%Y-%m-%dT%H:%M')
            label = dt.strftime('%b')  # Jan, Feb, etc.
            monthly_played[label] += 1
            if b['result'] == 'win':
                monthly_wins[label] += 1
        except Exception as e:
            print("Date parse error:", b['time'], e)

    # 构造有序结果
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    labels = []
    match_counts = []
    win_counts = []
    win_rate_trend = []

    for m in months:
        if monthly_played[m] > 0:
            labels.append(m)
            match_counts.append(monthly_played[m])
            win_counts.append(monthly_wins[m])
            ratio = round(monthly_wins[m] / monthly_played[m] * 100)
            win_rate_trend.append(ratio)

    return render_template('track_progress.html',
                           wins=wins,
                           losses=losses,
                           total=total,
                           win_rate=win_rate,
                           labels=labels,
                           match_counts=match_counts,
                           win_counts=win_counts,
                           win_rate_trend=win_rate_trend,
                           skill_metrics=skill_metrics)

# ---------- Registration and Authentication Routes ---------- #
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        level = request.form['level']
        
        db = get_db()
        error = None
        
        if not username:
            error = 'Username is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif not level:
            error = 'Playing level is required.'
        
        if error is None:
            try:
                db.execute(
                    'INSERT INTO users (username, email, password_hash, level) VALUES (?, ?, ?, ?)',
                    (username, email, generate_password_hash(password), level)
                )
                db.commit()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                error = 'User already exists.'
        
        flash(error)
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password_hash'], password):
            error = 'Incorrect password.'
        
        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('home'))
        
        flash(error)
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Update the existing routes to use user authentication
def login_required(view):
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()

@app.route('/set-scores', methods=['POST'])
def set_scores():
    if not g.user:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    booking_id = request.form.get('booking_id')
    if not booking_id:
        return jsonify({'success': False, 'error': 'No booking ID provided'})
    
    # Collect all game scores
    scores = []
    game_count = 1
    while True:
        my_score = request.form.get(f'my_score_{game_count}')
        opponent_score = request.form.get(f'opponent_score_{game_count}')
        
        if not my_score or not opponent_score:
            break
            
        scores.append(f"Game {game_count}: Me {my_score} Opponent {opponent_score}")
        game_count += 1
    
    if not scores:
        return jsonify({'success': False, 'error': 'No scores provided'})
    
    # Format scores as HTML
    scores_html = '<br>'.join(scores)
    
    # Update the booking with scores
    db = get_db()
    db.execute('UPDATE bookings SET scores = ? WHERE id = ?', (scores_html, booking_id))
    db.commit()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()  # Initialize basic database structure
    migrate_db()  # Safely add new tables and columns
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port,debug=True)
