from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.utils import secure_filename
import sqlite3
import os
import uuid
import random
import ssl
import string

from deepgram import Deepgram
from dotenv import load_dotenv
import os
import asyncio
from aiohttp import web
from aiohttp_wsgi import WSGIHandler

from typing import Dict, Callable

from openai import OpenAI
import pandas as pandas
import time

api_key = "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"
client = OpenAI(api_key=api_key)

app = Flask('aioflask')
dg_client = Deepgram("cf1ff9dc4a972c9b4b4d011617d780f31af60c4b")
app.secret_key = "~!@#$%^&*()_+QWERASDFGHJK"
DATA_BASE_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'accounts_info2.sqlite')

def check_to_create_table():
    connection = sqlite3.connect(DATA_BASE_FILE_PATH)
    cur = connection.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS Accounts ( id INTEGER PRIMARY KEY, full_name TEXT NOT NULL, level TEXT NOT NULL, age TEXT NOT NULL, email TEXT NOT NULL, password TEXT NOT NULL, language TEXT NOT NULL, previous_seven_subjects TEXT)')
    connection.commit()
    connection.close()
check_to_create_table()

def check_to_create_textTable():
    connection = sqlite3.connect(DATA_BASE_FILE_PATH)
    cur = connection.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS Texts ( id INTEGER PRIMARY KEY, email TEXT NOT NULL, text TEXT NOT NULL, viewId TEXT NOT NULL)')
    connection.commit()
    connection.close()
check_to_create_textTable()


#voice recognition
async def process_audio(fast_socket: web.WebSocketResponse):
    async def get_transcript(data: Dict) -> None:
        if 'channel' in data:
            transcript = data['channel']['alternatives'][0]['transcript']
        
            if transcript:
                await fast_socket.send_str(transcript)

    deepgram_socket = await connect_to_deepgram(get_transcript)

    return deepgram_socket
async def connect_to_deepgram(transcript_received_handler: Callable[[Dict], None]) -> str:
    try:
        socket = await dg_client.transcription.live({'punctuate': False, 'interim_results': False, 'language': 'de', 'model': 'nova-2', 'timeout' : 300})
        socket.registerHandler(socket.event.CLOSE, lambda c: print(f'Connection closed with code {c}.'))
        socket.registerHandler(socket.event.TRANSCRIPT_RECEIVED, transcript_received_handler)

        return socket
    except Exception as e:
        raise Exception(f'Could not open socket: {e}')
async def socket(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request) 

    deepgram_socket = await process_audio(ws)

    while True:
        data = await ws.receive_bytes()
        deepgram_socket.send(data)

@app.route('/temp_exercise',  methods=["POST", "GET"])
def index():
    def generate_unique_code():
        # Define the length of the code
        code_length = 6

        # Generate a random string of letters with the specified length
        unique_code = ''.join(random.choice(string.ascii_letters) for _ in range(code_length))

        return unique_code

    
    user_responses = session.get('user_responses', [])
    
    swivel = 0
    
    if swivel == 0:
        def get_completion(prompt, model="gpt-3.5-turbo"):
            response = client.chat.completions.create(
                model=model, 
                temperature = 0.8,
                max_tokens = 200,
                messages = [{"role": "user", "content": prompt}],

            )
            return response.choices[0].message.content
        
        formatted_responses = "[" + ", ".join(user_responses) + "]"
        prompt = f"Using the responses in brackets, generate a short narrative text in German: {formatted_responses}"
        
        chatgpt_return = get_completion(prompt)
        email = session["logged_in_user"]
        viewId = generate_unique_code()
        
        connection = sqlite3.connect(DATA_BASE_FILE_PATH)
        cur = connection.cursor()
        cur.execute(
            "INSERT INTO Texts (email, text, viewId) VALUES (?, ?, ?)",
            (email, chatgpt_return, viewId))
        connection.commit()
        connection.close()

        
        
    
    else:
        chatgpt_return = '''
        Hallo! Mein Name ist Anna. Ich komme aus Deutschland. Ich arbeite als Lehrerin und liebe es, mit Kindern zu arbeiten. In meiner Freizeit lese ich gerne Bücher und mache lange Spaziergänge im Park. Das Wetter hier ist heute schön. Ich hoffe, du hast auch einen schönen Tag!
        '''

    
    return render_template('index.html', chatgpt_return=chatgpt_return, user_responses=user_responses)

