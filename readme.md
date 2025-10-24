# DuoDetect AI

**Real-time AI-Powered Duplicate Detection using DeepFace**

> A Flask + MongoDB + DeepFace web app that prevents duplicate applications using **face recognition**  
> **One submission per email | Real-time AI analysis | Top 5 match audit trail**

---

## Features

| Feature | Description |
|-------|-----------|
| **Real Face Matching** | Uses **DeepFace (ArcFace + Cosine)** to compare faces |
| **Self-Exclusion** | Current photo is **excluded** from gallery during matching |
| **Top 5 Matches** | Stores & shows **top 5 closest matches** with photo, ID, confidence |
| **One Submission per Email** | Prevents spam & duplicates |
| **AJAX Form + Loader** | Smooth UX, no infinite loading |
| **Email Confirmation** | Sends AI result via Gmail (App Password) |
| **Live Dashboard** | Real-time stats: Total, Duplicates, Unique, Pending |
| **MongoDB Storage** | Full audit trail of submissions + AI results |
| **Admin Reset** | `/admin/clear` to wipe all data |
| **Responsive UI** | Bootstrap 5 + Font Awesome |

---

## Tech Stack

```text
Frontend:  HTML, Bootstrap 5, JavaScript (AJAX)
Backend:   Flask (Python)
AI Engine: DeepFace (ArcFace)
Database:  MongoDB
Email:     Flask-Mail + Gmail SMTP
Storage:   Local `/uploads` folder
```

---

## Project Structure

```bash
DuoDetect/
├── app.py                  # Main Flask app
├── .env                    # Environment variables
├── requirements.txt
├── uploads/                # Uploaded photos (auto-created)
├── templates/
│   ├── index.html
│   ├── instructions.html
│   ├── apply.html
│   ├── results.html
│   ├── privacy.html
├── static/
│   └── styles.css
└── README.md
```

---

## How to Run (Step-by-Step)

### 1. Clone & Enter Directory

```bash
git clone https://github.com/Sensekriti/DuoDetect.git
cd DuoDetect
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate    # Linux/Mac
venv\Scripts\activate       # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> `requirements.txt`:
```txt
Flask==2.3.3
Flask-WTF==1.2.1
Flask-Mail==0.9.1
pymongo==4.8.0
Pillow==10.3.0
python-dotenv==1.0.1
deepface==0.0.89
opencv-python-headless==4.9.0.80
tf-keras==2.15.0
```

### 4. Set Up `.env`

```env
MAIL_USERNAME=yourgmail@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=yourgmail@gmail.com
```

> Get App Password: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

### 5. Start MongoDB

```bash
# Ubuntu/Debian
sudo systemctl start mongod

# macOS (with Homebrew)
brew services start mongodb-community

# Windows: Start MongoDB service
```

### 6. Run the App

```bash
python app.py
```

Visit: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## How to Use

1. **Go to `/apply`**
2. Fill form → Upload **clear passport photo**
3. Click **Submit**
4. Wait 2–5 sec → AI analyzes face
5. Success → Redirect to form or dashboard
6. Check **`/Dashboard`** → See AI result + top matches

---

## Architecture Diagram

```mermaid
flowchart TD
    A[User Browser] -->|Submit Form| B(Flask Server)
    B --> C[Validate Form + Save Photo]
    C --> D[DeepFace.find()]
    D -->|Exclude Self| E[Gallery: All Other Photos]
    E --> F[Top 5 Matches + Confidence]
    F --> G[Save to MongoDB]
    G --> H[Send Email via Gmail]
    H --> I[Redirect + Show Result]
    B --> J[/Dashboard → MongoDB Query]
    J --> K[Render Results Table]
```

---

## Screenshots (Text Preview)

### 1. Apply Form
```
[IndiaAI Logo]
Full Name: ________________
Email:     ________________
[Upload Photo] [Submit Button] → [AI Analyzing...]
```

### 2. Dashboard
```
Total: 12 | Duplicates: 3 | Unique: 9 | Pending: 0

#1  APP20251024_ABC123  Rahul
    [Duplicate Badge]  Best: 98.4%
    ▼ Top 5 Matches
        [Photo] APP20251024_XYZ987  98.4%
        [Photo] APP20251024_PQR112  72.0%
    [Progress Bar: 98.4% red]
    Match: XYZ987 | Time: 3.2s
    [Candidate Photo]
```

---

## AI Logic Explained

| Step | Action |
|------|-------|
| 1 | User uploads photo → saved as `APPxxx_timestamp.jpg` |
| 2 | DeepFace compares it with **all other photos** (self-excluded) |
| 3 | Returns **top 5 closest faces** |
| 4 | If **best match < threshold (0.40)** → **Duplicate** |
| 5 | Save result + top 5 in MongoDB |
| 6 | Show in dashboard with **photos & confidence** |

---

## Admin Features

| Route | Action |
|------|-------|
| `/admin/clear` | Delete all submissions (for demo) |
| `/uploads/` | View raw photos |

---

## Future Roadmap

| Feature | Status |
|-------|--------|
| Face cropping & alignment | Planned |
| Manual verification queue | Planned |
| Export results to CSV | Planned |
| Admin login panel | Planned |
| WebSocket live updates | Planned |
| Confidence threshold tuning | Planned |
| Batch upload | Planned |

---

## Troubleshooting

| Issue | Fix |
|------|-----|
| `DeepFace` slow | Use `Facenet` instead of `ArcFace` |
| Email not sent | Check App Password & `Less secure apps` |
| MongoDB not connecting | Run `mongod` service |
| Loader stuck | Check browser console (F12) |
| Self-match appears | Ensure `exclude_filename` is passed |

---

## Contributors

- **You** – Lead Developer
- **Your Senior** – Provided `compare_one_to_all.py` script

---

## License

```
MIT License – Free to use, modify, and distribute
```

---

## Support

For issues, open a GitHub issue or contact:  
`your.email@example.com`

---

**Made with love for IndiaAI Challenge**

---

**Star this repo if you liked it!**

---

**Just copy-paste this into `README.md` in your project root.**  
It’s ready for **GitHub, internal docs, or demo presentation**.

Let me know if you want:
- PDF version
- Demo video script
- Docker setup
- Deploy to Render/Heroku

You're now **presentation-ready**!