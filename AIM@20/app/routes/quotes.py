from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Quote

quotes_bp = Blueprint('quotes', __name__)

@quotes_bp.route('/')
@login_required
def index():
    """Display all quotes with management options"""
    quotes = Quote.query.filter_by(is_active=True).all()
    return render_template('quotes/index.html', quotes=quotes)

@quotes_bp.route('/random')
@login_required
def random_quote():
    """Get a random active quote"""
    import random
    quotes = Quote.query.filter_by(is_active=True).all()
    if quotes:
        quote = random.choice(quotes)
        return jsonify({
            'text': quote.text,
            'author': quote.author,
            'category': quote.category
        })
    return jsonify({'error': 'No quotes available'}), 404

@quotes_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new quote"""
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        author = request.form.get('author', '').strip()
        category = request.form.get('category', 'motivation')

        if not text:
            flash('Quote text is required', 'error')
            return redirect(url_for('quotes.create'))

        quote = Quote(
            text=text,
            author=author if author else None,
            category=category
        )
        db.session.add(quote)
        db.session.commit()

        flash('Quote added successfully!', 'success')
        return redirect(url_for('quotes.index'))

    return render_template('quotes/create.html')

@quotes_bp.route('/<int:quote_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(quote_id):
    """Edit an existing quote"""
    quote = Quote.query.get_or_404(quote_id)

    if request.method == 'POST':
        quote.text = request.form.get('text', '').strip()
        quote.author = request.form.get('author', '').strip() or None
        quote.category = request.form.get('category', 'motivation')
        quote.is_active = 'is_active' in request.form

        if not quote.text:
            flash('Quote text is required', 'error')
            return redirect(url_for('quotes.edit', quote_id=quote_id))

        db.session.commit()
        flash('Quote updated successfully!', 'success')
        return redirect(url_for('quotes.index'))

    return render_template('quotes/edit.html', quote=quote)

@quotes_bp.route('/<int:quote_id>/delete', methods=['POST'])
@login_required
def delete(quote_id):
    """Delete a quote"""
    quote = Quote.query.get_or_404(quote_id)
    db.session.delete(quote)
    db.session.commit()

    flash('Quote deleted successfully!', 'success')
    return redirect(url_for('quotes.index'))

@quotes_bp.route('/api/random')
@login_required
def api_random():
    """API endpoint for random quote"""
    return random_quote()