question_pool = {
    "weather": [
        "What color was the sky today?",
        "When was the last time it rained?",
        "Would you have preferred if it rained today?",
        "How was the weather today?",
        "Is it a good day today to go camping?",
        "Did the weather today affect your mood?",
        "Was it too cold today morning for you or no?"
    ],
    "mood": [
        "How would you describe your mood today?",
        "What made you feel happy today?",
        "Did anything specific make you feel stressed?",
        "What's one thing that made you smile today?",
        "Was there a moment that boosted your mood?",
        "Did you experience any frustration today?",
        "What activity helped improve your mood today?"
    ],
    "surprises": [
        "What surprised you the most today?",
        "Did you encounter anything unexpected?",
        "Was there a pleasant surprise today?",
        "Did you surprise yourself with anything?",
        "Was there a moment that caught you off guard?",
        "What news or event surprised you today?",
        "Did you learn something surprising today?"
    ],
    "news": [
        "What did you learn today from the news?",
        "Did any news story grab your attention?",
        "How did a particular news item make you feel?",
        "Were you surprised by any current events?",
        "Did you discuss any news topics with others today?",
        "Is there a news story you want to know more about?",
        "What's your opinion on a recent news development?"
    ],
    "family": [
        "Did you have a meaningful conversation with a family member?",
        "What's something positive you experienced with your family today?",
        "Did you face any challenges in your family interactions?",
        "Did you make any family-related decisions today?",
        "What's one thing you appreciate about your family?",
        "How did your family support you today?",
        "Did you learn something new about a family member today?"
    ],
    "technology": [
        "What interesting technology did you interact with today?",
        "How did technology impact your day?",
        "Did you encounter any tech-related challenges?",
        "What app or device did you find useful today?",
        "How much time did you spend on screens today?",
        "Did you learn something new about technology?",
        "What tech-related news caught your attention today?"
    ],
    "books": [
        "What book are you currently reading?",
        "Did a particular passage or quote resonate with you today?",
        "How did your reading choice influence your day?",
        "Did you learn something new from your reading today?",
        "Is there a character you empathized with in your book?",
        "Did you discuss your current read with anyone?",
        "What genre or author are you exploring in your reading?"
    ],
    "health": [
        "How did you prioritize your health today?",
        "Did you engage in any physical activity?",
        "What healthy habits did you practice today?",
        "Did you try a new recipe or food for your well-being?",
        "How did your overall health impact your day?",
        "What's one thing you're grateful for regarding your health?",
        "Did you experience any health challenges today?"
    ],
    "movies": [
        "Did you watch any movies or TV shows today?",
        "What film or show made an impression on you?",
        "How did your entertainment choice influence your mood?",
        "Did you discover any new favorites in your watching?",
        "Is there a movie you want to recommend to others?",
        "Did you discuss any film-related topics with someone?",
        "What genre or theme are you exploring in your watching?"
    ],
    "travel": [
        "Have you been to any interesting places recently?",
        "What's a memorable travel experience you've had?",
        "How does travel impact your perspective?",
        "Did you encounter any challenges during your travels?",
        "Is there a destination you're dreaming of visiting?",
        "What's the most unique place you've been to?",
        "Did you learn something new about a culture today?"
    ],
    "music": [
        "Did you listen to any music today?",
        "What song or artist influenced your mood?",
        "How did music enhance your daily activities?",
        "Did you discover any new music that you liked?",
        "Is there a specific genre or style you're into right now?",
        "Did you attend any musical events or performances?",
        "What's your go-to song when you need a mood boost?"
    ],
    "work": [
        "How was your workday today?",
        "Did you achieve any significant milestones at work?",
        "What challenges did you face in your professional life?",
        "Did you learn something new or valuable at work?",
        "How did your work impact your overall mood?",
        "Is there a project or task you're excited about?",
        "Did you discuss work-related topics with colleagues or friends?"
    ],
    "hobbies": [
        "Did you engage in any hobbies or creative activities today?",
        "What's a hobby that brings you joy and relaxation?",
        "How do your hobbies contribute to your well-being?",
        "Did you try something new or experiment with a hobby?",
        "Is there a creative project you're currently working on?",
        "Did you share your hobbies with others today?",
        "What's the most rewarding aspect of your favorite hobby?"
    ],
    "dreams": [
        "Did you have any memorable dreams last night?",
        "Is there a recurring theme in your dreams?",
        "Did a dream leave a lasting impression on you?",
        "How do you interpret your dreams?",
        "Did you experience any lucid dreaming?",
        "Is there a dream you wish you could have again?",
        "Did you share your dreams with someone today?"
    ],
    "pets": [
        "How did your pet(s) brighten your day?",
        "Did you teach your pet a new trick?",
        "What's the funniest thing your pet did today?",
        "Did you take your pet for a walk or playtime?",
        "How does your pet's behavior reflect your mood?",
        "Is there a special bond you share with your pet?",
        "Did your pet do something unexpected today?"
    ],
    "gardening": [
        "Did you spend time in your garden today?",
        "What plants or flowers are blooming?",
        "Did you discover any pests or issues in your garden?",
        "How does gardening contribute to your well-being?",
        "Is there a plant you're excited to see grow?",
        "Did you try a new gardening technique or tool?",
        "What's your favorite thing about your garden?"
    ],
    "games": [
        "Did you play any games today?",
        "What's your favorite board game or video game?",
        "Did you win or lose in a game today?",
        "How does gaming impact your mood?",
        "Is there a game you'd like to learn or master?",
        "Did you play solo or with friends?",
        "What's the most memorable gaming moment of the day?"
    ],
    "education": [
        "What did you learn today that surprised you?",
        "How did you approach your learning goals?",
        "Did you encounter any challenges in your studies?",
        "How do you make learning fun and engaging?",
        "Is there a subject you're excited to explore?",
        "Did you share your knowledge with someone today?",
        "What educational resources did you find helpful?"
    ],
    "fashion": [
        "What outfit made you feel confident today?",
        "Did you try a new style or accessory?",
        "How does fashion influence your self-expression?",
        "Is there a fashion trend you're currently into?",
        "Did you receive compliments on your attire?",
        "How does your clothing choice reflect your mood?",
        "Did you shop for any new fashion items today?"
    ],
    "cooking": [
        "What delicious dish did you cook today?",
        "Did you try a new recipe or cooking technique?",
        "How did cooking contribute to your day?",
        "Is there a comfort food you enjoy making?",
        "Did you experiment with flavors or ingredients?",
        "How do you make cooking a creative process?",
        "Did you share your culinary creations with others?"
    ],
    "technology": [
        "What interesting technology did you interact with today?",
        "How did technology impact your day?",
        "Did you encounter any tech-related challenges?",
        "What app or device did you find useful today?",
        "How much time did you spend on screens today?",
        "Did you learn something new about technology?",
        "What tech-related news caught your attention today?"
    ],
    "nature": [
        "Did you spend time in nature today?",
        "What natural scenery caught your eye?",
        "How does being in nature affect your mood?",
        "Did you encounter any wildlife during your day?",
        "Is there a specific outdoor activity you enjoy?",
        "Did you capture any beautiful nature moments?",
        "What's your favorite season for outdoor activities?"
    ],
    "finance": [
        "How did you manage your finances today?",
        "Did you make any financial decisions or plans?",
        "Is there a budgeting strategy you find effective?",
        "Did you save or invest money today?",
        "How do your financial goals align with your values?",
        "Did you discuss financial matters with someone?",
        "What's your approach to financial well-being?"
    ],
    "creativity": [
        "Did you engage in any creative activities today?",
        "How does creativity contribute to your well-being?",
        "Is there a specific art form you're exploring?",
        "Did you try a new creative project or idea?",
        "How does creativity enhance your problem-solving?",
        "Did you share your creative work with others?",
        "What's the most fulfilling aspect of your creativity?"
    ],
    "mindfulness": [
        "Did you practice mindfulness or meditation today?",
        "How does mindfulness contribute to your focus?",
        "Did you engage in any mindful activities?",
        "How does mindfulness affect your stress levels?",
        "Is there a particular mindfulness technique you prefer?",
        "Did you take moments for self-reflection today?",
        "What's your favorite way to cultivate mindfulness?"
    ],
    "celebrations": [
        "Did you celebrate any special occasions today?",
        "How do celebrations bring people together?",
        "Is there a particular holiday or event you look forward to?",
        "Did you attend or host a celebration?",
        "How do you make ordinary days feel special?",
        "Did you share joyous moments with loved ones?",
        "What's your favorite way to mark a celebration?"
    ],
    "languages": [
        "Did you practice or learn a new language today?",
        "How do languages connect people and cultures?",
        "Is there a language you find fascinating?",
        "Did you encounter any interesting words or phrases?",
        "How does language shape your communication?",
        "Did you engage in multilingual conversations today?",
        "What's your approach to language learning?"
    ],
    "charity": [
        "Did you contribute to a charitable cause today?",
        "How does giving back impact your sense of purpose?",
        "Is there a cause or charity you're passionate about?",
        "Did you volunteer your time or resources?",
        "How do acts of kindness make a difference?",
        "Did you learn about a new charitable initiative?",
        "What's your favorite way to support a good cause?"
    ],
    "reflection": [
        "Did you take time for self-reflection today?",
        "How does reflection contribute to personal growth?",
        "Is there a specific aspect of your day you reflected on?",
        "Did you journal or record your thoughts?",
        "How do reflective practices improve your well-being?",
        "Did you set intentions or goals for the day?",
        "What insights did you gain from your reflections?"
    ],
    "fitness": [
        "How did you stay active and fit today?",
        "Did you enjoy any physical activities or workouts?",
        "Is there a fitness goal you're working towards?",
        "Did you try a new exercise routine?",
        "How does fitness contribute to your energy levels?",
        "Did you participate in a sports activity?",
        "What's your favorite way to stay physically active?"
    ],
    "relationships": [
        "How did you nurture your relationships today?",
        "Is there someone you reached out to or connected with?",
        "Did you have a meaningful conversation with a friend?",
        "How do your relationships contribute to your well-being?",
        "Did you express gratitude to someone special?",
        "How do you balance personal and social relationships?",
        "What's one thing you appreciate about a loved one?"
    ],
    "home": [
        "Did you make your home a cozy and welcoming space today?",
        "How does your home environment affect your mood?",
        "Is there a room or area in your home you enjoy the most?",
        "Did you complete any home-related tasks or projects?",
        "How do you create a sense of comfort in your home?",
        "Did you try a new home decor idea?",
        "What's your favorite thing about your living space?"
    ],
    "astronomy": [
        "Did you observe the night sky or celestial events today?",
        "What astronomical phenomenon fascinates you the most?",
        "Is there a specific constellation you can recognize?",
        "Did you learn something new about space or stars?",
        "How does astronomy contribute to your sense of wonder?",
        "Have you ever used a telescope to explore the sky?",
        "What's your favorite space-related fact or discovery?"
    ],
    "time": [
        "How do you manage your time effectively?",
        "Did you experience a moment of time standing still today?",
        "What's a time-related goal you're working towards?",
        "Is there a specific time of day you find most productive?",
        "Did you use your time wisely or encounter time challenges?",
        "How does time impact your daily routines?",
        "What's your favorite way to spend leisure time?"
    ],
    "emotions": [
        "How do you navigate and express your emotions?",
        "Did you experience a range of emotions today?",
        "Is there an emotion you find challenging to express?",
        "What's a positive emotion that stood out to you?",
        "How do you handle emotions in challenging situations?",
        "Did you learn something new about emotional intelligence?",
        "What's your favorite way to lift your spirits when you're down?"
    ],
    "colors": [
        "Did you notice a particular color that caught your eye today?",
        "How do colors influence your mood and perceptions?",
        "Is there a color that represents your current state of mind?",
        "Did you wear or surround yourself with a specific color today?",
        "How do you incorporate colors into your creative pursuits?",
        "Did you discover a new color combination that you liked?",
        "What's your favorite color and why?"
    ],
    "memory": [
        "Did you reminisce about a fond memory today?",
        "How does memory shape your identity?",
        "Is there a specific memory that brings you joy?",
        "Did you create new memories or experiences today?",
        "How do you preserve and cherish important memories?",
        "Did you share memories with someone close to you?",
        "What's a childhood memory that you often revisit?"
    ],
    "simplicity": [
        "How do you embrace simplicity in your daily life?",
        "Did you simplify any aspects of your routine today?",
        "Is there a minimalist principle you find beneficial?",
        "How does simplicity contribute to your well-being?",
        "Did you declutter or organize your living space?",
        "What's a simple pleasure that brings you happiness?",
        "How do you balance simplicity with complexity in your life?"
    ],
    "dream_destination": [
        "If you could visit any place in the world, where would it be?",
        "What aspects of your dream destination attract you the most?",
        "Is there a specific cultural experience you'd like to have?",
        "How would you imagine spending a day in your dream location?",
        "Did you take any steps toward planning a trip to your dream destination?",
        "How does the idea of traveling to your dream location inspire you?",
        "What's one thing you'd like to explore or discover in your dream destination?"
    ],
    "mind_games": [
        "Did you challenge your mind with puzzles or brain games today?",
        "How do mind games contribute to your cognitive abilities?",
        "Is there a specific type of puzzle you enjoy solving?",
        "Did you learn a new strategy or technique in a mind game?",
        "How do mind games provide mental stimulation for you?",
        "Did you play any trivia or quiz games today?",
        "What's your favorite mind game and why?"
    ],
    "random_acts_of_kindness": [
        "Did you perform a random act of kindness today?",
        "How does spreading kindness impact your own mood?",
        "Is there a specific act of kindness you received from someone?",
        "Did you witness or hear about a heartwarming act of kindness?",
        "How do you incorporate kindness into your daily interactions?",
        "Did you participate in any volunteer or charitable activities?",
        "What's your favorite way to brighten someone else's day?"
    ],
    "technology_innovation": [
        "Did you come across any innovative technologies today?",
        "How does technology shape the way you live and work?",
        "Is there a recent tech innovation that caught your attention?",
        "Did you explore any cutting-edge gadgets or devices?",
        "How do you stay updated on technological advancements?",
        "Is there a problem you'd like to see solved through technology?",
        "What's your perspective on the impact of technology on society?"
    ],
    "reflection_art": [
        "Did you engage in reflective art activities today?",
        "How does art contribute to your self-reflection?",
        "Is there a specific form of art that resonates with your introspection?",
        "Did you create any artwork as a form of reflection?",
        "How does art serve as a medium for expressing inner thoughts?",
        "Did you explore art pieces that provoke contemplation?",
        "What's your favorite way to incorporate art into your reflective practice?"
    ],
    "senses": [
        "Did you pay attention to your senses today?",
        "How do your senses contribute to your overall experiences?",
        "Is there a specific scent or aroma that brings back memories?",
        "Did you engage in activities that heightened your senses?",
        "How does tuning into your senses enhance mindfulness?",
        "Is there a favorite sound that brings you comfort?",
        "What's your favorite way to stimulate your senses?"
    ],
    "nostalgia": [
        "Did you reminisce about the past today?",
        "How does nostalgia influence your present emotions?",
        "Is there a particular item or object that triggers nostalgia for you?",
        "Did you revisit old photos or mementos?",
        "How do you balance nostalgia with living in the present?",
        "Is there a nostalgic memory that always brings a smile to your face?",
        "What's your favorite way to indulge in nostalgic moments?"
    ],
    "adventure": [
        "Did you embark on any adventurous activities today?",
        "How does the spirit of adventure contribute to your life?",
        "Is there a specific adventure or challenge you'd like to pursue?",
        "Did you step out of your comfort zone and try something new?",
        "How do you incorporate a sense of adventure into your routine?",
        "Is there an adventure you're looking forward to in the future?",
        "What's your favorite adventure-related memory?"
    ],
    "celestial_events": [
        "Did you observe any celestial events today?",
        "How does the moon or stars influence your mood?",
        "Is there a specific celestial event you're anticipating?",
        "Did you learn something new about astronomy or space?",
        "How do celestial events connect you to the cosmos?",
        "Is there a celestial event you've always wanted to witness?",
        "What's your favorite memory of watching a celestial event?"
    ],
    "compliments": [
        "Did you give or receive a genuine compliment today?",
        "How does receiving a compliment affect your mood?",
        "Is there a specific compliment that stood out to you?",
        "Did you express appreciation through compliments?",
        "How do compliments contribute to positive interactions?",
        "Is there a compliment you've received that you still remember?",
        "What's your favorite way to compliment others?"
    ],
    "nature_sounds": [
        "Did you immerse yourself in the sounds of nature today?",
        "How do nature sounds contribute to your relaxation?",
        "Is there a specific natural sound that brings you tranquility?",
        "Did you spend time in a place with calming nature sounds?",
        "How do nature sounds influence your mood and well-being?",
        "Is there a favorite nature sound that instantly lifts your spirits?",
        "What's your favorite way to experience the soothing sounds of nature?"
    ],
    "journey": [
        "Did you reflect on your personal journey today?",
        "How does your journey shape your present perspective?",
        "Is there a specific milestone in your journey you're proud of?",
        "Did you encounter any challenges on your journey?",
        "How do you appreciate the growth in your life's journey?",
        "Is there a journey you're looking forward to in the future?",
        "What's one lesson you've learned along your journey?"
    ],
    "words": [
        "Did you come across any interesting words or phrases today?",
        "How do words shape your communication and expression?",
        "Is there a word you find intriguing or beautiful?",
        "Did you learn a new word and its meaning?",
        "How do words convey emotions and ideas?",
        "Is there a favorite quote or saying that resonates with you?",
        "What's your favorite way to play with language and words?"
    ],
    "science_fiction": [
        "Did you explore any science fiction concepts or stories today?",
        "How does science fiction stimulate your imagination?",
        "Is there a specific sci-fi world or universe you find fascinating?",
        "Did you engage in discussions about futuristic technologies?",
        "How does science fiction influence your thoughts about the future?",
        "Is there a sci-fi movie or book you'd recommend to others?",
        "What's your favorite aspect of the science fiction genre?"
    ],
    "rituals": [
        "Did you practice any meaningful rituals today?",
        "How do rituals contribute to your sense of routine and stability?",
        "Is there a specific ritual that holds personal significance?",
        "Did you create a new ritual or modify an existing one?",
        "How do rituals connect you to your cultural or personal identity?",
        "Is there a favorite ritual that brings you comfort?",
        "What's your favorite way to celebrate through rituals?"
    ]
}

