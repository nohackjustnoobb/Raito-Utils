# Posts Extractor

Extract posts from facebook

## Quick Start

1. Copy the Script to the Facebook Console:

   - Open Facebook and navigate to the content you want to extract.
   - Open the browser's developer tools (press F12 or Ctrl+Shift+I).
   - Go to the "Console" tab.
   - Copy and paste the content of `extractorScript.js` into the console and press Enter.

2. Scroll Through the Content:

   - Scroll through the Facebook page to load all the posts you need to extract.

3. Copy Output to File:

   - Copy the value of outputString from the console.
   - Paste this value into a file named `input.txt`.

4. Run the Python Script:

   - Make sure Python is installed on your system.
   - Install the dependencies by running `pip install -r requirements.txt`.
   - Place `input.txt` in the same directory as the Python script.
   - Open a terminal or command prompt in that directory and run `python scraper.py`.

5. Config File (Optional):

   - A template config file is provided with the script to avoid entering configurations every time you run the script.
   - Customize the config file as needed and save it in the same directory as the Python script.
