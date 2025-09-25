#!/usr/bin/env python3
"""
Seed script to populate the database with motivational quotes.
Run this script to add default quotes to the application.
"""

from app import create_app
from app.models import Quote, db

def seed_quotes():
    """Add motivational quotes to the database"""

    quotes = [
        {
            'text': "The only way to do great work is to love what you do.",
            'author': "Steve Jobs",
            'category': "motivation"
        },
        {
            'text': "Success is not final, failure is not fatal: It is the courage to continue that counts.",
            'author': "Winston Churchill",
            'category': "perseverance"
        },
        {
            'text': "Your time is limited, so don't waste it living someone else's life.",
            'author': "Steve Jobs",
            'category': "focus"
        },
        {
            'text': "The future belongs to those who believe in the beauty of their dreams.",
            'author': "Eleanor Roosevelt",
            'category': "success"
        },
        {
            'text': "Don't watch the clock; do what it does. Keep going.",
            'author': "Sam Levenson",
            'category': "focus"
        },
        {
            'text': "The secret of getting ahead is getting started.",
            'author': "Mark Twain",
            'category': "motivation"
        },
        {
            'text': "Quality is not an act, it is a habit.",
            'author': "Aristotle",
            'category': "wisdom"
        },
        {
            'text': "The way to get started is to quit talking and begin doing.",
            'author': "Walt Disney",
            'category': "motivation"
        },
        {
            'text': "Believe you can and you're halfway there.",
            'author': "Theodore Roosevelt",
            'category': "motivation"
        },
        {
            'text': "The expert in anything was once a beginner.",
            'author': "Helen Hayes",
            'category': "perseverance"
        },
        {
            'text': "Knowledge is power, but enthusiasm pulls the switch.",
            'author': "Ivern Ball",
            'category': "motivation"
        },
        {
            'text': "The only limit to our realization of tomorrow will be our doubts of today.",
            'author': "Franklin D. Roosevelt",
            'category': "success"
        },
        {
            'text': "You miss 100% of the shots you don't take.",
            'author': "Wayne Gretzky",
            'category': "motivation"
        },
        {
            'text': "The best way to predict the future is to create it.",
            'author': "Peter Drucker",
            'category': "success"
        },
        {
            'text': "Keep your face always toward the sunshine—and shadows will fall behind you.",
            'author': "Walt Whitman",
            'category': "motivation"
        }
    ]

    app = create_app()

    with app.app_context():
        # Check if quotes already exist
        existing_count = Quote.query.count()
        if existing_count > 0:
            print(f"Database already has {existing_count} quotes. Skipping seed.")
            return

        # Add quotes
        for quote_data in quotes:
            quote = Quote(
                text=quote_data['text'],
                author=quote_data['author'],
                category=quote_data['category']
            )
            db.session.add(quote)

        db.session.commit()
        print(f"Successfully added {len(quotes)} motivational quotes to the database!")

if __name__ == "__main__":
    seed_quotes()