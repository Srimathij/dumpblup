import os
import requests
import speech_recognition as sr
import streamlit as st
from gtts import gTTS
from io import BytesIO
import base64
from audio_recorder_streamlit import audio_recorder

# Function to convert text to speech and play it in the browser
def text_to_speech_and_play(text):
    """Convert text to speech using gTTS and play directly in the browser."""
    try:
        # Generate the speech with gTTS and save it to a BytesIO object
        tts = gTTS(text=text, lang='en')
        audio_data = BytesIO()
        tts.write_to_fp(audio_data)  # This writes the speech to the BytesIO object
        audio_data.seek(0)

        # Convert BytesIO object to base64 for embedding in HTML
        audio_base64 = base64.b64encode(audio_data.read()).decode()
        audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio>'
        st.markdown(audio_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error during text-to-speech conversion: {e}")

# Function to send a message to Rasa and return the response
def send_message_to_rasa(message):
    """Send a message to Rasa and return the response."""
    try:
        response = requests.post('http://localhost:5002/webhooks/rest/webhook', json={"message": message})
        response.raise_for_status()  # Check if the request was successful
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error when sending message to Rasa: {e}")
        return []

# Initialize session state variables
def initialize_session_state():
    if "messages" not in st.session_state:
        # Send an initial greeting to Rasa to start the conversation
        initial_message = "Hello"
        response_json = send_message_to_rasa(initial_message)
        initial_bot_message = response_json[0].get('text', '') if response_json else "Hello, how can I assist you today?"
        
        st.session_state.messages = [
            {"role": "assistant", "content": initial_bot_message}
        ]
    if "user_query" not in st.session_state:
        st.session_state.user_query = ""

initialize_session_state()

# Streamlit UI
st.header("Voice Interaction with Rasa Bot")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Custom CSS to fix the footer container (where the mic will be) at the bottom
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        bottom: 0;
        width: 100%;
        background-color: rgba(255, 255, 255, 0.9);
        padding: 10px;
        text-align: center;
        z-index: 9999;
    }
    .main-content {
        margin-bottom: 100px; /* Ensure the main content does not overlap with footer */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Ensure that the chat and content have enough margin from the footer
st.markdown('<div class="main-content"></div>', unsafe_allow_html=True)

# Handle user input via audio recording inside a fixed footer
footer_container = st.container()
with footer_container:
    transcript = None
    
    # Fixed footer UI for mic input
    st.markdown('<div class="footer">', unsafe_allow_html=True)
    
    # Mic input via audio_recorder inside the footer
    audio_bytes = audio_recorder(icon_size="3x", sample_rate=16000)
    
    if audio_bytes:
        # Write the audio bytes to a file
        with st.spinner("Processing..."):
            wav_file_path = "temp_audio.wav"
            with open(wav_file_path, "wb") as f:
                f.write(audio_bytes)
            
            # Convert speech to text using the recognizer
            r = sr.Recognizer()
            with sr.AudioFile(wav_file_path) as source:
                audio = r.record(source)
            try:
                transcript = r.recognize_google(audio)
                st.session_state.user_query = transcript
                st.session_state.messages.append({"role": "user", "content": transcript})
                os.remove(wav_file_path)
            except sr.UnknownValueError:
                st.error("Sorry, could not understand the audio")
            except sr.RequestError as e:
                st.error(f"Speech recognition error: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# If there's a user query, process it
if st.session_state.user_query:
    with st.spinner("Bot is typing..."):
        response_json = send_message_to_rasa(st.session_state.user_query)
        if response_json:
            bot_message = response_json[0].get('text', '')
            
            # Add bot's response to session state for display
            st.session_state.messages.append({"role": "assistant", "content": bot_message})

            # Display the bot's response text in the Streamlit UI
            st.write(f"Bot says: {bot_message}")
            
            # Convert bot's response to speech and play it
            text_to_speech_and_play(bot_message)