@app.route('/landing', methods=["POST", "GET"])
def landing():
        #requested_search = request.values.get("search_input")

    connection = sqlite3.connect(DATA_BASE_FILE_PATH)
    cur = connection.cursor()
    cur.execute("SELECT * FROM Texts")
    records = cur.fetchall()
    connection.commit()  
    connection.close()
    
    return render_template('landing.html',
                           records=records)

'''
@app.route('/search_results', methods=["POST"])
def search_results():
    #requested_search = request.values.get("search_input")

    connection = sqlite3.connect(DATA_BASE_FILE_PATH)
    cur = connection.cursor()
    cur.execute("SELECT * FROM Texts")
    records = cur.fetchall()
    connection.commit()
    connection.close()
    
    return render_template('landing.html',
                           records=records)
'''


@app.route('/viewEx', methods=["POST", "GET"])
def viewEx():
    viewId = request.values.get('viewId')
    connection = sqlite3.connect(DATA_BASE_FILE_PATH)
    cur = connection.cursor()
    cur.execute("SELECT * FROM Texts WHERE viewId=?", (viewId,))
    one_user = cur.fetchone()
    
    email = one_user[1]
    text = one_user[2]
    viewId = one_user[3]
    
    connection.close()

    
    return render_template('viewEx.html', email=email, text=text, viewId=viewId)

