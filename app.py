from flask import Flask
from flask import request
import openai
import os
import mysql.connector


app = Flask(__name__)

# endpoint that helps input the text from the frontend/database
@app.route("/")
def index():
    txt = request.args.get('txt', default = 'No text inputted')
    return txt

@app.route("/test")
def test():
    return "Tested B)"

def split_text(text_to_split):
    max_chunk_size = 2048
    chunks = []
    current_chunk = ""
    for sentence in text_to_split.split("."):
        if len(current_chunk) + len(sentence) < max_chunk_size:
            current_chunk += sentence + "."
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + "."
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def generate_summary(text_to_summarize, keywords):
    input_chunks = split_text(text_to_summarize)
    output_chunks = []
    for chunk in input_chunks:
        response_summ = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"Summarize this content in 1-2 sentences using {keywords} as keywords"
                },
                {
                    "role": "user",
                    "content": chunk
                }
            ],
            temperature=0,
            max_tokens=100,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        summary = response_summ.choices[0]['message']['content']
        output_chunks.append(summary)
    return " ".join(output_chunks)

openai.api_key = "API_KEY_HERE"

mydb = mysql.connector.connect(
    host = "localhost",
    user = "root",
    password = os.getenv("SQLPASSWORD"),
    database = "vip"
)

cursor = mydb.cursor()

query = "select * from keywords;"

cursor.execute(query)

for (chapter_name) in cursor:
    keywords = chapter_name[0]
    text = chapter_name[2]
    print()
    print("Text:", text)
    print()
    print("Keywords extracted:", keywords)
    print()
    print("Summary using the keywords:", generate_summary(text, keywords))
    print()
    print("------------------")

cursor.close()
