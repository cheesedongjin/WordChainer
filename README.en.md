# WordChainer

## Introduction
WordChainer is a project that lets you enjoy the Korean word-chain game with an AI bot. It provides both a Tkinter-based desktop app and a web version distributed through GitHub Pages, so you can start playing easily from anywhere. [Play on the web](https://cheesedongjin.github.io/WordChainer/)

## Key Features
- **Multiple difficulty levels**: Adjust the bot's difficulty from level 1 to 5 to match your skill.
- **Real-time timer**: Each turn shows the remaining time with an intuitive gauge for a thrilling experience.
- **Word information lookup**: Click a word in the chat window to instantly see its pronunciation, definition, and usage examples from the dictionary.
- **Match history**: Game results are automatically saved by difficulty, allowing you to track your progress over time.
- **Suggested words**: If you lose because of a rule violation, the system message suggests example words you could have used.
- **Initial-sound rule support**: The game considers both the last character and its initial-sound conversions for a natural Korean word-chain experience.

## User Guide

### 1. Play on the Web
1. Visit [https://cheesedongjin.github.io/WordChainer/](https://cheesedongjin.github.io/WordChainer/) in your web browser.
2. Click the "Start Game" button in the left panel to begin playing against the bot.
3. Adjust the difficulty with the "Bot Difficulty" slider and enter words in the input field to alternate turns with the bot.
4. Check the meaning and usage of selected words in the "Word Info" section on the right panel to expand your vocabulary.

### 2. Run the Desktop App
1. Make sure Python 3.10 or later is installed.
2. After downloading the project, install the required dependencies with the following command.
   ```bash
   pip install -r requirements.txt
   ```
   > If no extra packages are listed in `requirements.txt`, the app runs with only the Python standard library.
3. Launch the Tkinter GUI app.
   ```bash
   python main.py
   ```
4. Once the app starts, click "Start Game" to begin playing, then type words into the input field or press Enter to submit them.
5. Game results are automatically stored in the `game_stats.json` file. Delete this file if you want to reset your record.

## Developer Guide

### Project Structure
```
WordChainer/
├── index.html          # Web app for GitHub Pages
├── main.py             # Tkinter-based desktop app
├── words.json          # Word database for the game
├── dev/
│   └── extract_words_to_json.py  # Script that generates words.json from raw data
├── requirements.txt    # Required Python packages
└── README.md
```

### Set Up a Local Development Environment
1. A virtual environment is recommended.
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. To modify the Tkinter UI, run `main.py` directly to verify your changes immediately.
3. To work on the web client, open `index.html` through a local server.
   ```bash
   python -m http.server 8000
   ```
   Then visit `http://localhost:8000/index.html` in your browser.

### Update the Word Data
- The `dev/extract_words_to_json.py` script extracts noun data from multiple Excel (`.xls`) files and generates `words.json`.
- Place the source data in the `dev/input_xls/` directory before running the script, and create the `dev/output/` folder if it does not exist.
  ```bash
  cd dev
  python extract_words_to_json.py
  ```
- The script calculates the "connection count" considering initial-sound rules to estimate word difficulty and uses it in the recommendation logic during gameplay.

### Deployment
- The web version is provided by deploying `index.html` on GitHub Pages. Because it consists only of static assets, no separate build step is required.
- The desktop version can be distributed with the `main.py` and `words.json` files. You can package it with PyInstaller if needed.

## License
This project is licensed under the [MIT License](LICENSE). Feel free to modify and distribute it in compliance with the license terms.
