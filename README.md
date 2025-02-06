Excel File Processor with Python Flask

This project processes Excel files, allowing the user to upload an original/master file and either generate fixed data or update Book 2. The frontend is built using HTML and CSS, while the backend is a Python Flask application. Additional functionality includes raw text file conversion to Excel.

Project Structure
ITI/
│
├── build/                         # Empty directory (can be used for future builds)
│
├── static/                        # Static files (CSS, images, and Excel templates)
│   ├── a.jpg.png                  # Background or other image used in the project
│   ├── Book2.xlsx                 # Template file for Book 2
│   ├── download (2).png           # Download icon or image used in the UI
│   ├── fixed file with headers.xlsx# Template for the fixed file with headers
│   ├── styles.css                 # CSS file for styling the HTML pages
│
├── templates/                     # HTML templates
│   ├── index.html                 # Main page for file upload and button display
│
├── uploads/                       # Directory for storing uploaded files (generated at runtime)
│
├── app.py                         # Main Python Flask application that handles file processing and logic
│
└── README.md                      # Project documentation (this file)


Features
File Uploads: Users can upload an original/master Excel file and either generate fixed data or update Book 2.
Fixed Data Generation: Processes data based on the uploaded Excel file and generates a fixed file using the provided template.
Book2 Update: Matches and updates data in Book 2 based on the uploaded master file and additional variables.
Raw Text File Conversion: Converts raw text files (properties delimited and semicolon-separated) into Excel files.

Requirements
Python 3.x
Flask: A micro web framework for Python.
OpenPyXL: A Python library to read/write Excel 2010 xlsx/xlsm/xltx/xltm files.
Pandas: A data manipulation library in Python.
Flask-Uploads: A Flask extension for file uploading.


Install the necessary dependencies by running the following command:
pip install flask openpyxl pandas flask-uploads

Setup Instructions
1.Clone the repository:
git clone <repository_url>
cd ITI
2.Install dependencies: Make sure you have all the required libraries installed by running:
pip install -r requirements.txt
3.Run the Flask app: Start the development server by running:
python app.py
4.Access the application: Open a browser and go to http://127.0.0.1:5000 to access the web interface.

How to Use
Upload a file: Use the form on the main page (index.html) to upload an Excel or raw text file.
Select action: After uploading, you can choose between:
Generate File: This will generate fixed data based on the uploaded Excel file.
Convert File: If you upload a raw text file, this button will convert it to Excel.
Download processed files: After processing, the resulting file will be available for download.

File Descriptions
app.py: The main application file that handles routing, file uploads, and data processing.
index.html: The HTML file that provides the frontend for uploading files and choosing actions.
styles.css: Contains the CSS for styling the webpage.
Book2.xlsx: The Excel template for the Book 2 file, which is updated based on the uploaded data.
fixed file with headers.xlsx: A template file for generating fixed data after processing.
a.jpg.png, download (2).png: Images used in the web application.

Future Enhancements
Database Integration: Storing processed data in a database like MongoDB.
User Authentication: Adding login and user-specific processing capabilities.

