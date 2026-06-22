# 🚀 AI-Driven Gesture Control & Air-Canvas HCI Engine

An advanced Human-Computer Interaction (HCI) workstation engine built using MediaPipe and OpenCV. This system transforms a standard webcam feed into an interactive, multi-mode control deck—allowing seamless swapping between single-hand macro shortcuts, desktop window manipulation, dynamic scaling metrics, and an asymmetric dual-hand air-canvas drawing system.

---

## ✨ Key Features

### ☝️ Single-Hand Macro Suite
* **Brave Browser & YouTube Launch:** Swipe a single finger right or left to deploy targeted workspaces instantly.
* **Window Manipulation Engine:** Swipe two fingers right/left for `Alt + Tab` navigation, or swipe down to minimize. Hold steady to deploy Google Chrome.
* **App Launcher Deck:** Flash 3 or 4 fingers to instantly spin up tools like Notepad or Microsoft Edge.
* **Spatial Depth Scaling:** Push or pull an open palm toward the camera to clear your desktop (`Win + D`) or maximize windows (`Win + Up`).

### 👐 Dual-Hand Multi-Mode Workspaces
* **The Sci-Fi Stretcher:** Bring both hands up with your left hand open to dynamically track wrist-to-wrist spatial distance, resizing a holographic visual overlay HUD in real-time.
* **Asymmetric Mouse Selector:** Flash 2 fingers on your left hand to gain hardware control over your native Windows cursor using your right index finger.
* **Persistent Air-Canvas (Double-Two Mode):** Flash 2 fingers on *both* hands simultaneously to lock down a native left-click drag and paint glowing yellow digital ink directly over your video feed.
* **Swipe-to-Flush Eraser:** Drop your left hand out of the 2-finger posture and slice your right palm downward rapidly to wipe the entire air-canvas tracking memory instantly.

---

## 🛠️ Tech Stack & System Architecture

* **Core Language:** Python 3.x
* **Computer Vision Framework:** Google MediaPipe (Hand Landmarker API) for real-time 21-point 3D skeletal hand tracking.
* **Image Processing:** OpenCV (cv2) for video capture stream orchestration, localized frame mirroring, and dynamic HUD canvas layering.
* **OS Integration Core:** Windows API via `ctypes` (User32 interface) for low-level virtual key injects (`keybd_event`) and absolute mouse positioning coordinate scaling.
* **Concurrency:** Native Python `threading` to detach blocking system shell execution macros from the main camera pipeline, preserving high frame rates.

### 🔄 Multi-Tiered State Machine Logic
The engine implements a hierarchical prioritization layer to prevent race conditions between single-hand and dual-hand tracking:
1. **Frame Capture & Normalization:** Images are read, flipped horizontally for intuitive mirror interaction, and converted to RGB tensors.
2. **Dual-Hand Guard Isolation:** If MediaPipe identifies two hands, a structural verification frame-streak accumulator fires. Single-hand macro evaluation is explicitly frozen to avoid false-positive triggers (e.g., preventing an accidental `Alt+Tab` while raising both hands for Canvas Mode).
3. **Spatial Sorting:** Hands are dynamically grouped by their relative horizontal coordinates along the screen X-axis to cleanly distinguish between Left and Right hand profiles regardless of entrance order.
