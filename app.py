from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash, jsonify
import pandas as pd
import os
import shutil
import sqlite3
import time
import openai  # Added OpenAI import
from fuzzywuzzy import process  # Added for fuzzy matching

app = Flask(__name__)
app.secret_key = 'simple_key'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['STATIC_FOLDER'] = 'static/'
app.config['FIXED_FILE'] = os.path.join(app.config['STATIC_FOLDER'], 'fixed file with headers with no data.xlsx')
app.config['VARIABLE_FILE'] = os.path.join(app.config['STATIC_FOLDER'], 'variable file template.xlsx')
app.config['BOOK2_FILE'] = os.path.join(app.config['STATIC_FOLDER'], 'Book2.xlsx')

# Set OpenAI API Key
openai.api_key = "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"

# Ensure necessary folders exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['STATIC_FOLDER']):
    os.makedirs(app.config['STATIC_FOLDER'])

# Initialize SQLite database
def init_db():
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()

init_db()

def clear_files():
    time.sleep(1)
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        shutil.rmtree(app.config['UPLOAD_FOLDER'])
        os.makedirs(app.config['UPLOAD_FOLDER'])
    if os.path.exists(app.config['STATIC_FOLDER']):
        for filename in os.listdir(app.config['STATIC_FOLDER']):
            if filename.endswith('.xlsx') and filename not in [
                'fixed file with headers with no data.xlsx', 
                'variable file template.xlsx', 
                'Book2.xlsx']:
                os.remove(os.path.join(app.config['STATIC_FOLDER'], filename))

@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check credentials in the database
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
            user = c.fetchone()

        if user:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.")
    return render_template('login.html')

@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            with sqlite3.connect('users.db') as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
            flash("Account created successfully! Please log in.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already taken. Please choose another.")
    
    return render_template('sign_up.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('new_password')
        
        with sqlite3.connect('users.db') as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = c.fetchone()
            
            if user:
                c.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
                conn.commit()
                flash("Password updated successfully! Please log in.")
                return redirect(url_for('login'))
            else:
                flash("Username not found.")
    
    return render_template('forgot_password.html')

@app.route('/index')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    first_file_uploaded = os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], 'original_file.xlsx'))
    files_generated = os.path.exists(os.path.join(app.config['STATIC_FOLDER'], 'updated_Book2.xlsx'))
    return render_template('index.html', 
                           first_file_uploaded=first_file_uploaded, 
                           files_generated=files_generated)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if file and file.filename.endswith('.txt'):
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'original_file.txt')
            file.save(file_path)
            df = pd.read_csv(file_path, sep=';', header=None)
            df.fillna(0, inplace=True)
            df.replace('', 0, inplace=True)  
            excel_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'original_file.xlsx')
            df.to_excel(excel_file_path, index=False, header=False)
            return redirect(url_for('index', msg="Upload Successful! Now you can generate files!"))
        except Exception as e:
            return redirect(url_for('index', msg="Error processing file."))
    else:
        return redirect(url_for('index'))  # Trigger error message

