import os
import time
import base64
import requests
import streamlit as st
from gtts import gTTS
from io import BytesIO
import speech_recognition as sr
from audio_recorder_streamlit import audio_recorder
from streamlit_float import *

# Define the Rasa webhook URL
RASA_WEBHOOK_URL = 'http://localhost:5002/webhooks/rest/webhook'  # Update with your Rasa server URL if needed

# Initialize TTS using gTTS
def text_to_speech(input_text):
    tts = gTTS(text=input_text, lang='en')
    audio_data = BytesIO()
    tts.write_to_fp(audio_data)
    audio_data.seek(0)
    return audio_data

# Autoplay the generated audio in the browser
def autoplay_audio(audio_data):
    audio_base64 = base64.b64encode(audio_data.read()).decode("utf-8")
    audio_html = f"""
    <audio autoplay>
    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
    </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

# Convert speech to text using SpeechRecognition
def speech_to_text(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand that."
    except sr.RequestError as e:
        return f"Could not request results from Google Speech Recognition service; {e}"

# Send the user input to Rasa and get the bot's response
def send_message_to_rasa(message):
    """Send a message to Rasa and return the response."""
    try:
        # Send the user's message to the Rasa webhook
        response = requests.post(RASA_WEBHOOK_URL, json={"message": message})
        response.raise_for_status()  # Check if the request was successful

        # Parse the JSON response from Rasa
        rasa_responses = response.json()

        # Check if we got a valid response
        if rasa_responses:
            return rasa_responses[0].get('text', 'I am sorry, I did not understand that.')
        else:
            return "I didn't receive a response from the bot."

    except requests.exceptions.RequestException as e:
        # Handle errors related to the request
        st.error(f"Error when sending message to Rasa: {e}")
        return "Sorry, I couldn't connect to the server. Please try again later."

# Streamlit UI
st.header("𝐊𝐆𝐢𝐒𝐋 𝐕𝐨𝐱𝐀𝐬𝐬𝐢𝐬𝐭🤖")

# Inject custom CSS to hide "Click to record" text
# hide_click_to_record_css = """
#     <style>
#     /* Hide the "Click to record" text */
#     button[title="Click to record"]::after {
#         content: '';
#     }
#     </style>
# """
# st.markdown(hide_click_to_record_css, unsafe_allow_html=True)

# Create footer container for the microphone
footer_container = st.container()
with footer_container:
    # st.markdown("<div style='height:350px;'></div>", unsafe_allow_html=True)  # Add spacing above the footer

    # audio_bytes = audio_recorder()
    audio_bytes = audio_recorder(text=None, icon_size="3x", sample_rate=16000)


# Display messages from session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! Welcome to Customer Support for health insurance. I’m Evas. May I know your policy number please?😊"}
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Process audio input
if audio_bytes:
    with st.spinner("Processing your request..📜"):
        wav_file_path = "temp_audio.wav"
        with open(wav_file_path, "wb") as f:
            f.write(audio_bytes)
        
        # Convert the speech to text
        transcript = speech_to_text(wav_file_path)
        st.session_state.messages.append({"role": "user", "content": transcript})

        # Display user message
        with st.chat_message("user"):
            st.write(transcript)

        os.remove(wav_file_path)

        # Send user message to Rasa and get the response
        bot_response = send_message_to_rasa(transcript)
        st.session_state.messages.append({"role": "assistant", "content": bot_response})

        # Convert the bot's response to speech and play it
        audio_file = text_to_speech(bot_response)
        autoplay_audio(audio_file)

        with st.chat_message("assistant"):
            st.write(bot_response)

# Float the footer container and provide CSS to target it with
footer_container.float("bottom: 0rem; right: 10px;")

# st.markdown("""
#     <style>
#     /* Hide the "Click to record" text */
#     .css-14xtw13 p {
#         display: none;
#     }
#     /* Style the chat input and audio recorder in the footer */
#     .stContainer {
#         display: flex;
#         align-items: center;
#         justify-content: space-between;
#         bottom: 0;
#         width: 100%;
#         padding: 1rem;
#         background-color: #ffffff;
#         border-top: 1px solid #e0e0e0;
#         z-index: 1000;
#     }
#     .stTextInput > div > input {
#         height: 3rem;  /* Increase the height of the chat input */
#         font-size: 1.25rem;  /* Increase the font size */
#         padding: 0.5rem;  /* Adjust padding */
#     }
#     .stTextInput {
#         width: 100%;
#         margin-right: 10rem;
#     }
#     .stAudioRecorder {
#         margin-left: auto;
#     }
#     </style>
# """, unsafe_allow_html=True)

