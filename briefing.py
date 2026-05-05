#!/usr/bin/env python3
"""Daily morning briefing — generates web page + sends push notification."""

import base64
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# ── Config ────────────────────────────────────────────────────────────────────
NTFY_TOPIC    = "luke-brief-x7k2m9"
PAGE_URL      = "https://hirschluke-hub.github.io/Morning-Brief/"

TWILIO_SID    = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_TOKEN  = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_NUMBER = "+18588081672"

SCRIPT_DIR           = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR             = os.path.join(SCRIPT_DIR, "docs")
HTML_FILE            = os.path.join(DOCS_DIR, "index.html")

GOOGLE_CLIENT_ID     = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REFRESH_TOKEN = os.environ["GOOGLE_REFRESH_TOKEN"]

LAT, LON = 32.7157, -117.1611  # San Diego

COLOR_CATEGORIES = {
    "1":  ("Work",     "#b39ddb"),
    "10": ("School",   "#81c784"),
}

# 146 quotes with thematically matched hero images — rotates by day of year
QUOTE_IMAGE_PAIRS = [
    # ── Morning / New Day ─────────────────────────────────────────────────────
    ("Every morning we are born again. What we do today matters most.", "Buddha", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("With the new day comes new strength and new thoughts.", "Eleanor Roosevelt", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("This is a wonderful day. I've never seen this one before.", "Maya Angelou", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("Each morning when I open my eyes I say to myself: I, not events, have the power to make me happy or unhappy today.", "Groucho Marx", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("An early-morning walk is a blessing for the whole day.", "Henry David Thoreau", "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1400&q=85"),
    ("Morning is when I am awake and there is a dawn in me.", "Henry David Thoreau", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("The sun is a daily reminder that we too can rise again from the darkness, that we too can shine our own light.", "S. Ajna", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("Every day begins with an act of courage and hope: getting out of bed.", "Mason Cooley", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("Smile in the mirror. Do that every morning and you'll start to see a big difference in your life.", "Yoko Ono", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("The breeze at dawn has secrets to tell you. Don't go back to sleep.", "Rumi", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("Morning comes whether you set the alarm or not.", "Ursula K. Le Guin", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("It is a serious thing just to be alive on this fresh morning in this broken world.", "Mary Oliver", "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1400&q=85"),
    ("First thing every morning before you arise say out loud, 'I believe,' three times.", "Ovid", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("Every day I wake up and I feel lucky.", "Reba McEntire", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("Each morning we wake up is a gift.", "Anonymous", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    # ── New Beginnings ────────────────────────────────────────────────────────
    ("Every day is a new beginning. Take a deep breath and start again.", "Anonymous", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("Every morning you have two choices: continue to sleep with your dreams, or wake up and chase them.", "Anonymous", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("New day, new blessings. Don't let yesterday's failures ruin the beauty of today.", "Anonymous", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("Be willing to be a beginner every single morning.", "Meister Eckhart", "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1400&q=85"),
    ("Today is a new day. Stop telling yourself it's just another boring day.", "Steve Maraboli", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("Your future is created by what you do today, not tomorrow.", "Robert Kiyosaki", "https://images.unsplash.com/photo-1476611338391-6f395a0dd82e?w=1400&q=85"),
    ("Don't let yesterday take up too much of today.", "Will Rogers", "https://images.unsplash.com/photo-1434725039720-aaad6dd32dfe?w=1400&q=85"),
    ("One small positive thought in the morning can change your whole day.", "Dalai Lama", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("Today is your day! Your mountain is waiting. So get on your way.", "Dr. Seuss", "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1400&q=85"),
    # ── Mindset / Attitude ────────────────────────────────────────────────────
    ("Wake up determined. Go to bed satisfied.", "Dwayne 'The Rock' Johnson", "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1400&q=85"),
    ("Your attitude, not your aptitude, will determine your altitude.", "Zig Ziglar", "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1400&q=85"),
    ("The only limit to our realization of tomorrow will be our doubts of today.", "Franklin D. Roosevelt", "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=1400&q=85"),
    ("Whether you think you can or you think you can't, you're right.", "Henry Ford", "https://images.unsplash.com/photo-1476611338391-6f395a0dd82e?w=1400&q=85"),
    ("The pessimist sees difficulty in every opportunity. The optimist sees opportunity in every difficulty.", "Winston Churchill", "https://images.unsplash.com/photo-1540390769625-2fc3f8b1d50c?w=1400&q=85"),
    ("Nothing is impossible, the word itself says 'I'm possible!'", "Audrey Hepburn", "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=1400&q=85"),
    ("Keep your face always toward the sunshine, and shadows will fall behind you.", "Walt Whitman", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt", "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1400&q=85"),
    ("You are never too old to set another goal or to dream a new dream.", "C.S. Lewis", "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1400&q=85"),
    ("Act as if what you do makes a difference. It does.", "William James", "https://images.unsplash.com/photo-1434725039720-aaad6dd32dfe?w=1400&q=85"),
    ("Start where you are. Use what you have. Do what you can.", "Arthur Ashe", "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1400&q=85"),
    ("The secret of getting ahead is getting started.", "Mark Twain", "https://images.unsplash.com/photo-1476611338391-6f395a0dd82e?w=1400&q=85"),
    ("You don't have to be great to start, but you have to start to be great.", "Zig Ziglar", "https://images.unsplash.com/photo-1434725039720-aaad6dd32dfe?w=1400&q=85"),
    ("Push yourself, because no one else is going to do it for you.", "Anonymous", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    ("The harder you work for something, the greater you'll feel when you achieve it.", "Anonymous", "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1400&q=85"),
    ("Great things never come from comfort zones.", "Anonymous", "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=1400&q=85"),
    ("Dream it. Believe it. Build it.", "Anonymous", "https://images.unsplash.com/photo-1484910292437-025e5d13ce87?w=1400&q=85"),
    ("Success doesn't just find you. You have to go out and get it.", "Anonymous", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    # ── Hard Work / Perseverance ──────────────────────────────────────────────
    ("The pain you feel today is the strength you feel tomorrow.", "Anonymous", "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1400&q=85"),
    ("Work hard in silence, let your success be your noise.", "Frank Ocean", "https://images.unsplash.com/photo-1484910292437-025e5d13ce87?w=1400&q=85"),
    ("The difference between ordinary and extraordinary is that little extra.", "Jimmy Johnson", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    ("Success is the sum of small efforts, repeated day in and day out.", "Robert Collier", "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1400&q=85"),
    ("It's not about how bad you want it. It's about how hard you're willing to work for it.", "Anonymous", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    ("Don't stop when you're tired. Stop when you're done.", "Anonymous", "https://images.unsplash.com/photo-1549719386-74dfcbf7dbed?w=1400&q=85"),
    ("A year from now you may wish you had started today.", "Karen Lamb", "https://images.unsplash.com/photo-1476611338391-6f395a0dd82e?w=1400&q=85"),
    ("Doubt kills more dreams than failure ever will.", "Suzy Kassem", "https://images.unsplash.com/photo-1540390769625-2fc3f8b1d50c?w=1400&q=85"),
    ("The only way to do great work is to love what you do.", "Steve Jobs", "https://images.unsplash.com/photo-1484910292437-025e5d13ce87?w=1400&q=85"),
    ("Your dreams don't work unless you do.", "John C. Maxwell", "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1400&q=85"),
    ("Don't watch the clock; do what it does. Keep going.", "Sam Levenson", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    ("You've got to get up every morning with determination if you're going to go to bed with satisfaction.", "George Lorimer", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("Be so good they can't ignore you.", "Steve Martin", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    ("Do something today that your future self will thank you for.", "Sean Patrick Flanery", "https://images.unsplash.com/photo-1434725039720-aaad6dd32dfe?w=1400&q=85"),
    ("Motivation gets you going, but discipline keeps you growing.", "John C. Maxwell", "https://images.unsplash.com/photo-1549719386-74dfcbf7dbed?w=1400&q=85"),
    # ── Athletes / Sports ─────────────────────────────────────────────────────
    ("I've missed more than 9,000 shots in my career. I've lost almost 300 games. I've failed over and over again. That is why I succeed.", "Michael Jordan", "https://images.unsplash.com/photo-1752166673288-f8e354af4fb9?w=1400&q=85"),
    ("The moment you give up is the moment you let someone else win.", "Kobe Bryant", "https://images.unsplash.com/photo-1752166673288-f8e354af4fb9?w=1400&q=85"),
    ("I hated every minute of training, but I said: don't quit. Suffer now and live the rest of your life as a champion.", "Muhammad Ali", "https://images.unsplash.com/photo-1549719386-74dfcbf7dbed?w=1400&q=85"),
    ("Don't count the days, make the days count.", "Muhammad Ali", "https://images.unsplash.com/photo-1549719386-74dfcbf7dbed?w=1400&q=85"),
    ("You are in danger of living a life so comfortable and soft that you will die without ever realizing your true potential.", "David Goggins", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    ("Hard work beats talent when talent doesn't work hard.", "Tim Notke", "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1400&q=85"),
    ("Champions keep playing until they get it right.", "Billie Jean King", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    ("Either you run the day, or the day runs you.", "Jim Rohn", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    ("Today I will do what others won't, so tomorrow I can accomplish what others can't.", "Jerry Rice", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    # ── Courage / Resilience ──────────────────────────────────────────────────
    ("Courage is not the absence of fear, but the triumph over it.", "Nelson Mandela", "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=1400&q=85"),
    ("You have within you right now, everything you need to deal with whatever the world can throw at you.", "Brian Tracy", "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=1400&q=85"),
    ("It always seems impossible until it's done.", "Nelson Mandela", "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=1400&q=85"),
    ("Fall seven times, stand up eight.", "Japanese Proverb", "https://images.unsplash.com/photo-1540390769625-2fc3f8b1d50c?w=1400&q=85"),
    ("The comeback is always stronger than the setback.", "Anonymous", "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=1400&q=85"),
    ("Strength does not come from physical capacity. It comes from an indomitable will.", "Mahatma Gandhi", "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=1400&q=85"),
    ("You are stronger than you think.", "Anonymous", "https://images.unsplash.com/photo-1540390769625-2fc3f8b1d50c?w=1400&q=85"),
    ("She believed she could, so she did.", "R.S. Grey", "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=1400&q=85"),
    ("Sometimes you win, sometimes you learn.", "John Maxwell", "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1400&q=85"),
    ("When you feel like quitting, think about why you started.", "Anonymous", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    ("Be fearless in the pursuit of what sets your soul on fire.", "Jennifer Lee", "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=1400&q=85"),
    ("Stars can't shine without darkness.", "Anonymous", "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1400&q=85"),
    ("Rock bottom became the solid foundation on which I rebuilt my life.", "J.K. Rowling", "https://images.unsplash.com/photo-1540390769625-2fc3f8b1d50c?w=1400&q=85"),
    ("The strongest people are not those who show strength in front of us, but those who win battles we know nothing about.", "Anonymous", "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=1400&q=85"),
    ("Everything you've ever wanted is on the other side of fear.", "George Addair", "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=1400&q=85"),
    ("Tough times never last, but tough people do.", "Robert H. Schuller", "https://images.unsplash.com/photo-1540390769625-2fc3f8b1d50c?w=1400&q=85"),
    ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Winston Churchill", "https://images.unsplash.com/photo-1540390769625-2fc3f8b1d50c?w=1400&q=85"),
    # ── Purpose / Life ────────────────────────────────────────────────────────
    ("The two most important days in your life are the day you are born and the day you find out why.", "Mark Twain", "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1400&q=85"),
    ("Life is 10% what happens to us and 90% how we react to it.", "Charles R. Swindoll", "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1400&q=85"),
    ("In the middle of every difficulty lies opportunity.", "Albert Einstein", "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?w=1400&q=85"),
    ("Life is short, and it is here to be lived.", "Kate Winslet", "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=1400&q=85"),
    ("I am not a product of my circumstances. I am a product of my decisions.", "Stephen R. Covey", "https://images.unsplash.com/photo-1434725039720-aaad6dd32dfe?w=1400&q=85"),
    ("You only live once, but if you do it right, once is enough.", "Mae West", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("The purpose of life is a life of purpose.", "Robert Byrne", "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=1400&q=85"),
    ("In the end, it's not the years in your life that count. It's the life in your years.", "Abraham Lincoln", "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1400&q=85"),
    ("What lies behind us and what lies before us are tiny matters compared to what lies within us.", "Ralph Waldo Emerson", "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1400&q=85"),
    ("It is never too late to be what you might have been.", "George Eliot", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("Be yourself; everyone else is already taken.", "Oscar Wilde", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment.", "Ralph Waldo Emerson", "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=1400&q=85"),
    ("Above all, be the heroine of your life, not the victim.", "Nora Ephron", "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=1400&q=85"),
    ("Your time is limited, so don't waste it living someone else's life.", "Steve Jobs", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("Discipline is choosing between what you want now and what you want most.", "Abraham Lincoln", "https://images.unsplash.com/photo-1476611338391-6f395a0dd82e?w=1400&q=85"),
    # ── Happiness / Gratitude ─────────────────────────────────────────────────
    ("Happiness is not something ready-made. It comes from your own actions.", "Dalai Lama", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("Count your age by friends, not years. Count your life by smiles, not tears.", "John Lennon", "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1400&q=85"),
    ("The best and most beautiful things in the world cannot be seen or even touched — they must be felt with the heart.", "Helen Keller", "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=1400&q=85"),
    ("Spread love everywhere you go. Let no one ever come to you without leaving happier.", "Mother Teresa", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("When I started counting my blessings, my whole life turned around.", "Willie Nelson", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("Gratitude turns what we have into enough.", "Anonymous", "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1400&q=85"),
    ("Joy is what happens to us when we allow ourselves to recognize how good things really are.", "Marianne Williamson", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("The present moment is filled with joy and happiness. If you are attentive, you will see it.", "Thich Nhat Hanh", "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1400&q=85"),
    ("Happiness is a direction, not a place.", "Sydney J. Harris", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("Choose to be optimistic, it feels better.", "Dalai Lama", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("The most wasted of all days is one without laughter.", "E.E. Cummings", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("Enjoy the little things, for one day you may look back and realize they were the big things.", "Robert Brault", "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1400&q=85"),
    # ── Action / Initiative ───────────────────────────────────────────────────
    ("The journey of a thousand miles begins with one step.", "Lao Tzu", "https://images.unsplash.com/photo-1476611338391-6f395a0dd82e?w=1400&q=85"),
    ("Don't wait. The time will never be just right.", "Napoleon Hill", "https://images.unsplash.com/photo-1434725039720-aaad6dd32dfe?w=1400&q=85"),
    ("You miss 100% of the shots you don't take.", "Wayne Gretzky", "https://images.unsplash.com/photo-1752166673288-f8e354af4fb9?w=1400&q=85"),
    ("The best time to plant a tree was 20 years ago. The second best time is now.", "Chinese Proverb", "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1400&q=85"),
    ("Go confidently in the direction of your dreams. Live the life you have imagined.", "Henry David Thoreau", "https://images.unsplash.com/photo-1476611338391-6f395a0dd82e?w=1400&q=85"),
    ("Twenty years from now you will be more disappointed by the things that you didn't do than by the ones you did do.", "Mark Twain", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("I never dreamed about success. I worked for it.", "Estée Lauder", "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1400&q=85"),
    ("If not now, when?", "Hillel", "https://images.unsplash.com/photo-1434725039720-aaad6dd32dfe?w=1400&q=85"),
    ("The best revenge is massive success.", "Frank Sinatra", "https://images.unsplash.com/photo-1484910292437-025e5d13ce87?w=1400&q=85"),
    ("A dream doesn't become reality through magic; it takes sweat, determination and hard work.", "Colin Powell", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    ("Do what you can, with what you have, where you are.", "Theodore Roosevelt", "https://images.unsplash.com/photo-1533240332313-0db49b459ad6?w=1400&q=85"),
    ("Show up. Do the work. Trust the process.", "Anonymous", "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=1400&q=85"),
    # ── Kindness / Connection ─────────────────────────────────────────────────
    ("Be kind whenever possible. It is always possible.", "Dalai Lama", "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1400&q=85"),
    ("In a world where you can be anything, be kind.", "Anonymous", "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=1400&q=85"),
    ("We rise by lifting others.", "Robert Ingersoll", "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1400&q=85"),
    ("No act of kindness, no matter how small, is ever wasted.", "Aesop", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("The meaning of life is to find your gift. The purpose of life is to give it away.", "Pablo Picasso", "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1400&q=85"),
    ("You are enough just as you are.", "Anonymous", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("Love yourself first and everything else falls into line.", "Lucille Ball", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("The best preparation for tomorrow is doing your best today.", "H. Jackson Brown Jr.", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    # ── Wisdom / Reflection ───────────────────────────────────────────────────
    ("Knowing yourself is the beginning of all wisdom.", "Aristotle", "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1400&q=85"),
    ("The more that you read, the more things you will know. The more that you learn, the more places you'll go.", "Dr. Seuss", "https://images.unsplash.com/photo-1476611338391-6f395a0dd82e?w=1400&q=85"),
    ("Yesterday is history, tomorrow is a mystery, today is a gift of God, which is why we call it the present.", "Bil Keane", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1400&q=85"),
    ("All our dreams can come true, if we have the courage to pursue them.", "Walt Disney", "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1400&q=85"),
    ("I can't change the direction of the wind, but I can adjust my sails to always reach my destination.", "Jimmy Dean", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("Not all those who wander are lost.", "J.R.R. Tolkien", "https://images.unsplash.com/photo-1434725039720-aaad6dd32dfe?w=1400&q=85"),
    ("In three words I can sum up everything I've learned about life: it goes on.", "Robert Frost", "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1400&q=85"),
    ("Two roads diverged in a wood, and I — I took the one less traveled by, and that has made all the difference.", "Robert Frost", "https://images.unsplash.com/photo-1434725039720-aaad6dd32dfe?w=1400&q=85"),
    ("The best is yet to come.", "Robert Browning", "https://images.unsplash.com/photo-1418985991508-e47386d96a71?w=1400&q=85"),
    ("Life is not measured by the number of breaths we take, but by the moments that take our breath away.", "Maya Angelou", "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1400&q=85"),
    ("Wherever you go, go with all your heart.", "Confucius", "https://images.unsplash.com/photo-1476611338391-6f395a0dd82e?w=1400&q=85"),
    ("Live in the sunshine, swim the sea, drink the wild air.", "Ralph Waldo Emerson", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1400&q=85"),
    ("The world is a book and those who do not travel read only one page.", "Saint Augustine", "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=1400&q=85"),
    ("In the sweetness of friendship let there be laughter, and sharing of pleasures.", "Kahlil Gibran", "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1400&q=85"),
    ("Don't be pushed around by the fears in your mind. Be led by the dreams in your heart.", "Roy T. Bennett", "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1400&q=85"),
    ("You have brains in your head. You have feet in your shoes. You can steer yourself any direction you choose.", "Dr. Seuss", "https://images.unsplash.com/photo-1434725039720-aaad6dd32dfe?w=1400&q=85"),
]

WEATHER_CODES = {
    0: "Clear skies", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog", 51: "Light drizzle", 53: "Drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    80: "Rain showers", 81: "Showers", 95: "Thunderstorm",
}

# ── Weather ───────────────────────────────────────────────────────────────────
def get_weather():
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={LAT}&longitude={LON}"
            f"&daily=temperature_2m_max,weathercode"
            f"&temperature_unit=fahrenheit"
            f"&timezone=America/Los_Angeles"
        )
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
        temp = round(data["daily"]["temperature_2m_max"][0])
        code = data["daily"]["weathercode"][0]
        desc = WEATHER_CODES.get(code, "San Diego")
        return temp, desc
    except Exception:
        return None, None


# ── To-Do (inbound SMS) ───────────────────────────────────────────────────────
def get_todos():
    try:
        from email.utils import parsedate_to_datetime
        import urllib.parse
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
            f"?To={urllib.parse.quote(TWILIO_NUMBER)}&PageSize=50"
        )
        creds = base64.b64encode(f"{TWILIO_SID}:{TWILIO_TOKEN}".encode()).decode()
        req   = urllib.request.Request(url, headers={"Authorization": f"Basic {creds}"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        msgs = []
        for m in data.get("messages", []):
            if m.get("direction") != "inbound":
                continue
            sent = parsedate_to_datetime(m["date_sent"])
            if sent >= cutoff:
                msgs.append({"text": m["body"].strip(), "time": sent})
        msgs.sort(key=lambda x: x["time"])

        # Find the most recent "clear" — only keep messages after it
        last_clear = None
        for msg in msgs:
            if msg["text"].strip().lower().rstrip("!.:") == "clear":
                last_clear = msg["time"]
        if last_clear:
            msgs = [m for m in msgs if m["time"] > last_clear]

        # "done: <item>" removes matching todos
        done  = {m["text"][5:].strip().lower() for m in msgs if m["text"].lower().startswith("done:")}
        todos = [m["text"] for m in msgs if not m["text"].lower().startswith("done:") and m["text"].lower().strip() not in done]

        print(f"Todos found: {todos}")
        return todos
    except Exception as e:
        print(f"Todo fetch error: {e}")
        return []


# ── Google Calendar ───────────────────────────────────────────────────────────
def get_calendar_service():
    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return build("calendar", "v3", credentials=creds)


def get_todays_events(service):
    now   = datetime.now(timezone.utc)
    start = now.replace(hour=0,  minute=0,  second=0,  microsecond=0)
    end   = now.replace(hour=23, minute=59, second=59, microsecond=0)

    result = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for e in result.get("items", []):
        color_id          = e.get("colorId", "")
        category, color   = COLOR_CATEGORIES.get(color_id, ("Personal", "#80cbc4"))
        start_str         = e["start"].get("dateTime", e["start"].get("date", ""))
        end_str           = e["end"].get("dateTime",   e["end"].get("date", ""))
        events.append({
            "summary":  e.get("summary", "Untitled"),
            "start":    start_str,
            "end":      end_str,
            "category": category,
            "color":    color,
        })
    return events


def fmt_time(dt_str):
    try:
        if "T" not in dt_str:
            return "All day"
        dt     = datetime.fromisoformat(dt_str)
        hour   = dt.strftime("%I").lstrip("0") or "12"
        minute = dt.strftime("%M")
        ampm   = dt.strftime("%p").lower()
        return f"{hour}:{minute}{ampm}" if minute != "00" else f"{hour}{ampm}"
    except Exception:
        return dt_str


# ── HTML ──────────────────────────────────────────────────────────────────────
def generate_html(events, todos, temp, weather_desc, quote, author, image_url):
    today        = datetime.now()
    day_name     = today.strftime("%A").upper()
    date_display = today.strftime("%B %-d, %Y")
    weather_str      = f"{temp}°" if temp else ""
    weather_desc_str = weather_desc if weather_desc else ""

    if events:
        rows = ""
        for e in events:
            start_t    = fmt_time(e["start"])
            end_t      = fmt_time(e["end"])
            time_range = start_t if start_t == "All day" else f"{start_t} — {end_t}"
            rows += f"""
          <div class="event" style="border-left-color:{e['color']}">
            <div class="event-time">{time_range}</div>
            <div class="event-name">{e['summary']}</div>
            <div class="event-category" style="color:{e['color']}">{e['category']}</div>
          </div>"""
        events_html = rows
    else:
        events_html = '<div class="empty">Free day — make it yours.</div>'

    if todos:
        todos_html = "".join(
            f'<div class="todo-item"><div class="circle"></div>{item}</div>'
            for item in todos
        )
    else:
        todos_html = '<div class="empty">Text (858) 808-1672 to add tasks.</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Morning Brief</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #0d0d0d;
      color: #e0e0e0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif;
      min-height: 100vh;
    }}

    /* ── Hero ── */
    .hero {{
      position: relative;
      width: 100%;
      height: 60vh;
      min-height: 360px;
      background: url('{image_url}') center/cover no-repeat;
    }}

    .hero-overlay {{
      position: absolute;
      inset: 0;
      background: linear-gradient(
        to bottom,
        rgba(0,0,0,0.3) 0%,
        rgba(0,0,0,0.1) 35%,
        rgba(0,0,0,0.85) 100%
      );
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 28px 32px 36px;
    }}

    .hero-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}

    .greeting {{
      font-size: 13px;
      font-weight: 500;
      letter-spacing: 2.5px;
      text-transform: uppercase;
      color: rgba(255,255,255,0.55);
      text-shadow: 0 1px 4px rgba(0,0,0,0.5);
    }}

    .hero-bottom {{ }}

    .hero-day {{
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 3px;
      color: rgba(255,255,255,0.38);
      text-transform: uppercase;
      margin-bottom: 6px;
    }}

    .hero-date {{
      font-size: 38px;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.5px;
      text-shadow: 0 2px 12px rgba(0,0,0,0.6);
      margin-bottom: 18px;
      line-height: 1;
    }}

    .hero-quote {{
      font-size: 16px;
      font-style: italic;
      color: rgba(255,255,255,0.85);
      line-height: 1.6;
      text-shadow: 0 1px 4px rgba(0,0,0,0.6);
      max-width: 500px;
    }}

    .hero-author {{
      margin-top: 8px;
      font-size: 12px;
      color: rgba(255,255,255,0.38);
      text-shadow: 0 1px 3px rgba(0,0,0,0.5);
      letter-spacing: 0.5px;
    }}

    /* ── Weather ── */
    .weather-strip {{
      background: #111;
      border-bottom: 1px solid #1c1c1c;
      padding: 24px 32px;
      display: flex;
      align-items: center;
      gap: 20px;
    }}

    .weather-temp-big {{
      font-size: 52px;
      font-weight: 200;
      color: #f0f0f0;
      line-height: 1;
    }}

    .weather-right {{}}

    .weather-condition {{
      font-size: 16px;
      color: #aaa;
      font-weight: 400;
    }}

    .weather-location {{
      font-size: 12px;
      color: #3a3a3a;
      margin-top: 4px;
      text-transform: uppercase;
      letter-spacing: 1.5px;
    }}

    /* ── Content ── */
    .content {{
      max-width: 860px;
      margin: 0 auto;
      padding: 36px 32px 64px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 40px;
    }}

    @media (max-width: 600px) {{
      .content {{ grid-template-columns: 1fr; gap: 32px; padding: 28px 20px 56px; }}
      .hero-date {{ font-size: 28px; }}
    }}

    .label {{
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 2.5px;
      color: #888;
      font-weight: 600;
      margin-bottom: 16px;
    }}

    /* ── Event cards ── */
    .event {{
      background: #111;
      border-radius: 12px;
      border-left: 4px solid #444;
      padding: 14px 16px;
      margin-bottom: 10px;
    }}

    .event-time {{
      font-size: 19px;
      font-weight: 700;
      color: #fff;
      line-height: 1;
      margin-bottom: 5px;
    }}

    .event-name {{
      font-size: 14px;
      color: #888;
      line-height: 1.35;
      margin-bottom: 5px;
    }}

    .event-category {{
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      opacity: 0.7;
    }}

    /* ── To-Do ── */
    .todo-item {{
      display: flex;
      align-items: center;
      gap: 14px;
      background: #111;
      border-radius: 12px;
      border-left: 4px solid #e8e8e8;
      padding: 14px 16px;
      margin-bottom: 10px;
      font-size: 15px;
      font-weight: 500;
      color: #e8e8e8;
    }}

    .circle {{
      width: 18px;
      height: 18px;
      border: 2px solid #e8e8e8;
      border-radius: 50%;
      flex-shrink: 0;
    }}

    .empty {{ color: #383838; font-size: 14px; padding: 8px 0; }}

    .bottom {{
      text-align: center;
      padding: 0 32px 56px;
      font-size: 13px;
      color: #2e2e2e;
      font-style: italic;
      letter-spacing: 0.3px;
    }}
  </style>
</head>
<body>

  <div class="hero">
    <div class="hero-overlay">
      <div class="hero-top">
        <div class="greeting">Good morning, Luke.</div>
      </div>
      <div class="hero-bottom">
        <div class="hero-day">{day_name}</div>
        <div class="hero-date">{date_display}</div>
        <div class="hero-quote">"{quote}"</div>
        <div class="hero-author">— {author}</div>
      </div>
    </div>
  </div>

  <div class="weather-strip">
    <div class="weather-temp-big">{weather_str}</div>
    <div class="weather-right">
      <div class="weather-condition">{weather_desc_str}</div>
      <div class="weather-location">San Diego, CA — Today's High</div>
    </div>
  </div>

  <div class="content">
    <div>
      <div class="label">Today's Schedule</div>
      {events_html}
    </div>
    <div>
      <div class="label">To-Do</div>
      {todos_html}
    </div>
  </div>

  <div class="bottom">You're building the life you dreamed of. Keep going.</div>

</body>
</html>"""


# ── Save & send ───────────────────────────────────────────────────────────────
def save_html(html):
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)


def send_notification(title, body):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=body.encode(),
        headers={"Title": title, "Click": PAGE_URL},
    )
    urllib.request.urlopen(req, timeout=5)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    service        = get_calendar_service()
    events         = get_todays_events(service)
    todos          = get_todos()
    temp, weather  = get_weather()
    day_of_year = datetime.now().timetuple().tm_yday
    quote, author, image_url = QUOTE_IMAGE_PAIRS[day_of_year % len(QUOTE_IMAGE_PAIRS)]

    html = generate_html(events, todos, temp, weather, quote, author, image_url)
    save_html(html)

    day = datetime.now().strftime("%A")
    send_notification("Morning Brief", f"Good morning Luke. Your {day} brief is ready.")
    print("Done.")
