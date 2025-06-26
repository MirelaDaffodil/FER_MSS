# 🎵 Facial Emotion Recognition and Music Synchronization System

This Python application captures real-time facial emotions using your webcam and synchronizes music playback accordingly using **Spotify** or **local music files**. It enhances your mood by playing songs that match your emotional state.

---

## 📸 Features

- 🎭 Detects 7 emotions: **Happy**, **Sad**, **Angry**, **Fear**, **Surprise**, **Disgust**, and **Neutral**
- 🤖 Uses **DeepFace** for facial emotion recognition
- 🎶 Plays emotion-based music via:
  - **Spotify** (automated track selection)
  - **Fallback local MP3s**
- 🎚️ Volume control, pause/resume, and change music options
- 🧠 Logs emotion history with timestamp
- 🖥️ Fullscreen GUI built with **Tkinter** and **OpenCV**

---

## 🛠 Requirements

Install all dependencies with:

```bash
pip install -r requirements.txt
You also need:

A webcam

A valid Spotify Developer App (Client ID and Secret)

📂 Folder Structure
bash
Copy
Edit
FER_MSS/
├── fer_mss.py              # Main application
├── requirements.txt        # Python dependencies
├── README.md               # Project overview
├── .gitignore
└── local_music/            # Fallback songs per emotion
    ├── happy.mp3
    ├── sad.mp3
    ├── angry.mp3
    ├── fear.mp3
    ├── surprise.mp3
    ├── disgust.mp3
    └── neutral.mp3
🚀 How to Run
Clone this repo and open a terminal:

bash
Copy
Edit
git clone https://github.com/MirelaDaffodil/FER_MSS.git
cd FER_MSS
Install dependencies:

bash
Copy
Edit
pip install -r requirements.txt
Set up Spotify credentials (Client ID, Secret, Redirect URI) in the code.

Run the app:

bash
Copy
Edit
python fer_mss.py
💡 How It Works
The app detects your face and emotions in real-time.

If the same emotion is maintained for 15 seconds, it freezes the detection.

Based on the emotion:

Tries to play a matching Spotify song

If Spotify fails, plays a local MP3 fallback

UI displays the emotion, confidence, song name, and history.

🧑‍💻 Tech Stack
Python

OpenCV

DeepFace

Spotipy (Spotify API)

Tkinter

Pygame (for local MP3 playback)

📷 Emotion Examples 
Emotion	Caption	Music Type
Happy 😊	Enjoy the moment!	Upbeat track
Sad 😢	It's okay to feel down sometimes	Comforting melody
Angry 😠	Take a deep breath and stay calm	Calming sound
Surprise 😲	Wow! That was unexpected!	Energetic tune
Fear 😨	Stay strong, you've got this!	Soothing sounds
Disgust 🤢	Something doesn't feel right?	Neutral music
Neutral 😐	A moment of calm and balance	Relaxing track

📌 Notes
ESC toggles fullscreen mode

Press “Try Again” to restart detection

Emotion history is saved on exit

Local files must exist in local_music/
