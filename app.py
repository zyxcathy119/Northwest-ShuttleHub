import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, jsonify, flash, session
from datetime import datetime
from collections import defaultdict
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
import hashlib

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
        
        # Create user_preferences table if it doesn't exist
        db.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                day_of_week TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                is_available BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, day_of_week, start_time)
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
                recent_matches INTEGER DEFAULT 0,
                gender TEXT DEFAULT 'Not specified',
                age INTEGER DEFAULT 25,
                bio TEXT DEFAULT '',
                photo_url TEXT DEFAULT '',
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                favorite_shot TEXT DEFAULT '',
                playing_style TEXT DEFAULT '',
                years_playing INTEGER DEFAULT 1,
                achievements TEXT DEFAULT ''
            );
        ''')
        
        # Check if new columns exist in players table and add them if they don't
        cursor = db.execute('PRAGMA table_info(players)')
        player_columns = {row['name'] for row in cursor.fetchall()}
        
        new_columns = [
            ('gender', 'TEXT DEFAULT "Not specified"'),
            ('age', 'INTEGER DEFAULT 25'),
            ('bio', 'TEXT DEFAULT ""'),
            ('photo_url', 'TEXT DEFAULT ""'),
            ('total_wins', 'INTEGER DEFAULT 0'),
            ('total_losses', 'INTEGER DEFAULT 0'),
            ('favorite_shot', 'TEXT DEFAULT ""'),
            ('playing_style', 'TEXT DEFAULT ""'),
            ('years_playing', 'INTEGER DEFAULT 1'),
            ('achievements', 'TEXT DEFAULT ""'),
            ('preferred_time', 'TEXT DEFAULT ""'),
            ('location', 'TEXT DEFAULT ""'),
            ('languages', 'TEXT DEFAULT ""'),
            ('equipment_brand', 'TEXT DEFAULT ""'),
            ('training_schedule', 'TEXT DEFAULT ""'),
            ('strongest_skill', 'TEXT DEFAULT ""'),
            ('improvement_goal', 'TEXT DEFAULT ""'),
            ('match_frequency', 'TEXT DEFAULT ""'),
            ('coach_experience', 'TEXT DEFAULT ""'),
            ('tournament_level', 'TEXT DEFAULT ""')
        ]
        
        for column_name, column_def in new_columns:
            if column_name not in player_columns:
                try:
                    db.execute(f'ALTER TABLE players ADD COLUMN {column_name} {column_def}')
                except sqlite3.OperationalError:
                    pass  # Column might already exist
        
        # Insert sample players if none exist
        existing_players = db.execute('SELECT COUNT(*) as count FROM players').fetchone()
        if existing_players['count'] == 0:
            sample_players = [
                ('John Smith', 'Intermediate', 65, 15, 'Male', 28, 'Experienced doubles specialist with a love for aggressive net play. Former college athlete who picked up badminton 3 years ago and has been steadily improving. Known for his powerful smashes and quick reflexes at the net. Always encouraging to beginners and loves to share tips.', '/static/images/john.jpg', 13, 7, 'Smash', 'Aggressive', 3, 'Club Championship Finalist 2023, Best Doubles Player Award', 'Evening (6-9 PM)', 'Bellevue, WA', 'English, Spanish', 'Yonex', 'Tuesday/Thursday evenings, Saturday mornings', 'Net play and quick reactions', 'Improve singles game and court positioning', '3-4 times per week', 'Coached junior players at local club', 'Regional level'),
                
                ('Sarah Johnson', 'Advanced', 78, 22, 'Female', 32, 'Former NCAA Division II player with exceptional court coverage and tactical awareness. Plays with surgical precision and has an uncanny ability to read opponents. Currently working as a physical therapist, which gives her deep understanding of injury prevention and body mechanics in sports.', '/static/images/sarah.jpg', 18, 6, 'Drop Shot', 'Tactical', 8, 'Regional Tournament Winner 2022, State Doubles Champion, NCAA All-Conference Team 2013', 'Morning (6-9 AM) and weekends', 'Seattle, WA', 'English, Mandarin', 'Victor', 'Daily practice 6-8 AM, weekend tournament play', 'Deceptive shots and game strategy', 'Compete at national level tournaments', '6-7 times per week', 'High school varsity coach for 2 years', 'National level'),
                
                ('Mike Chen', 'Beginner', 45, 8, 'Male', 24, 'Recent graduate who discovered badminton during university and fell in love with the sport. Very analytical approach to learning, keeps detailed notes on techniques and strategies. Quick learner with natural athleticism from basketball background. Extremely enthusiastic and always asks great questions.', '/static/images/mike.jpg', 3, 5, 'Clear', 'Defensive', 1, 'Most Improved Player 2023, Perfect Attendance Award', 'Afternoon (2-6 PM)', 'Redmond, WA', 'English, Mandarin, Cantonese', 'Li-Ning', 'Monday/Wednesday/Friday afternoons', 'Footwork and endurance', 'Master basic techniques and reach intermediate level', '3 times per week', 'Peer tutor for beginner classes', 'Club level'),
                
                ('Emma Wilson', 'Intermediate', 70, 12, 'Female', 26, 'Consistent and reliable player with textbook form and excellent fundamentals. Works as a software engineer and brings the same methodical approach to her badminton training. Known for her mental toughness and ability to stay calm under pressure. Great doubles partner who communicates well on court.', '/static/images/emma.jpg', 8, 4, 'Net Shot', 'All-around', 4, 'Club Member of the Year 2023, Most Sportsmanlike Player 2022', 'Evening (7-10 PM)', 'Kirkland, WA', 'English, French', 'Mizuno', 'Monday/Wednesday/Friday evenings', 'Consistency and shot placement', 'Develop more attacking shots', '3 times per week', 'Assistant coach for youth program', 'Regional level'),
                
                ('Alex Brown', 'Advanced', 82, 25, 'Male', 35, 'Veteran player and natural leader with over 12 years of competitive experience. Former semi-professional player who competed in international tournaments. Now focuses on coaching and mentoring while maintaining his competitive edge. Known for his powerful drives and exceptional court awareness.', '/static/images/alex.jpg', 21, 4, 'Drive', 'Power', 12, 'State Singles Champion 2021, Master\'s Division Winner, International Tournament Semi-finalist 2019', 'Morning (5-8 AM) and evening (8-11 PM)', 'Seattle, WA', 'English, German, some Japanese', 'Yonex', 'Daily training 5:30-7:30 AM, coaching afternoons', 'Power shots and mental game', 'Mentor next generation of players', '5-6 times per week', 'Head coach at Northwest Badminton Academy', 'International level'),
                
                ('Lisa Park', 'Intermediate', 72, 18, 'Female', 29, 'Former tennis player who transitioned to badminton 2 years ago and quickly adapted her skills. Brings excellent hand-eye coordination and understanding of racquet sports. Works as a marketing manager and plays badminton for stress relief and fitness. Loves the social aspect of the sport.', '/static/images/lisa.jpg', 12, 6, 'Backhand Clear', 'Versatile', 2, 'Fastest Improvement Award 2022, Doubles Tournament Finalist', 'Lunch time (12-2 PM) and weekends', 'Bothell, WA', 'English, Korean', 'Babolat', 'Tuesday/Thursday lunch, weekend tournaments', 'Adaptability and quick learning', 'Master advanced techniques', '4 times per week', 'Organizes social badminton events', 'Regional level'),
                
                ('David Kim', 'Advanced', 85, 28, 'Male', 27, 'Lightning-fast player with incredible agility and shot-making ability. Specializes in singles play and known for his never-give-up attitude. Currently pursuing a PhD in Sports Science while competing at high levels. His analytical mind helps him break down opponents\' weaknesses quickly.', '/static/images/david.jpg', 24, 4, 'Jump Smash', 'Speed-based', 6, 'State Singles Champion 2023, University Champion 2020-2022, National Youth Team Member', 'Morning (6-9 AM)', 'University District, Seattle', 'English, Korean, Japanese', 'Yonex', 'Daily morning training, afternoon research', 'Speed and agility', 'Qualify for national team', '6 times per week', 'University team assistant coach', 'National level'),
                
                ('Rachel Green', 'Beginner', 38, 6, 'Female', 31, 'Busy mother of two who recently started playing badminton as a way to stay active and meet new people. Very determined and hardworking despite limited time for practice. Brings great energy and positive attitude to every session. Quick to encourage other beginners and create a welcoming environment.', '/static/images/rachel.jpg', 2, 4, 'Serve', 'Learning', 0.5, 'Beginner of the Month Award, Team Spirit Award', 'Morning (9-11 AM) while kids are at school', 'Issaquah, WA', 'English', 'Decathlon starter set', 'Tuesday/Thursday mornings', 'Determination and team spirit', 'Build basic skills and confidence', '2 times per week', 'Volunteer organizer for family events', 'Social level')
            ]
            
            db.executemany('''INSERT INTO players (name, level, win_rate, recent_matches, gender, age, bio, photo_url, total_wins, total_losses, favorite_shot, playing_style, years_playing, achievements, preferred_time, location, languages, equipment_brand, training_schedule, strongest_skill, improvement_goal, match_frequency, coach_experience, tournament_level) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', sample_players)
        
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

