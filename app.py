from flask import Flask, request, render_template_string, session
from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired
import os
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session management

# HTML template as a string
FORM_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instagram Message Sender</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 50px; }
        form { max-width: 500px; margin: auto; }
        label { display: block; margin: 10px 0 5px; }
        input, textarea { width: 100%; padding: 8px; margin-bottom: 10px; }
        button { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        button:hover { background-color: #45a049; }
        .message { margin-top: 20px; color: #333; }
    </style>
</head>
<body>
    <h1>Instagram Message Sender</h1>
    <form method="POST" action="/send_messages">
        <label for="username">Instagram Username:</label>
        <input type="text" id="username" name="username" value="{{ username }}" required>
        
        <label for="password">Instagram Password:</label>
        <input type="password" id="password" name="password" required>
        
        <label for="thread_id">Group Thread ID:</label>
        <input type="text" id="thread_id" name="thread_id" required>
        
        <label for="message_file">Message File Path (e.g., CP.txt):</label>
        <input type="text" id="message_file" name="message_file" required>
        
        <label for="message_count">Number of Messages to Send:</label>
        <input type="number" id="message_count" name="message_count" min="1" required>
        
        <label for="otp">OTP (if required):</label>
        <input type="text" id="otp" name="otp" placeholder="Enter OTP if prompted">
        
        <button type="submit">Send Messages</button>
    </form>
    <div class="message">{{ message | safe }}</div>
</body>
</html>
"""

# Function to read message from file
def read_message_from_file(file_path):
    try:
        with open(file_path, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        return None
    except Exception as e:
        return f"Error reading file: {str(e)}"

# Route for the main page
@app.route('/', methods=['GET'])
def index():
    return render_template_string(FORM_TEMPLATE, message="", username=session.get('username', ''))

# Route to handle form submission and send messages
@app.route('/send_messages', methods=['POST'])
def send_messages():
    # Get form data
    username = request.form['username']
    password = request.form['password']
    thread_id = request.form['thread_id']
    message_file = request.form['message_file']
    message_count = int(request.form['message_count'])
    otp = request.form.get('otp', '')

    # Store username in session to prefill the form
    session['username'] = username

    # Read the message from the specified file
    message = read_message_from_file(message_file)
    if not message or isinstance(message, str) and message.startswith("Error"):
        return render_template_string(FORM_TEMPLATE, message=f"Error: {message or 'Could not read message from ' + message_file}", username=username)

    # Initialize Instagram client
    cl = Client()
    result_message = ""

    # Optional: Add proxy to avoid IP blocks
    proxy = os.getenv("INSTAGRAM_PROXY")
    if proxy:
        cl.set_proxy(proxy)

    try:
        # Attempt login
        cl.login(username, password)
        result_message += "Login successful!<br>"

    except ChallengeRequired:
        # Handle Instagram challenge (e.g., OTP)
        if not otp:
            result_message += "Instagram requires verification. Check your email/phone for an OTP and enter it above.<br>"
            return render_template_string(FORM_TEMPLATE, message=result_message, username=username)
        else:
            try:
                # Pass OTP to resolve challenge
                cl.challenge_resolve(cl.last_json, code=otp)
                result_message += "OTP verified, login successful!<br>"
            except Exception as otp_error:
                result_message += f"OTP verification failed: {str(otp_error)}<br>"
                return render_template_string(FORM_TEMPLATE, message=result_message, username=username)

    except Exception as e:
        result_message += f"Login failed: {str(e)}<br>"
        return render_template_string(FORM_TEMPLATE, message=result_message, username=username)

    # Send messages if login succeeds
    try:
        for i in range(message_count):
            cl.direct_send(message, thread_ids=[thread_id])
            result_message += f"Message {i+1}/{message_count} sent successfully!<br>"
            time.sleep(5)  # Throttle to avoid rate limits
    except Exception as e:
        result_message += f"Error sending message: {str(e)}<br>"

    result_message += "Execution completed."
    return render_template_string(FORM_TEMPLATE, message=result_message, username=username)
