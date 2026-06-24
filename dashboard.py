# dashboard.py
import os
from flask import render_template, send_from_directory
from dashboard import create_dashboard_app

# Instantiate the app using your blueprint factory configuration
app = create_dashboard_app()

# Set up secret key or configurations if needed
app.secret_key = os.urandom(24)

@app.route("/")
def index():
    """
    Serves the beautiful index.html template from the templates/ directory.
    Your frontend JavaScript (app.js) handles all data loading asynchronously.
    """
    return render_template("index.html")

if __name__ == "__main__":
    # Run the consolidated dashboard application
    print("Starting CW Biomatric Sync Dashboard on http://localhost:5000")
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True # Set to False in production
    )
