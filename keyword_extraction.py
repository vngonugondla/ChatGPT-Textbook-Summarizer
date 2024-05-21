import os
import sys
import nltk
from nltk.corpus import words
from nltk.tokenize import word_tokenize, sent_tokenize
from transformers import AutoTokenizer, T5ForConditionalGeneration, MT5ForConditionalGeneration
import mysql.connector

nltk.download('punkt')
nltk.download("words")

class KeywordExtractor:
    def __init__(self, model_type: str = "t5", model_name: str = "snrspeaks/KeyPhraseTransformer"):
        self.model_name = model_name
        if model_type == "t5":
            self.model = T5ForConditionalGeneration.from_pretrained(self.model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        if model_type == "mt5":
            self.model = MT5ForConditionalGeneration.from_pretrained(self.model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

    def split_text(self, document: str, max: int = 128):
        sentences = sent_tokenize(document.strip())
        temp = ""
        temp_list = []
        final = []

        for i, sentence in enumerate(sentences):
            sent = sentence
            temp = temp + " " + sent
            word_count = len(self.tokenizer.tokenize(temp))

            if word_count < max:
                temp_list.append(sentence)

                if i == len(sentences) - 1:
                    final.append(" ".join(temp_list))
            else:
                final.append(" ".join(temp_list))
                temp = sentence
                temp_list = [sentence]

                if i == len(sentences) - 1:
                    final.append(" ".join(temp_list))

        return [section for section in final if len(section.strip()) != 0]

    def process(self, outputs):
        temp = [output[0].split(" | ") for output in outputs]
        flatten = [item for sublist in temp for item in sublist]
        return sorted(set(flatten), key=flatten.index)

    def filter(self, keywords, text):
        keywords = [phrase.lower() for phrase in keywords]
        text = text.lower()
        valid_keywords = []
        invalid_keywords = []

        for phrases in keywords:
            for phrase in word_tokenize(phrases):
                if (phrase in word_tokenize(text)) or (phrase in words.words()):
                    if phrases not in valid_keywords:
                        valid_keywords.append(phrases)
                else:
                    invalid_keywords.append(phrases)

        return [phrase for phrase in valid_keywords if phrase not in invalid_keywords]

    def extract(self, document: str):
        input_ids = self.tokenizer.encode(
            document, return_tensors="pt", add_special_tokens=True
        )
        generated_ids = self.model.generate(
            input_ids=input_ids,
            num_beams=2,
            max_length=512,
            repetition_penalty=2.5,
            length_penalty=1,
            early_stopping=True,
            top_p=0.95,
            top_k=50,
            num_return_sequences=1,
        )
        res = [
            self.tokenizer.decode(
                g, skip_special_tokens=True, clean_up_tokenization_spaces=True
            )
            for g in generated_ids
        ]
        return res

    def get_keywords(self, text: str, section_length: int = 64):
        res = []
        sections = self.split_text(
            document=text, max = section_length
        )

        for section in sections:
            res.append(self.extract(section))

        keywords = self.filter(self.process(res), text)
        return keywords

def generate_keywords(text):
    keyword_extractor = KeywordExtractor()
    words = 100
    keywords_per_100 = 2
    keywords = []

    sentences = sent_tokenize(text)
    paragraph = ""
    paragraph_count = 0

    for sentence in sentences:
        if paragraph_count + len(sentence.split()) <= words:
            paragraph += " " + sentence
            paragraph_count += len(sentence.split())
        else:
            paragraph_keywords = keyword_extractor.get_keywords(paragraph)
            keywords.extend(paragraph_keywords[:keywords_per_100])
            paragraph = sentence
            paragraph_count = len(sentence.split())

    paragraph_keywords = keyword_extractor.get_keywords(paragraph)
    keywords.extend(paragraph_keywords[:keywords_per_100])

    return keywords

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password= os.getenv("SQLPASSWORD"),
    database="vip"
)

cursor = mydb.cursor()

select_query = "SELECT * FROM keywords;"
insert_query = "INSERT INTO keywords VALUES (%s, %s, %s, %s);"

cursor.execute(select_query)
rows = cursor.fetchall()

for (id, chapter_name) in enumerate(rows):
    keywords = chapter_name[0]
    text = chapter_name[2]
    print()
    print("Text:", text)
    print()
    keywords = generate_keywords(text)
    print("Generated Keywords:", keywords)
    val = (str(keywords), str(chapter_name[1]), str(chapter_name[2]), str(id + 5))
    print(val)
    print()

    cursor.execute(insert_query, val)
    mydb.commit()

    print("Database updated with new keywords.")

delete_query = "DELETE FROM keywords WHERE (id = 2 or id = 3 or id = 4);"
cursor.execute(delete_query)
mydb.commit()

cursor.close()
mydb.close()