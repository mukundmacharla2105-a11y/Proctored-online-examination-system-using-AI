# Proctored-online-examination-system-using-AI
Below is a **clean, professional, submission-ready README.md** tailored exactly to **your project**, tech stack, and what evaluators expect.
You can **copy–paste this directly** into a file named `README.md` in your project root.

---

# 🧠 AI-Based Proctored Online Examination System

An **AI-powered online examination proctoring system** built using **Python, Flask, OpenCV, HTML, CSS, and APIs**.
The system monitors candidates during online exams by **detecting multiple faces**, identifying suspicious behavior, and helping prevent **malpractice** in real time.

---

## 📌 Problem Statement

Online examinations are vulnerable to cheating due to the lack of physical supervision.
This project addresses that challenge by using **computer vision and AI techniques** to automatically monitor examinees and flag suspicious activities.

---

## 🚀 Features

* 👁️ **Real-time face detection using OpenCV**
* 👥 **Multiple face detection** (flags presence of more than one person)
* 🚨 **Suspicious activity monitoring during exams**
* 📷 Live webcam monitoring
* 🧑‍💻 Admin & candidate workflow
* 🌐 Web-based interface using Flask
* 📊 Dataset-driven exam management
* 🔐 Secure and automated proctoring

---

## 🛠️ Tech Stack

### Backend

* Python 3.x
* Flask
* OpenCV
* REST APIs

### Frontend

* HTML5
* CSS3
* JavaScript

### AI / CV

* Haar Cascade / OpenCV DNN (Face Detection)
* Real-time video processing

---

## 📂 Project Structure

```text
Proctored-online-examination-system-using-AI/
│
├── backend/
│   ├── datasets/           # Exam question datasets
│   ├── static/             # CSS, JS, images
│   ├── templates/          # HTML files
│   ├── admin.py
│   ├── app.py              # Main Flask app
│   ├── proctor.py          # AI proctoring logic
│   └── models.py
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

## ⚙️ Installation & Setup

### 1️⃣ Prerequisites

Make sure you have:

* Python **3.8 or above**
* Webcam (mandatory)
* Git installed

---

### 2️⃣ Clone the Repository

```bash
git clone https://github.com/mukundmacharla2105-a11y/Proctored-online-examination-system-using-AI.git
cd Proctored-online-examination-system-using-AI
```

---

### 3️⃣ Create Virtual Environment (Recommended)

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

---

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is missing, install manually:

```bash
pip install flask opencv-python numpy
```

---

## ▶️ How to Run the Project

### Step 1: Navigate to backend

```bash
cd backend
```

### Step 2: Run the Flask application

```bash
python app.py
```

or

```bash
flask run
```

---

### Step 3: Open in Browser

Open your browser and go to:

```text
http://127.0.0.1:5000/
```

---

## 🎥 How Proctoring Works

1. Candidate logs in and starts the exam
2. Webcam activates automatically
3. OpenCV continuously detects faces
4. ⚠️ If **more than one face** is detected → flagged as suspicious
5. Proctoring logs activity during the entire exam session

---

## 📊 Use Cases

* Online college/university exams
* Certification platforms
* Remote hiring assessments
* Secure skill evaluation systems

---

## 🔒 Limitations

* Requires good lighting conditions
* Performance depends on webcam quality
* No cloud deployment (local execution)

---

## 🌱 Future Enhancements

* Eye gaze tracking
* Head pose estimation
* Audio-based cheating detection
* Cloud deployment
* ML-based behavior analysis
* Face recognition for identity verification

---

## 👨‍🎓 Academic Relevance

This project is suitable for:

* Final year projects
* AI / ML mini projects
* Computer Vision coursework
* Internship & placement portfolios

---

## 📜 License

This project is for **educational purposes only**.
Feel free to modify and extend it.

---

## 🤝 Author

**Mukund Macharla**
AI-Based Proctored Online Examination System
Built using Python, Flask, OpenCV, and Web Technologies

---