@app.route('/generate_files', methods=['POST'])
def generate_files():
    original_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'original_file.xlsx')
    if not os.path.exists(original_file_path):
        return "Error: Original file does not exist.", 400
    try:
        master_data = pd.read_excel(original_file_path, header=None)
        emp_id_data = master_data.iloc[:, 4]
        variable_data = master_data.iloc[:, 33:74]
        variable_file_df = pd.DataFrame()
        variable_file_df['emp id'] = emp_id_data
        for i in range(0, variable_data.shape[1], 2):
            if i + 1 < variable_data.shape[1]:
                variable_file_df[f'Special Code {i+1}'] = variable_data.iloc[:, i]
                variable_file_df[f'Value {i+1}'] = variable_data.iloc[:, i + 1]
        updated_variable_file_path = os.path.join(app.config['STATIC_FOLDER'], 'variable_file_updated.xlsx')
        variable_file_df.to_excel(updated_variable_file_path, index=False)
        book2 = pd.read_excel(app.config['BOOK2_FILE'])
        if 'emp id' in book2.columns:
            book2['emp id'] = emp_id_data.values
        else:
            return "Error: 'emp id' column not found in Book2."
        for _, row in variable_file_df.iterrows():
            emp_id = row['emp id']
            for i in range(1, len(row), 2):
                special_number_code = row[i]
                value = row[i + 1]
                book2_row = book2[book2['emp id'] == emp_id]
                if not book2_row.empty and special_number_code in book2.columns:
                    book2.at[book2_row.index[0], special_number_code] = value
        book2.fillna(0, inplace=True)
        updated_book2_path = os.path.join(app.config['STATIC_FOLDER'], 'updated_Book2.xlsx')
        book2.to_excel(updated_book2_path, index=False)
        fixed_file_template = pd.read_excel(app.config['FIXED_FILE'])
        fixed_data = pd.concat([master_data.iloc[:, :33], master_data.iloc[:, 73:]], axis=1)
        if fixed_data.shape[1] > fixed_file_template.shape[1]:
            fixed_data = fixed_data.iloc[:, :fixed_file_template.shape[1]]
        elif fixed_data.shape[1] < fixed_file_template.shape[1]:
            for _ in range(fixed_file_template.shape[1] - fixed_data.shape[1]):
                fixed_data[f'Extra_Column_{_}'] = ''
        updated_fixed_data = pd.DataFrame(fixed_data.values, columns=fixed_file_template.columns)
        updated_fixed_file_path = os.path.join(app.config['STATIC_FOLDER'], 'fixed_file_updated.xlsx')
        updated_fixed_data.to_excel(updated_fixed_file_path, index=False)
        return redirect(url_for('index', msg="Files generated successfully!"))
    except Exception as e:
        return f"Error generating files: {str(e)}"

@app.route('/download_fixed')
def download_fixed_file():
    return send_from_directory(app.config['STATIC_FOLDER'], 'fixed_file_updated.xlsx', as_attachment=True)

@app.route('/download_original')
def download_original_file():
    return send_from_directory(app.config['UPLOAD_FOLDER'], 'original_file.xlsx', as_attachment=True)

@app.route('/download_book2')
def download_book2_file():
    return send_from_directory(app.config['STATIC_FOLDER'], 'updated_Book2.xlsx', as_attachment=True)

@app.route('/re_upload')
def re_upload():
    clear_files()
    return redirect(url_for('index'))