@app.route('/daily_exercise', methods=["POST", "GET"])
def daily_exercise():
    random_topic = random.choice(list(question_pool.keys()))
    topic_questions = question_pool[random_topic]
    
    if request.method == 'POST':
        user_responses = request.form.getlist('response')
        session['user_responses'] = user_responses
        return redirect(url_for('index'))
    
    
    
    
    
    
    return render_template('daily_exercise.html', questions=topic_questions[:5])

@app.route('/account', methods=["POST", "GET"])
def account():    
    connection = sqlite3.connect(DATA_BASE_FILE_PATH)
    cur = connection.cursor()
    cur.execute("SELECT * FROM Accounts WHERE email=?", (session["logged_in_user"],))
    one_user = cur.fetchone()
        
    full_name = one_user[1]
    level = one_user[2]
    age = one_user[3]
    password = one_user[5]
        
    connection.close()
        
    return render_template("account.html", full_name=full_name, level=level, age=age, password=password)
    
@app.route('/account_update', methods=["POST"])
def account_update():
    new_full_name = request.values.get('full_name')
    new_level = request.form["proficiency"]
    new_age = request.values.get('age')
    new_password = request.values.get('password')
    email = session["logged_in_user"]
    
    connection = sqlite3.connect(DATA_BASE_FILE_PATH)
    cur = connection.cursor()
    cur.execute(
    "UPDATE Accounts SET full_name=?, level=?, age=?, password=? WHERE email=?",
    (new_full_name, new_level, new_age, new_password, email),)

    connection.commit()
    connection.close()

    return render_template('successful_account_update.html')
    
