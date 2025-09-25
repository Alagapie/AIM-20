#!/usr/bin/env python3
"""
Run script for AIM20/VISION20 Flask application
"""

import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5005)),
        debug=app.config['DEBUG']
    )