@app.route('/dox_ai', methods=['POST'])
def dox_ai():
    """
    Enhanced chatbot logic using fuzzy matching with fallback to OpenAI.
    """
    user_message = request.json.get('message')  # Get user's message from the frontend

    if not user_message:
        return jsonify({"response": "Please type a message."})

    # Predefined question-response pairs
    predefined_responses = [
    {"question": "How do I upload a file?", "response": "Click the upload button and select your `.txt` file."},
    {"question": "How do I generate files?", "response": "After uploading, click the 'Generate' button to process the data."},
    {"question": "What file formats are supported?", "response": "Only `.txt` files are supported."},
    {"question": "Can I upload multiple files?", "response": "No, only one file can be processed at a time."},
    {"question": "What should the delimiter be in the file?", "response": "Use `;` as the delimiter for proper processing."},
    {"question": "What is the size limit for files?", "response": "The file size must not exceed 5MB."},
    {"question": "How do I download the processed files?", "response": "Click on the download buttons after generation is complete."},
    {"question": "Can I log out of my account?", "response": "Yes, use the 'Logout' button on the interface."},
    {"question": "How can I reset my password?", "response": "Use the 'Forgot Password' option on the login page."},
    {"question": "Is my data stored on the server?", "response": "No, your data is processed and then cleared from the server."},
    {"question": "Can I delete my uploaded file?", "response": "Yes, use the 'ReUpload' button to clear the current file and upload a new one."},
    {"question": "What happens if I upload an unsupported file?", "response": "You will see an error message prompting you to upload a valid `.txt` file."},
    {"question": "Can I generate files without uploading a file?", "response": "No, you must upload a valid file before generating processed files."},
    {"question": "How do I know if my file is uploaded successfully?", "response": "A success message will appear after uploading your file."},
    {"question": "What are the steps to process my file?", "response": "Upload the file, click 'Generate,' and download the results."},
    {"question": "Can I preview the uploaded file?", "response": "Currently, previewing the uploaded file is not supported."},
    {"question": "What does the 'Generate' button do?", "response": "It processes the uploaded file and generates the output files."},
    {"question": "Are there any file naming conventions?", "response": "Use descriptive names and ensure the file has a `.txt` extension."},
    {"question": "What should I do if the file processing fails?", "response": "Ensure your file meets the requirements, then try again."},
    {"question": "Can I use this application on mobile devices?", "response": "Yes, the application is mobile-friendly."},
    {"question": "Is there a help section for troubleshooting?", "response": "You can ask Dox.ai for assistance with your queries."},
    {"question": "How do I contact support?", "response": "Currently, there is no dedicated support team. Use Dox.ai for assistance."},
    {"question": "Can I upload a file in another format?", "response": "No, only `.txt` files with a `;` delimiter are supported."},
    {"question": "How do I ensure my data is processed correctly?", "response": "Ensure your file format and delimiter match the requirements."},
    {"question": "What happens if my file contains errors?", "response": "Processing may fail; ensure your file is formatted correctly."},
    {"question": "Can I generate files multiple times?", "response": "Yes, you can generate files as long as a valid file is uploaded."},
    {"question": "What happens after I log out?", "response": "Your session will end, and you will need to log in again to access the application."},
    {"question": "Is my login information secure?", "response": "Yes, your credentials are securely stored in the database."},
    {"question": "Can I create multiple accounts?", "response": "Yes, but each account must have a unique username."},
    {"question": "How can I improve the processing speed?", "response": "Ensure your file is properly formatted and under the size limit."},
    {"question": "What types of files are generated?", "response": "Fixed, variable, and original data files in `.xlsx` format."},
    {"question": "Can I edit the generated files?", "response": "Yes, the files are in Excel format and can be edited."},
    {"question": "Is there a way to customize the output files?", "response": "Currently, customization of the output files is not supported."},
    {"question": "Can I process large datasets?", "response": "Processing speed may vary with file size; ensure your file is under 5MB."},
    {"question": "What does the error bubble indicate?", "response": "It highlights invalid file uploads or unsupported actions."},
    {"question": "Can I process files in other languages?", "response": "Yes, as long as the format and delimiter requirements are met."},
    {"question": "How often is my data cleared from the server?", "response": "Data is cleared after you click 'ReUpload' or log out."},
    {"question": "What browsers are supported?", "response": "The application works best on modern browsers like Chrome, Firefox, and Edge."},
    {"question": "How can I reset the application?", "response": "Use the 'ReUpload' button to reset the current session."},
    {"question": "What should I do if the application crashes?", "response": "Reload the page and ensure your file meets the requirements."},
    {"question": "Can I retrieve deleted files?", "response": "No, once deleted, files cannot be recovered."},
    {"question": "How do I navigate the interface?", "response": "Follow the instructions provided on the screen or ask Dox.ai for help."},
    {"question": "Can I provide feedback on the application?", "response": "Currently, there is no feedback mechanism. You can share your thoughts via chat."},
    {"question": "How is my password stored?", "response": "Passwords are securely stored in the database using encryption."},
    {"question": "What if I forget my username?", "response": "Contact the administrator, as username recovery is not automated."},
    {"question": "How do I know when the files are ready for download?", "response": "A message will appear, and download buttons will be enabled."},
    {"question": "What does the 'Logout' button do?", "response": "It ends your session and redirects you to the login page."},
    {"question": "Can I download all files at once?", "response": "No, files must be downloaded individually."},
    {"question": "What are the supported operating systems?", "response": "The application is accessible on any OS with a modern web browser."},
    {"question": "What if my file has confidential data?", "response": "Your data is processed locally on the server and cleared afterward."},
    {"question": "What is the purpose of the fixed file?", "response": "It organizes data into a fixed format for further use."},
    {"question": "What is the purpose of the variable file?", "response": "It provides dynamic data for additional processing or analysis."},
    {"question": "Can I upload a compressed file?", "response": "No, only plain `.txt` files are accepted."},
    {"question": "What if I encounter a bug?", "response": "Report the issue via chat, and it will be addressed in future updates."},
    {"question": "How is the AI integrated into the application?", "response": "Dox.ai uses GPT-3.5 to assist with user queries and troubleshooting."},
    {"question": "What is the source of the AI's knowledge?", "response": "The AI is powered by OpenAI's language model trained on diverse datasets."},
    {"question": "How can I clear the chat history?", "response": "Currently, clearing chat history is not supported."},
    {"question": "What does the 'ReUpload' button do?", "response": "It clears the current file and allows you to upload a new one."},
    {"question": "How do I know my file was processed correctly?", "response": "Check the output files for accuracy and completeness."},
    {"question": "Can I request new features?", "response": "Feature requests are not supported in the current version."},
    {"question": "What is the maximum number of rows supported?", "response": "The application can handle files under the 5MB size limit."},
    {"question": "Can I process files with missing values?", "response": "Yes, missing values will be handled automatically during processing."},
    {"question": "What if I upload a duplicate file?", "response": "The new file will overwrite the existing file."},
    {"question": "What are the restrictions on usernames?", "response": "Usernames must be unique and adhere to database constraints."},
    {"question": "Can I use special characters in my file?", "response": "Yes, as long as the file format and delimiter are correct."},
    {"question": "What is the purpose of the chat feature?", "response": "It allows users to interact with Dox.ai for assistance and guidance."},
    {"question": "Can I save my session progress?", "response": "No, session progress is not saved. Ensure you download your files before logging out."},
    {"question": "How do I know my data is secure?", "response": "Your data is processed on the server and cleared after processing."},
    {"question": "What if my file has extra columns?", "response": "Extra columns will be ignored unless required for processing."},
    {"question": "What happens if I log out accidentally?", "response": "You will need to log in again and re-upload your files."},
    {"question": "Can I use the application offline?", "response": "No, the application requires an active internet connection."},
    {"question": "What if the AI doesn't understand my query?", "response": "Rephrase your query for clarity or ask specific questions."},
    {"question": "How is file integrity maintained?", "response": "Uploaded files are processed as is, ensuring no data alteration."},
    {"question": "Can I view a demo of the application?", "response": "Currently, there is no demo mode available."},
    {"question": "What if my file uses a different delimiter?", "response": "Only `;` as a delimiter is supported. Adjust your file accordingly."},
    {"question": "Can I upload multiple files at once?", "response": "No, only one file can be uploaded at a time."},
    {"question": "What is the purpose of the original file?", "response": "The original file is saved for reference and comparison."},
    {"question": "Can I use special characters in my password?", "response": "Yes, special characters are supported in passwords."},
    {"question": "What does the progress bar indicate?", "response": "Currently, there is no progress bar. Wait for the success message."},
    {"question": "Can I process encrypted files?", "response": "No, encrypted files are not supported."},
    {"question": "What if my internet connection is lost?", "response": "Reestablish the connection and try again."},
    {"question": "How can I access help for advanced features?", "response": "Ask Dox.ai for specific guidance or queries."},
    {"question": "Can I share the application with others?", "response": "Yes, but ensure they create their own accounts for access."},
    {"question": "What does the 'Fixed Data' file contain?", "response": "It contains structured data based on a fixed template."},
    {"question": "What does the 'Variable Data' file contain?", "response": "It includes dynamic data for further analysis or use."},
    {"question": "Can I customize the application?", "response": "Customization is not supported in the current version."},
    {"question": "What happens if I click 'Generate' twice?", "response": "The same output files will be generated again."},
    {"question": "Can I undo changes in the generated files?", "response": "No, you need to manually adjust the files if needed."},
    {"question": "What happens if my file is too large?", "response": "Processing may fail or take longer than expected. Ensure your file is within size limits."},
    {"question": "Is there a tutorial for new users?", "response": "Currently, there is no tutorial, but you can use Dox.ai for guidance."},
    {"question": "Can I use emojis in my file?", "response": "Emojis are not recommended and may cause processing issues."},
    {"question": "How is the output file format determined?", "response": "Output files are generated in `.xlsx` format based on predefined templates."},
    {"question": "Can I process files with headers?", "response": "Yes, but headers will be handled as regular data entries."},
    {"question": "What if I need to process multiple datasets?", "response": "You will need to process each file separately."},
    {"question": "Can I use this application for business purposes?", "response": "Yes, but ensure compliance with your organization's policies."},
    {"question": "How do I know if my file is processed correctly?", "response": "Check the generated files for accuracy and completeness."},
    {"question": "Can I collaborate with others using this application?", "response": "No, collaboration features are not supported."},
    {"question": "What if my file contains sensitive information?", "response": "Ensure you trust the server as your data will be temporarily processed."},
    {"question": "Can I use this application for free?", "response": "Yes, the application is free to use."},
    {"question": "Is there a premium version of the application?", "response": "Currently, there is no premium version available."},
    {"question": "What are the supported file encodings?", "response": "UTF-8 encoding is recommended for best results."},
    {"question": "Can I generate charts or graphs?", "response": "No, chart or graph generation is not supported."},
    {"question": "What if my file contains duplicate rows?", "response": "Duplicate rows will be processed as is."},
    {"question": "Can I provide feedback about Dox.ai?", "response": "You can use the chat feature to share your feedback."},
    {"question": "How do I clear all data from the application?", "response": "Use the 'ReUpload' button to clear the current session."},
    {"question": "What happens if I upload a corrupted file?", "response": "Processing will fail, and you will see an error message."},
    {"question": "Can I schedule file processing tasks?", "response": "No, task scheduling is not supported in the current version."},
    {"question": "Is there a limit on the number of files I can upload?", "response": "You can upload one file per session."},
    {"question": "What if my file has mixed delimiters?", "response": "Ensure your file uses only the `;` delimiter for proper processing."},
    {"question": "How is the chat history saved?", "response": "Chat history is not saved and will be cleared upon refresh or logout."},
    {"question": "What happens if I type an unsupported query?", "response": "Dox.ai will provide a generic response or ask for clarification."},
    {"question": "Can I download a user manual?", "response": "Currently, there is no downloadable user manual available."},
    {"question": "What are the future updates planned?", "response": "Future updates may include advanced features based on user feedback."},
    {"question": "How can I contribute to the project?", "response": "Currently, external contributions are not accepted."},
    {"question": "hi", "response": "Hi there! How can I assist you today?"},
    {"question": "hello", "response": "Hello! How can I help you?"},
    {"question": "hey", "response": "Hey! How's it going? How can I assist you?"},
    {"question": "how are you", "response": "I'm just a helpful bot, but thanks for asking! How can I assist you today?"},
    {"question": "thank you", "response": "You're welcome! Let me know if there's anything else I can help with."},
    {"question": "bye", "response": "Goodbye! Thanks for using the application. Have a great day!"},
    {"question": "thanks", "response": "Thanks to you too! Feel free to reach out if you need more help."}
]

    # Extract questions from predefined responses
    questions = [item["question"] for item in predefined_responses]

    # Find the best match for the user's input
    match, confidence = process.extractOne(user_message, questions)

    # If confidence is above a certain threshold, return the matched response
    if confidence > 75:  # Adjust threshold as needed
        for item in predefined_responses:
            if item["question"] == match:
                return jsonify({"response": item["response"]})

    # Fallback to OpenAI API if no good match is found
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use GPT-3.5-turbo model
            messages=[
                {"role": "system", "content": "You are Dox.ai, an assistant to help users with file processing tasks."},
                {"role": "user", "content": user_message}
            ]
        )

        ai_reply = response['choices'][0]['message']['content']  # Extract AI's reply
        return jsonify({"response": ai_reply})

    except Exception as e:
        print(f"Error with OpenAI API: {e}")
        return jsonify({"response": "Sorry, I am currently unable to process your request. Please try again later."})

if __name__ == '__main__':
    app.run(debug=True)
