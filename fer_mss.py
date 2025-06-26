import os
import sys
import warnings


warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

import tkinter as tk
from tkinter import ttk, font, messagebox, filedialog
from PIL import Image, ImageTk
import cv2
import logging
logging.getLogger('cv2').setLevel(logging.ERROR)
logging.getLogger('tensorflow').setLevel(logging.ERROR)

import pygame
import numpy as np
from deepface import DeepFace
import time
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import threading
import random
import traceback
from collections import deque, Counter
import json

class EmotionRecognitionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        print("[INFO] Starting EmotionRecognitionApp...")

        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.report_callback_exception = self.handle_exception

        # Initialize Spotify client
        
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id='d7cedbef1a244115836f2d78508b31cd',
                client_secret='739ce7ee4481450e8eba66e9b3f2f837',
                redirect_uri='http://127.0.0.1:8080/callback',
                scope='user-modify-playback-state,user-read-playback-state,user-library-read,user-library-modify',
                cache_path='.spotifycache',
                open_browser=True
            ))
        # Test the connection immediately
            self.sp.current_user()
        except Exception as e:
            print(f"[ERROR] Spotify initialization failed: {e}")
            self.sp = None
    
        self.emotion_music_query = {
            'happy': 'upbeat music',
            'sad': 'comforting music',
            'angry': 'calming music',
            'fear': 'soothing music',
            'surprise': 'energetic music',
            'disgust': 'neutral background music',
            'neutral': 'relaxing music'
        }

        
        pygame.mixer.pre_init(44100, -16, 2, 512)  
        pygame.mixer.init()
        self.local_music_files = {
            'happy': 'local_music/happy.mp3',
            'sad': 'local_music/sad.mp3',
            'angry': 'local_music/angry.mp3',
            'surprise': 'local_music/surprise.mp3',
            'fear': 'local_music/fear.mp3',
            'disgust': 'local_music/disgust.mp3',
            'neutral': 'local_music/neutral.mp3'
        }

        # Emotion captions
        self.emotion_captions = {
            'happy': "You look happy! Let's keep the good vibes going with some upbeat music!",
            'sad': "You seem sad. Here's some comforting music to lift your spirits...",
            'angry': "You appear angry. Let's help you relax with some calming tunes.",
            'surprise': "You look surprised! Let's match that excitement with some energetic music!",
            'fear': "You seem fearful. Here's some soothing music to help you feel safe.",
            'disgust': "You look disgusted. Let's change your mood with some neutral tracks.",
            'neutral': "You appear neutral. Enjoy some relaxing background music."
        }

        # Application state
        self.current_emotion = "neutral"

        self.current_song = None
        self.is_playing = False
        self.detection_active = True
        self.frozen_emotion = "neutral"
        self.frozen_confidence = 0
        self.frozen_image = None
        self.emotion_history = []
        self.emotion_journey_log = deque(maxlen=30)
        self.last_emotion_change_time = time.time()
        self.same_emotion_duration = 0
        self.volume_level = 50  # Default volume level
        self.frozen_image = np.zeros((480, 640, 3), dtype=np.uint8)  # Placeholder black image
        
        # GUI setup
        self.title("Facial Emotion Recognition and Music Synchronization System")
        self.attributes('-fullscreen', True)
        self.configure(bg='#f0f0f0')
        self.bind('<Escape>', lambda e: self.attributes('-fullscreen', not self.attributes('-fullscreen')))

        # Style setup
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.helvetica = font.Font(family="Helvetica", size=12)
        self.helvetica_bold = font.Font(family="Helvetica", size=12, weight="bold")
        self.title_font = font.Font(family="Helvetica", size=16, weight="bold")

        # Initialize camera
        print("[INFO] Initializing camera...")
        
        self.cap = None
        for index in range(3):  # Try multiple indexes if needed
            cap_try = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if cap_try.isOpened():
                self.cap = cap_try
                break

        if not self.cap or not self.cap.isOpened():
            messagebox.showerror("Camera Error", "Could not open camera. Please check your connection.")
            return

            if not self.cap.isOpened():
                print("[ERROR] Could not open camera")
                messagebox.showerror("Camera Error", "Could not open camera. Please check your camera connection.")
                self.cap = None
                return  # Exit initialization if camera fails

        # Set camera properties (adjusted to your original higher resolution)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Keep your preferred resolution
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        print("[INFO] Camera initialized successfully")
        # Start camera update thread
        self.camera_thread = threading.Thread(target=self.update_camera, daemon=True)
        self.camera_thread.start()
        

        # Create initial detection interface
        self.create_detection_interface()

        # Preload DeepFace model in background
        # self.preload_deepface()

    def preload_deepface(self):
        try:
            print("[INFO] Preloading DeepFace model...")
            blank_img = np.zeros((224, 224, 3), dtype=np.uint8)
            _ = DeepFace.analyze(blank_img, actions=['emotion'], enforce_detection=False)
            print("[INFO] DeepFace model loaded successfully")
        except Exception as e:
            print(f"[ERROR] DeepFace preload failed: {e}")
        

    def handle_exception(self, exc, val, tb):
        pass  # completely silent


    def create_detection_interface(self):
        """Create the initial full-screen camera detection interface"""
        # Clear any existing widgets
        for widget in self.winfo_children():
            widget.destroy()

        # Full-screen camera view
        self.camera_frame = tk.Frame(self, bg='black')
        self.camera_frame.pack(fill=tk.BOTH, expand=True)

        self.camera_label = tk.Label(self.camera_frame, bg='black')
        self.camera_label.pack(fill=tk.BOTH, expand=True)

        # Detection status label (hidden initially)
        self.detection_status = tk.Label(self.camera_frame, 
                                        text="Align your face in the frame",
                                        font=("Helvetica", 16),
                                        bg='black', fg='white')
        self.detection_status.place(relx=0.5, rely=0.1, anchor=tk.CENTER)

    def create_confirmation_interface(self):
        """Create the confirmation interface with all controls"""
        # Clear any existing widgets
        for widget in self.winfo_children():
            widget.destroy()

        # Main container
        main_frame = tk.Frame(self, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header
        header_frame = tk.Frame(main_frame, bg='#2c3e50', bd=2, relief=tk.RAISED)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(header_frame, 
                text="Emotion Detected: Music Selection",
                font=self.title_font,
                fg='white',
                bg='#2c3e50',
                padx=20,
                pady=10).pack()

        # Content area
        content_frame = tk.Frame(main_frame, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel - Emotion info
        left_panel = tk.Frame(content_frame, bg='#ecf0f1', bd=2, relief=tk.SUNKEN)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))

        # Emotion display
        emotion_frame = tk.Frame(left_panel, bg='#ecf0f1', padx=10, pady=10)
        emotion_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Label(emotion_frame, 
                text="Detected Emotion:",
                font=self.helvetica_bold,
                bg='#ecf0f1').pack(anchor=tk.W)

        self.confirmed_emotion_label = tk.Label(emotion_frame,
                                              text=self.frozen_emotion.capitalize(),
                                              font=("Helvetica", 24, "bold"),
                                              bg='#ecf0f1',
                                              fg='#2c3e50')
        self.confirmed_emotion_label.pack(anchor=tk.W, pady=5)

        tk.Label(emotion_frame,
                text=f"Confidence: {self.frozen_confidence}%",
                font=self.helvetica,
                bg='#ecf0f1').pack(anchor=tk.W)

        # Caption
        caption_frame = tk.Frame(left_panel, bg='#ecf0f1', padx=10, pady=10)
        caption_frame.pack(fill=tk.X, pady=10)

        tk.Label(caption_frame,
                text="Suggestion:",
                font=self.helvetica_bold,
                bg='#ecf0f1').pack(anchor=tk.W)

        self.caption_box = tk.Label(caption_frame,
                                  text=self.emotion_captions.get(self.frozen_emotion, ""),
                                  font=self.helvetica,
                                  bg='#ecf0f1',
                                  wraplength=300,
                                  justify=tk.LEFT)
        self.caption_box.pack(anchor=tk.W, pady=5)

        # Action buttons
        button_frame = tk.Frame(left_panel, bg='#ecf0f1', padx=10, pady=10)
        button_frame.pack(fill=tk.X, pady=10)

        tk.Button(button_frame,
                 text="Play Music",
                 command=self.play_selected_emotion,
                 bg='#27ae60',
                 fg='white',
                 font=self.helvetica_bold,
                 width=15).pack(pady=5, fill=tk.X)

        tk.Button(button_frame,
                 text="Change Song",
                 command=self.change_song,
                 bg='#3498db',
                 fg='white',
                 font=self.helvetica_bold,
                 width=15).pack(pady=5, fill=tk.X)

        # Volume control
        volume_frame = tk.Frame(button_frame, bg='#ecf0f1')
        volume_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(volume_frame,
                text="Volume:",
                font=self.helvetica,
                bg='#ecf0f1').pack(side=tk.LEFT)
        
        self.volume_slider = tk.Scale(volume_frame,
                                     from_=0, to=100,
                                     orient=tk.HORIZONTAL,
                                     command=self.set_volume,
                                     bg='#ecf0f1',
                                     highlightthickness=0)
        self.volume_slider.set(self.volume_level)
        self.volume_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Playback controls
        playback_frame = tk.Frame(button_frame, bg='#ecf0f1')
        playback_frame.pack(fill=tk.X, pady=5)

        self.pause_btn = tk.Button(
            playback_frame,
            text="Pause",
            command=self.pause_music,
            bg='#f39c12',
            fg='white',
            font=self.helvetica_bold,
            width=7
        )
        self.pause_btn.pack(side=tk.LEFT, padx=2)

        self.resume_btn = tk.Button(
            playback_frame,
            text="Resume",
            command=self.resume_music,
            bg='#1abc9c',
            fg='white',
            font=self.helvetica_bold,
            width=7
        )
        self.resume_btn.pack(side=tk.LEFT, padx=2)



        
        tk.Button(
            playback_frame,
            text="Help",
            command=self.show_help,
            bg='#9b59b6',
            fg='white',
            font=self.helvetica_bold,
            width=7
        ).pack(side=tk.RIGHT, padx=2)
        tk.Button(button_frame,
                 text="Try Again",
                 command=self.return_to_detection,
                 bg='#e74c3c',
                 fg='white',
                 font=self.helvetica_bold,
                 width=15).pack(pady=5, fill=tk.X)

        # Right panel - Now playing and history
        right_panel = tk.Frame(content_frame, bg='#f0f0f0')
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Now playing
        now_playing_frame = tk.Frame(right_panel, bg='#3498db', bd=2, relief=tk.RAISED)
        now_playing_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(now_playing_frame,
                text="NOW PLAYING",
                font=self.helvetica_bold,
                bg='#3498db',
                fg='white',
                padx=10).pack(side=tk.LEFT)

        self.now_playing_label = tk.Label(now_playing_frame,
                                        text="No song selected",
                                        font=self.helvetica,
                                        bg='#3498db',
                                        fg='white')
        self.now_playing_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Frozen image display - REPLACE YOUR EXISTING CODE WITH THIS
        if hasattr(self, 'frozen_image') and self.frozen_image is not None:
            try:
                img_frame = tk.Frame(right_panel, bg='#ecf0f1', bd=2, relief=tk.SUNKEN)
                img_frame.pack(fill=tk.X, pady=(0, 20))
        
                # Convert image (handle both BGR and RGB cases)
                if isinstance(self.frozen_image, np.ndarray):
                    if self.frozen_image.shape[2] == 3:  # Check if it's 3-channel
                        display_img = cv2.cvtColor(self.frozen_image, cv2.COLOR_BGR2RGB)
                    else:
                        display_img = self.frozen_image
                else:
                    display_img = self.frozen_image
            
                img = Image.fromarray(display_img)
                img = img.resize((400, 300), Image.LANCZOS)  # Increased size
        
                # Must keep reference to prevent garbage collection
                self.confirmation_img = ImageTk.PhotoImage(image=img)  # Use persistent attribute
        
                self.frozen_img_label = tk.Label(img_frame, image=self.confirmation_img, bg='#ecf0f1')
                self.frozen_img_label.pack(pady=5)
        
            except Exception as e:
                print(f"[DEBUG] Image display error: {e}")
        # History
        history_frame = tk.Frame(right_panel, bg='#ecf0f1', bd=2, relief=tk.SUNKEN)
        history_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(history_frame,
                text="Emotion History",
                font=self.helvetica_bold,
                bg='#ecf0f1').pack(fill=tk.X, pady=5)

        scrollbar = ttk.Scrollbar(history_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.history_log = tk.Listbox(history_frame,
            yscrollcommand=scrollbar.set,
            bg='white',
            fg='#2c3e50',
            font=self.helvetica,
            selectbackground='#3498db',
            selectforeground='white'
        )
        self.history_log.pack(fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.history_log.yview)

        # Add current emotion to history
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"{timestamp} - {self.frozen_emotion.capitalize()}"
        self.emotion_history.append(entry)

        # Load all history into the Listbox
        self.history_log.delete(0, tk.END)  # Clear and refill to persist across tries
        for item in self.emotion_history:
            self.history_log.insert(tk.END, item)

    def update_camera(self):
        while True:
            try:
                if self.cap is None or not self.detection_active:  
                    time.sleep(1)
                    continue

                ret, frame = self.cap.read()
                if not ret:
                    # print("[WARNING] Camera frame read failed")
                    time.sleep(0.1)
                    continue

                # Process frame and detect emotion
                frame, emotion, emotions = self.detect_emotion(frame)
                confidence = emotions.get(emotion, 0) if emotions else 0

                # Track emotion duration
                if emotion.lower() == self.current_emotion:
                    self.same_emotion_duration = time.time() - self.last_emotion_change_time
                else:
                    self.current_emotion = emotion.lower()
                    self.last_emotion_change_time = time.time()
                    self.same_emotion_duration = 0

                # Draw face rectangle and emotion label
                try:
                    # Get face location (simplified - in real app use face detection coordinates)
                    height, width = frame.shape[:2]
                    face_center = (width//2, height//3)
                    face_size = min(width, height) // 2
                    
                    # Draw rectangle
                    cv2.rectangle(frame, 
                                 (face_center[0]-face_size//2, face_center[1]-face_size//2),
                                 (face_center[0]+face_size//2, face_center[1]+face_size//2),
                                 (0, 255, 0), 2)
                    
                    # Put emotion text
                    cv2.putText(frame, f"{emotion.capitalize()} ({int(confidence)}%)", 
                              (face_center[0]-face_size//2, face_center[1]-face_size//2 - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # Show timer if same emotion
                    if self.same_emotion_duration > 0:
                        cv2.putText(frame, f"{int(self.same_emotion_duration)}s", 
                                  (face_center[0]+face_size//2 + 10, face_center[1]-face_size//2 - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                except:
                    pass


                # Check if we should freeze the emotion (30 seconds of same emotion)
                if self.same_emotion_duration >= 15:  # After 20 seconds of same emotion
                    self.frozen_emotion = emotion.lower()
                    self.frozen_confidence = int(confidence)
                    # Convert BGR to RGB and store the frame
                    self.frozen_image = cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB)  # Fix color channels
                    self.detection_active = False
                    self.after(0, self.create_confirmation_interface)
                    continue

                # Display frame in GUI thread
                self.after(0, lambda: self.update_camera_display(frame))

                time.sleep(0.05)

            except Exception as e:
                time.sleep(0.5)
                continue 
    def update_camera_display(self, frame):
        try:
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)

            if hasattr(self, 'camera_label'):
                self.camera_label.imgtk = imgtk
                self.camera_label.configure(image=imgtk)
        except Exception as e:
            print(f"[ERROR] Display update error: {e}")

    def detect_emotion(self, frame):
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = DeepFace.analyze(rgb_frame, actions=['emotion'], enforce_detection=False)
        
            # Handle cases where no face is detected
            if isinstance(result, list):
                if not result:  # Empty list (no faces)
                    return frame, "neutral", {}
                result = result[0]  # Take first face if multiple
        
            # Ensure emotions exist and are valid
            emotions = result.get('emotion', {})
            if not emotions:  # Check if emotions dict is empty
                return frame, "neutral", {}
            
            emotion = max(emotions.items(), key=lambda x: x[1])[0]  # Safer max()
            confidence = int(emotions[emotion])
        
            return frame, emotion, emotions
        
        except Exception as e:
            print(f"[ERROR] Emotion detection failed: {e}")
            return frame, "neutral", {}

    def play_selected_emotion(self):
        """Play music dynamically based on detected emotion - runs in background"""
        if not self.frozen_emotion:  
            return

        def _play():
            try:
                # First try Spotify
                if self.sp:
                    query = self.emotion_music_query.get(self.frozen_emotion, self.frozen_emotion)
                    results = self.sp.search(q=query, type='track', limit=10)
                    tracks = results['tracks']['items']
                
                    if tracks:
                        random_track = random.choice(tracks)
                        uri = random_track['uri']
                        self.play_song_for_uri(uri)
                        return
                
                # Fallback to local music if Spotify fails
                self.play_local_music(self.frozen_emotion)
            
            except Exception as e:
                print(f"[ERROR] Music playback failed: {e}")
                self.play_local_music(self.frozen_emotion)

        # Run in a separate thread
        threading.Thread(target=_play, daemon=True).start()

    def update_now_playing(self, uri):
        """More robust version with error handling"""
        if not uri:
            if hasattr(self, "now_playing_label"):
                self.now_playing_label.config(text="No song selected")
            return

        try:
            track = self.sp.track(uri)
            if not track:
                raise ValueError("Empty track data")

            song_name = track.get('name', 'Unknown Track')
            artists = track.get('artists', [{}])
            artist_names = ", ".join([a.get('name', 'Unknown Artist') for a in artists])

            if hasattr(self, "now_playing_label"):
                self.now_playing_label.config(
                    text=f"{song_name} by {artist_names}"
                )

            if hasattr(self, "play_pause_btn"):
                self.play_pause_btn.config(text="Pause")

            self.is_playing = True

        except Exception as e:
            print(f"[NOW PLAYING UPDATE ERROR] {e}")
            if hasattr(self, "now_playing_label"):
                self.now_playing_label.config(
                    text="Couldn't load track info"
                )
      

    def change_song(self):
        """Search and play a new random song based on the same emotion theme"""
        if self.frozen_emotion:
            query = self.emotion_music_query.get(self.frozen_emotion, self.frozen_emotion)

            try:
                results = self.sp.search(q=query, type='track', limit=10)
                tracks = results['tracks']['items']

                if tracks:
                    random_track = random.choice(tracks)
                    uri = random_track['uri']
                    self.play_song_for_uri(uri)
                else:
                    messagebox.showerror("Error", f"No songs found for {self.frozen_emotion}")

            except Exception as e:
                print(f"[SPOTIFY SEARCH ERROR] {e}")
                self.play_local_music(self.frozen_emotion)

    def toggle_playback(self):
        if not self.sp or not self.current_song:
            return

        try:
            if self.is_playing:
                self.sp.pause_playback()
                self.play_pause_btn.config(text="Resume")
            else:
                self.sp.start_playback()
                self.play_pause_btn.config(text="Pause")
                self.after(0, lambda: self.update_now_playing(self.current_song))
            
            self.is_playing = not self.is_playing
        except Exception:
            pass  # Silently ignore or log optionally

    def pause_music(self):
        if self.sp and self.is_playing:
            try:
                self.sp.pause_playback()
                self.is_playing = False
            except:
                pass
        elif pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.is_playing = False

    def resume_music(self):
        if self.sp and not self.is_playing:
            try:
                self.sp.start_playback()
                self.is_playing = True
            except:
                pass
        elif not self.is_playing:
            pygame.mixer.music.unpause()
            self.is_playing = True


    def set_volume(self, volume):
        """Set the volume level"""
        self.volume_level = int(volume)
        if self.sp:
            def _set_vol():
                try:
                    self.sp.volume(self.volume_level)
                except Exception as e:
                    print(f"[ERROR] Volume set failed: {e}")

            threading.Thread(target=_set_vol, daemon=True).start()
    def play_song_for_uri(self, uri):
        def _play():
            try:
                # Get active device
                devices = self.sp.devices().get('devices', [])
                device = next((d for d in devices if d['is_active']), None)
            
                if not device:
                    # Try to transfer playback to this computer
                    devices = self.sp.devices().get('devices', [])
                    if devices:
                        self.sp.transfer_playback(devices[0]['id'], force_play=False)
                        time.sleep(2)  # Wait for transfer to complete
            
                # Start playback
                self.sp.start_playback(uris=[uri])
                self.current_song = uri
                self.is_playing = True
                self.after(0, lambda: self.update_now_playing(uri))
            
            except Exception as e:
                print(f"[SPOTIFY PLAYBACK ERROR] {e}")
                self.play_local_music(self.frozen_emotion)

        threading.Thread(target=_play, daemon=True).start()
    def play_local_music(self, emotion):
        try:
            local_file = self.local_music_files.get(emotion)
            if local_file and os.path.exists(local_file):
                pygame.mixer.music.stop()
                pygame.mixer.music.load(local_file)
                pygame.mixer.music.set_volume(self.volume_level / 100)
                pygame.mixer.music.play()
                self.is_playing = True
                self.current_song = None
                self.after(0, lambda: self.now_playing_label.config(
                    text=f"Playing local: {os.path.basename(local_file)}"
                ))
            else:
                self.after(0, lambda: messagebox.showwarning(
                    "File Not Found", 
                    f"No local music file found for emotion: {emotion}"
                ))
        except Exception as e:
            print(f"[LOCAL MUSIC ERROR] {e}")
            self.after(0, lambda: messagebox.showerror(
                "Playback Error", 
                f"Could not play local file for {emotion}"
            ))




    def show_help(self):
        """Show help information"""
        help_text = """Emotion-Based Music Player Help:

1. Face the camera and maintain an expression for 15 seconds to detect your emotion.
2. The app will suggest music based on your detected emotion.
3. Use the controls to:
   - Play/pause music
   - Change songs within the same emotion playlist
   - Adjust volume
4. Click 'Try Again' to restart emotion detection.
5. Press ESC to toggle fullscreen mode.
6. The app saves your emotion history when you quit.
"""
        messagebox.showinfo("Help", help_text)

    def return_to_detection(self):
        """Return to the detection interface"""
        if self.sp and self.is_playing:
            try:
                self.sp.pause_playback()
                self.is_playing = False
            except:
                pass
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            self.is_playing = False

        self.detection_active = True
        self.same_emotion_duration = 0
        self.last_emotion_change_time = time.time()
        self.create_detection_interface()

    def save_emotion_history(self):
        try:
            filename = f"emotion_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w') as f:
                for entry in self.emotion_history:
                    f.write(entry + '\n')
            print(f"[INFO] Emotion history saved to {filename}")
        except Exception as e:
            print(f"[ERROR] Failed to save emotion history: {e}")


    def quit_app(self):
        if messagebox.askokcancel("Quit", "Do you want to quit and stop music?"):
            try:
                if self.sp and self.is_playing:
                    self.sp.pause_playback()  # Stop music
                if self.cap:
                    self.cap.release()
                self.save_emotion_history()   
                self.destroy()
            except Exception as e:
                print(f"[EXIT ERROR] {e}")
                self.save_emotion_history()
                self.destroy()


if __name__ == "__main__":
    try:
        print("[INFO] Initializing App...")
        app = EmotionRecognitionApp()
        print("[INFO] App initialized. Starting mainloop...")
        app.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Fatal Error", f"The application encountered a fatal error:\n{e}")
