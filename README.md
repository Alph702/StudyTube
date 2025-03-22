# StudyTube 📚🎥

StudyTube is a minimalist web application that allows users to search and watch educational videos directly from YouTube. It features a sleek, responsive design and a seamless video player experience. The app is built using Flask (Python) as the backend and serves dynamic content with Jinja2 templating.

## Features 🌟

- 🔎 Search for educational videos using keywords.
- 🎬 Play videos directly within the app.
- ⏳ Skeleton loading effect while videos are fetched.
- 🚀 Minimalist and responsive design for a clean user experience.

## Tech Stack 🛠️

- **Backend:** Flask (Python)
- **Frontend:** HTML, CSS, Jinja2 Templates
- **API Integration:** YouTube Data API v3

## Installation 💻

1. Clone the repository:

   ```bash
   git clone https://github.com/Alph702/StudyTube.git
   cd StudyTube
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up API Keys:

   - Obtain your YouTube Data API v3 key from the Google Developer Console.
   - Create a `env.py` file and add your API keys:
     ```python
     YOUTUBE_API_KEYS = [
        'YOUR_API_KEY_1',
        'YOUR_API_KEY_2',
        # Add more API keys as needed
      ]
     ```

4. Run the application:

   ```bash
   flask run
   ```

5. Open your browser and visit:

   ```
   http://127.0.0.1:5000
   ```

## File Structure 🗃️
- `templates/` - HTML templates (index, player, loading)
- `static/` - CSS file
- `app.py` - Main Flask application
- `env.py` - Environment variables
- `requirements.txt` - Dependencies list

## Contributing 🤝
Contributions are welcome! Feel free to submit issues or pull requests to enhance the project.

## License 📄
This project is licensed under the MIT License.

## Acknowledgements 🙏
Special thanks to the developers of Flask and the YouTube Data API for making this project possible!