@app.route('/')
def home():
    return render_template('home.html')

@app.route("/login", methods=["POST", "GET"])
@app.route("/", methods=["POST", "GET"])
def login():
    if request.method == 'GET':
        return render_template("login.html", username="", error_message="")

    email = request.values.get("email")
    password = request.values.get("password")
    connection = sqlite3.connect(DATA_BASE_FILE_PATH)
    cur = connection.cursor()
    cur.execute("SELECT * FROM Accounts WHERE email=? and password=?", (email, password))
    one_user = cur.fetchone()

    if one_user is not None:
        # Put a new value into session
        session["logged_in_user"] = email
        connection.close()
        return redirect("/logged_in_confirmation")
    else:
        connection.close()
        return render_template("login.html", email=email, error_message="Email or password is wrong!")

@app.route('/logged_in_confirmation')
def logged_in_confirmation():
    return render_template('logged_in_confirmation.html')

@app.route("/logged_out", methods=["POST", "GET"])
def logout():
    session.clear()
    return render_template("successful_logout.html")

@app.route('/create_account')
def create_account():
    return render_template('create_account.html')

@app.route('/action_page', methods=["POST"])
def action_page():
    full_name = request.values.get('full_name')
    level = request.form["proficiency"]
    age = request.values.get('age')
    email = request.values.get('email')
    password = request.values.get('password')
    language = request.values.get('language')

    easter_egg = 'easter_egg'
    
    connection = sqlite3.connect(DATA_BASE_FILE_PATH)
    cur = connection.cursor()
    cur.execute(
        "INSERT INTO Accounts (full_name, level, age, email, password, language, previous_seven_subjects) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (full_name, level, age, email, password, language, easter_egg))
    connection.commit()
    connection.close()

    session["logged_in_user"] = email

    
    return render_template('successful_account_creation.html')


    
if __name__ == "__main__":
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    loop = asyncio.get_event_loop()
    aio_app = web.Application()
    wsgi = WSGIHandler(app)
    aio_app.router.add_route('*', '/{path_info: *}', wsgi.handle_request)
    aio_app.router.add_route('GET', '/listen', socket)
    
    
    web.run_app(aio_app, port=5555, host='localhost')