# ---------- About ---------- #
@app.route('/about')
def about():
    return render_template('about.html')

# ---------- Rank ---------- #
@app.route('/rank')
def rank():
    db = get_db()
    players = db.execute('SELECT * FROM players ORDER BY win_rate DESC, total_wins DESC').fetchall()
    
    # Calculate ranking scores for each player
    ranked_players = []
    for i, player in enumerate(players):
        total_matches = player['total_wins'] + player['total_losses']
        win_rate = player['win_rate']
        
        # Calculate activity score based on recent matches and frequency
        activity_score = 0
        if player['recent_matches']:
            activity_score += player['recent_matches'] * 2
        
        # Parse match frequency to get activity multiplier
        frequency_multiplier = 1.0
        if player['match_frequency']:
            freq = player['match_frequency'].lower()
            if '6-7' in freq or 'daily' in freq:
                frequency_multiplier = 2.0
            elif '5-6' in freq:
                frequency_multiplier = 1.8
            elif '4' in freq:
                frequency_multiplier = 1.5
            elif '3' in freq:
                frequency_multiplier = 1.2
            elif '2' in freq:
                frequency_multiplier = 1.0
        
        # Calculate overall ranking score
        # Formula: (win_rate * total_matches * frequency_multiplier) + activity_score
        ranking_score = (win_rate * total_matches * frequency_multiplier) + activity_score
        
        # Determine rank tier
        if ranking_score >= 2000:
            tier = "Champion"
            tier_class = "champion"
        elif ranking_score >= 1500:
            tier = "Expert"
            tier_class = "expert"
        elif ranking_score >= 1000:
            tier = "Advanced"
            tier_class = "advanced"
        elif ranking_score >= 500:
            tier = "Intermediate"
            tier_class = "intermediate"
        else:
            tier = "Beginner"
            tier_class = "beginner"
        
        ranked_players.append({
            'rank': i + 1,
            'player': player,
            'total_matches': total_matches,
            'ranking_score': round(ranking_score, 1),
            'tier': tier,
            'tier_class': tier_class,
            'activity_score': round(activity_score, 1),
            'frequency_multiplier': frequency_multiplier
        })
    
    return render_template('rank.html', ranked_players=ranked_players)

