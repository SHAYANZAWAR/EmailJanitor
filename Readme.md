# EmailJanitor

**EmailJanitor** is a smart assistant that helps organize your [Gmail](https://mail.google.com/) inbox by automatically adding labels to emails based on their priority and required actions.

## Features

- Scans your Gmail inbox for new emails
- Assigns labels according to priority and action requirements
- Helps you keep your inbox organized and manageable

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/EmailJanitor.git
   cd EmailJanitor
   ```

2. **(Optional) Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   # or
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Google API credentials:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Create a new project and enable the Gmail API.
   - Download your `credentials.json` and place it in the project root directory.

5. **(Optional) Configure environment variables:**
   - Create a `.env` file if you need to store API keys or configuration.

## Usage

Run the main script to start organizing your inbox:

```bash
python email_agent.py
```

The assistant will authenticate with your Gmail account, scan your inbox, and apply labels to emails based on their content and urgency.

## Security

- **Do not share your `credentials.json`, `.env`, or `token.json` files.**
- These files are included in `.gitignore` to prevent accidental uploads.

## License

This project is licensed under the MIT License.

---

**EmailJanitor** – Keep your inbox clean