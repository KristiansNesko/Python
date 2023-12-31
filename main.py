from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import random
import json

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = '_privatekey_'

with open('data/texts.json', 'r') as file:
    texts = json.load(file)

with sqlite3.connect('users.db') as connection:
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            life_points INTEGER DEFAULT 150,
            combat_points INTEGER DEFAULT 0,
            experience_points INTEGER DEFAULT 0,
            experience_required INTEGER DEFAULT 100,
            games_played INTEGER DEFAULT 0  
        )
    ''')

    cursor.execute("PRAGMA table_info(users);")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    if 'experience_points' not in column_names:
        cursor.execute('ALTER TABLE users ADD COLUMN experience_points INTEGER DEFAULT 100;')

    connection.commit()

with sqlite3.connect('users.db') as connection:
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            x INTEGER,
            y INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    connection.commit()

def calculate_level(experience_points):
    return (experience_points // 250) + 1

@app.route('/')
def home():
    return render_template('home.html', texts=texts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']

            with sqlite3.connect('users.db') as connection:
                cursor = connection.cursor()
                cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                               (username, password))
                connection.commit()
                flash('Registration successful!', 'success')
                return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose a different one.',
                  'danger')
        except Exception as e:
            print(f"Error during registration: {str(e)}")
            flash('An error occurred during registration. Please try again.',
                  'danger')

    return render_template('register.html', texts=texts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with sqlite3.connect('users.db') as connection:
            cursor = connection.cursor()
            cursor.execute(
                'SELECT id FROM users WHERE username = ? AND password = ?',
                (username, password))
            user_id = cursor.fetchone()

            if user_id:
              session['user_id'] = user_id[0]
              flash('Login successful!', 'success')
              print("User ID stored in session:", session['user_id'])
              print("Texts:", texts)  
              return redirect(url_for('game'))

    return render_template('login.html', texts=texts)

@app.route('/game', methods=['GET', 'POST'])
def game():
    if 'user_id' not in session:
        flash('Please log in to play.', 'danger')
        return redirect(url_for('login', texts=texts))

    player_id = session['user_id']

    with sqlite3.connect('users.db') as connection:
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (player_id,))
        player = cursor.fetchone()

        if player is None:
            flash('Player not found. Please log in again.', 'danger')
            return redirect(url_for('login', texts=texts))

        columns = [column[1] for column in cursor.execute("PRAGMA table_info(users);")]
        if 'games_played' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN games_played INTEGER DEFAULT 0;')
            connection.commit()

        player_games_played = player[6] if len(player) > 6 else 0
        player_level = calculate_level(player[5])  

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'fight':
                if player[3] > 0:  
                    x = random.randint(12, 26)
                    y = random.randint(10, 30)

                    player_life_points = max(player[3] - x, 0)
                    player_combat_points = player[4] + y
                    player_experience_points = player[5] + 50  

                    player_level = calculate_level(player_experience_points)

                    if player_life_points == 0:
                        player_experience_points += player_combat_points

                        cursor.execute(
                            'UPDATE users SET life_points = 0, combat_points = 0, experience_points = ?, games_played = ? WHERE id = ?',
                            (player_experience_points, player_games_played + 1, player_id))
                        connection.commit()

                        return render_template('game_result.html', player_name=player[1],
                                               x=x,
                                               y=y,
                                               player_life_points=0,
                                               player_combat_points=player_combat_points,
                                               player_experience_points=player_experience_points,
                                               player_level=player_level,
                                               player_games_played=player_games_played + 1,                               
                                               texts=texts)

                    cursor.execute(
                        'UPDATE users SET life_points = ?, combat_points = ?, experience_points = ?, games_played = ? WHERE id = ?',
                        (player_life_points, player_combat_points, player_experience_points, player_games_played + 1, player_id))
                    connection.commit()

                    return render_template('game_result.html', player_name=player[1],
                                           x=x,
                                           y=y,
                                           player_life_points=player_life_points,
                                           player_combat_points=player_combat_points,
                                           player_experience_points=player_experience_points,
                                           player_level=player_level,
                                           player_games_played=player_games_played + 1,
                                           texts=texts)

                else:
                    flash('You have lost. Your life points are already 0.', 'danger')

            elif action == 'leave':
                flash('Game ended. See your stats below.', 'info')
                return redirect(url_for('game',texts=texts))

            elif action == 'stats':
                return redirect(url_for('stats',texts=texts))

            elif action == 'logout':
                session.clear()
                return redirect(url_for('login',texts=texts))

    return render_template('game.html', player_level=player_level, player_experience_points=player[5],
                           player_games_played=player_games_played, texts=texts)

@app.route('/stats')
def stats(): 
    if 'user_id' not in session:
        flash('Please log in to view stats.', 'danger')
        return redirect(url_for('login', texts=texts))

    player_id = session['user_id']
    with sqlite3.connect('users.db') as connection:
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (player_id,))
        player = cursor.fetchone()

    if player is None:
        flash('Player not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    return render_template('stats.html', player=player, texts=texts)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
