import os
from flask import Flask, request, jsonify
import redis
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Redis configuration for session management
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),  # Replace with your cloud Redis host
    port=int(os.getenv('REDIS_PORT', 6379)),    # Replace with your Redis port
    password=os.getenv('REDIS_PASSWORD', ''),   # Redis password if set
    decode_responses=True
)

# WhatsApp Business Number and FAQ data
WHATSAPP_BUSINESS_NUMBER = "+2347081932925"
FAQ_DATA = {
    "What services do you offer?": "At Udiwonder, we provide top-notch automation, tech integration, sales funnel design, and website setup to help businesses save time and increase revenue. Visit https://udiwonder.com for more details.",
    "How do I contact support?": "You can contact us by emailing support@udiwonder.com or by replying 'Speak to Support' here on WhatsApp.",
    "What is the Define, Design, Deploy process?": "Our 3D process is our service blueprint. Define: Understanding your needs. Design: Bringing ideas to life. Deploy: Making your solution live. More details at https://udiwonder.com.",
    "How do I start a project with Udiwonder?": "To start a project, visit https://udiwonder.com and fill out our contact form, or reply 'Get Started' here on WhatsApp.",
    # Add more FAQs as needed
}

# Session management class
class UserSession:
    def __init__(self, phone_number):
        self.phone_number = phone_number
        self.redis_key = f"whatsapp_session:{phone_number}"
    
    def get_session(self):
        """Get existing session or create a new one."""
        session_data = redis_client.get(self.redis_key)
        if session_data:
            return json.loads(session_data)
        return self._create_new_session()
    
    def _create_new_session(self):
        """Create a new session with default values."""
        session = {
            'phone_number': self.phone_number,
            'last_interaction': datetime.now().isoformat(),
            'current_state': 'INITIAL',
            'context': {},
        }
        self.update_session(session)
        return session
    
    def update_session(self, session_data):
        """Update session in Redis."""
        redis_client.setex(
            self.redis_key,
            timedelta(hours=24),  # Session expires after 24 hours
            json.dumps(session_data)
        )

# Function to handle FAQs
def handle_faq_request(phone_number, message_text):
    """Check if the message matches an FAQ question."""
    faq_response = FAQ_DATA.get(message_text.strip())
    if faq_response:
        return create_text_response(phone_number, faq_response)
    else:
        return create_text_response(
            phone_number,
            "I'm not sure how to help with that. Try asking about our services or say 'Speak to Support'."
        )

# Interactive message templates
def create_text_response(phone_number, text):
    """Create a text response message."""
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "text",
        "text": {
            "body": text
        }
    }

# Main handler for user interactions
def handle_user_interaction(phone_number, message_type, message_text):
    """Process incoming messages and respond based on FAQ data."""
    session = UserSession(phone_number)
    current_session = session.get_session()
    
    # Update last interaction time
    current_session['last_interaction'] = datetime.now().isoformat()
    
    if message_type == 'text':
        response = handle_faq_request(phone_number, message_text)
    else:
        response = create_text_response(
            phone_number,
            "Please send a text message with your question or type 'Speak to Support'."
        )
    
    # Update session with any changes
    session.update_session(current_session)
    return response

# Webhook endpoint to receive and respond to WhatsApp messages
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    phone_number = data['from']
    message_type = data['type']
    message_text = data['message']['text']['body']
    
    response = handle_user_interaction(phone_number, message_type, message_text)
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