# ---------- Helper function to generate mock badminton scores ---------- #
def generate_mock_scores():
    """Generate realistic badminton match scores (1-3 games)"""
    num_games = random.randint(1, 3)
    scores = []
    my_wins = 0
    opp_wins = 0
    
    for game_num in range(1, num_games + 1):
        # Generate realistic badminton scores
        # Winner usually gets 21, loser gets between 5-20
        if random.random() < 0.6:  # 60% chance I win this game
            my_score = 21
            opp_score = random.randint(5, 20)
            if opp_score >= 20:  # Close game, might go to deuce
                my_score = random.choice([21, 22, 23, 24])
                opp_score = my_score - random.randint(1, 3)
            my_wins += 1
        else:  # Opponent wins this game
            opp_score = 21
            my_score = random.randint(5, 20)
            if my_score >= 20:  # Close game, might go to deuce
                opp_score = random.choice([21, 22, 23, 24])
                my_score = opp_score - random.randint(1, 3)
            opp_wins += 1
        
        scores.append(f"Game {game_num}: Me {my_score} Opponent {opp_score}")
    
    # Determine overall match result
    result = "win" if my_wins > opp_wins else "loss"
    scores_html = '<br>'.join(scores)
    
    return scores_html, result

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
            
        # Get player info from form data first, then query parameters as fallback
        matched_player = request.form.get('playerName') or request.args.get('playerName')
        matched_player_level = request.form.get('playerLevel') or request.args.get('playerLevel')
        
        # Create booking without automatic scores - user will add them later
        db.execute('''
            INSERT INTO bookings (court, time, matched_player, matched_player_level, scores, result) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (court, time, matched_player, matched_player_level, '', ''))
        db.commit()
        
        if matched_player:
            flash(f'Court booked successfully with {matched_player}! Remember to record your scores after playing.')
        else:
            flash('Court booked successfully! You can add your opponent and record scores later.')
        return redirect(url_for('book_courts'))

    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
    # Sort bookings by time in descending order (newest first)
    bookings = db.execute('SELECT * FROM bookings ORDER BY datetime(time) DESC').fetchall()
    return render_template('book_courts.html', bookings=bookings, now=now)

# ---------- Delete Booking ---------- #
@app.route('/delete-booking/<int:booking_id>', methods=['POST'])
def delete_booking(booking_id):
    db = get_db()
    # Check if booking exists
    booking = db.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    
    if not booking:
        flash('Booking not found')
        return redirect(url_for('book_courts'))
    
    # Delete the booking
    db.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
    db.commit()
    flash('Booking deleted successfully!')
    return redirect(url_for('book_courts'))

# ---------- Update Opponent ---------- #
@app.route('/update-opponent', methods=['POST'])
def update_opponent():
    booking_id = request.form.get('booking_id')
    opponent_name = request.form.get('opponent_name')
    opponent_level = request.form.get('opponent_level')
    
    if not booking_id or not opponent_name or not opponent_level:
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    db = get_db()
    # Check if booking exists
    booking = db.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    
    if not booking:
        return jsonify({'success': False, 'error': 'Booking not found'})
    
    # Update the opponent information
    db.execute(
        'UPDATE bookings SET matched_player = ?, matched_player_level = ? WHERE id = ?',
        (opponent_name, opponent_level, booking_id)
    )
    db.commit()
    
    return jsonify({'success': True})

# ---------- Get Available Players API ---------- #
@app.route('/api/available-players')
def get_available_players():
    db = get_db()
    all_players = db.execute('SELECT * FROM players').fetchall()
    
    # Get the selected time from query parameters
    selected_time = request.args.get('start')
    
    # Use time-based randomization to show different players for different time slots
    if selected_time:
        # Create a seed based on the selected time to ensure consistent results for the same time
        time_seed = int(hashlib.md5(selected_time.encode()).hexdigest()[:8], 16)
        random.seed(time_seed)
        
        # Randomly select 3-5 players for this time slot
        num_players = random.randint(3, min(5, len(all_players)))
        available_players = random.sample(list(all_players), num_players)
    else:
        # If no time selected, show all players
        available_players = all_players
    
    return jsonify([{
        'id': p['id'],
        'name': p['name'],
        'level': p['level'],
        'winRate': f"{p['win_rate']}%",
        'recentMatches': p['recent_matches'],
        'photo': p['photo_url'] if p['photo_url'] else '',
        'gender': p['gender'],
        'age': p['age'],
        'bio': p['bio'],
        'totalWins': p['total_wins'],
        'totalLosses': p['total_losses'],
        'favoriteShot': p['favorite_shot'],
        'playingStyle': p['playing_style'],
        'yearsPlaying': p['years_playing'],
        'achievements': p['achievements'],
        'preferredTime': p['preferred_time'] if p['preferred_time'] else '',
        'location': p['location'] if p['location'] else '',
        'languages': p['languages'] if p['languages'] else '',
        'equipmentBrand': p['equipment_brand'] if p['equipment_brand'] else '',
        'trainingSchedule': p['training_schedule'] if p['training_schedule'] else '',
        'strongestSkill': p['strongest_skill'] if p['strongest_skill'] else '',
        'improvementGoal': p['improvement_goal'] if p['improvement_goal'] else '',
        'matchFrequency': p['match_frequency'] if p['match_frequency'] else '',
        'coachExperience': p['coach_experience'] if p['coach_experience'] else '',
        'tournamentLevel': p['tournament_level'] if p['tournament_level'] else ''
    } for p in available_players])

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
    rows = db.execute('SELECT * FROM bookings WHERE result IN ("win", "loss") ORDER BY datetime(time) ASC').fetchall()

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
                if total > 0:
                    skill_metrics['Strategy'] += (wins / total) * 20

                # Endurance: Based on number of games played and maintaining performance
                if total_games >= 3:  # Only count matches with multiple games
                    skill_metrics['Endurance'] += min(20, total_games * 5)  # Cap at 20 points per match
                    # Bonus for maintaining performance in later games
                    if total_games >= 3:
                        try:
                            last_game_score = scores[-1].split('Me ')[1].split(' ')[0]
                            if int(last_game_score) >= 21:  # Won the last game
                                skill_metrics['Endurance'] += 5
                        except:
                            pass

    # Normalize all metrics to be between 0 and 100
    for key in skill_metrics:
        skill_metrics[key] = min(100, round(skill_metrics[key]))

    # Calculate monthly statistics from actual booking data
    monthly_played = defaultdict(int)
    monthly_wins = defaultdict(int)
    
    # Get current year for filtering recent data
    current_year = datetime.now().year
    current_month = datetime.now().month

    for b in played:
        try:
            dt = datetime.strptime(b['time'], '%Y-%m-%dT%H:%M')
            # Only include data from the last 12 months for more relevant trending
            if dt.year == current_year or (dt.year == current_year - 1 and dt.month > current_month):
                month_year_key = dt.strftime('%Y-%m')  # e.g., "2023-12"
                label = dt.strftime('%b %Y')  # e.g., "Dec 2023"
                monthly_played[month_year_key] = monthly_played.get(month_year_key, 0) + 1
                if b['result'] == 'win':
                    monthly_wins[month_year_key] = monthly_wins.get(month_year_key, 0) + 1
        except Exception as e:
            print("Date parse error:", b['time'], e)

    # Create ordered results for the last 12 months
    labels = []
    match_counts = []
    win_counts = []
    win_rate_trend = []
    
    # Generate last 12 months
    from datetime import timedelta
    import calendar
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # Last 12 months
    
    current_date = start_date
    while current_date <= end_date:
        month_year_key = current_date.strftime('%Y-%m')
        label = current_date.strftime('%b %Y')
        
        played_count = monthly_played.get(month_year_key, 0)
        wins_count = monthly_wins.get(month_year_key, 0)
        
        # Only include months with data to avoid empty chart
        if played_count > 0:
            labels.append(label)
            match_counts.append(played_count)
            win_counts.append(wins_count)
            win_rate = round((wins_count / played_count) * 100) if played_count > 0 else 0
            win_rate_trend.append(win_rate)
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)

    # If no data found, show at least current month with zero values
    if not labels:
        current_month_label = datetime.now().strftime('%b %Y')
        labels = [current_month_label]
        match_counts = [0]
        win_counts = [0]
        win_rate_trend = [0]

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

# ---------- Time Preferences ---------- #
@app.route('/time-preferences', methods=['GET', 'POST'])
def time_preferences():
    if not g.user:
        return redirect(url_for('login'))
    
    db = get_db()
    
    if request.method == 'POST':
        # Clear existing preferences for this user
        db.execute('DELETE FROM user_preferences WHERE user_id = ?', (g.user['id'],))
        
        # Get form data and save new preferences
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for day in days_of_week:
            # Check if this day is enabled
            day_enabled = request.form.get(f'{day.lower()}_enabled')
            if day_enabled:
                # Get time slots for this day
                start_times = request.form.getlist(f'{day.lower()}_start_time[]')
                end_times = request.form.getlist(f'{day.lower()}_end_time[]')
                
                # Save each time slot
                for start_time, end_time in zip(start_times, end_times):
                    if start_time and end_time:
                        db.execute('''
                            INSERT INTO user_preferences (user_id, day_of_week, start_time, end_time, is_available)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (g.user['id'], day, start_time, end_time, True))
        
        db.commit()
        flash('Time preferences updated successfully!')
        return redirect(url_for('time_preferences'))
    
    # Get existing preferences for this user
    preferences = db.execute('''
        SELECT day_of_week, start_time, end_time, is_available
        FROM user_preferences 
        WHERE user_id = ? 
        ORDER BY 
            CASE day_of_week 
                WHEN 'Monday' THEN 1 
                WHEN 'Tuesday' THEN 2 
                WHEN 'Wednesday' THEN 3 
                WHEN 'Thursday' THEN 4 
                WHEN 'Friday' THEN 5 
                WHEN 'Saturday' THEN 6 
                WHEN 'Sunday' THEN 7 
            END, start_time
    ''', (g.user['id'],)).fetchall()
    
    # Organize preferences by day
    prefs_by_day = {}
    for pref in preferences:
        day = pref['day_of_week']
        if day not in prefs_by_day:
            prefs_by_day[day] = []
        prefs_by_day[day].append({
            'start_time': pref['start_time'],
            'end_time': pref['end_time'],
            'is_available': pref['is_available']
        })
    
    return render_template('time_preferences.html', preferences=prefs_by_day)

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

# ---------- Helper function to determine result from scores ---------- #
def determine_result_from_scores(scores_html):
    """Determine win/loss result from game scores"""
    if not scores_html:
        return None
    
    scores = scores_html.split('<br>')
    my_wins = 0
    opp_wins = 0
    
    for score in scores:
        try:
            # Parse "Game X: Me Y Opponent Z" format
            parts = score.split(': Me ')
            if len(parts) != 2:
                continue
            score_part = parts[1]  # "Y Opponent Z"
            my_score = int(score_part.split(' Opponent ')[0])
            opp_score = int(score_part.split(' Opponent ')[1])
            
            if my_score > opp_score:
                my_wins += 1
            else:
                opp_wins += 1
        except (ValueError, IndexError):
            continue
    
    return "win" if my_wins > opp_wins else "loss"

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
    
    # Automatically determine result from scores
    result = determine_result_from_scores(scores_html)
    
    # Update the booking with scores and result
    db = get_db()
    db.execute('UPDATE bookings SET scores = ?, result = ? WHERE id = ?', (scores_html, result, booking_id))
    db.commit()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()  # Initialize basic database structure
    migrate_db()  # Safely add new tables and columns
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port,debug=True)
