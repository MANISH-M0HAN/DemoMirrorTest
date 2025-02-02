import csv
import requests
import os
from dotenv import load_dotenv
import requests

load_dotenv()

url = os.getenv("CHATBOT_URL")
api_key = os.getenv("API_KEY")

headers = {
    "X-API-KEY": api_key,
    "Content-Type": "application/json"
}

data = [
    ["Concept", "Input", "Expected Output"],
    ["Single trigger", "what is angina?", "Angina is chest pain caused by reduced blood flow to the heart."],
    ["Single trigger", "what is angina? and why is it caused", "Angina is chest pain caused by reduced blood flow to the heart. It signals an increased risk of heart attack."],
    ["Only trigger word", "angina", "Angina is chest pain caused by reduced blood flow to the heart.\n For personalized advice or concerns about your health, Please consult our healthcare professional. We can provide you with the best guidance based on your specific needs."],
    ["Domain relevance", "what is cardiac", "Cardiovascular refers to the heart and blood vessels. \n\n Myocardial infarction is a heart attack. \n\n Tachycardia is a rapid heartbeat."],
    ["Domain relevance", "what is football", "I'm sorry, I can only answer questions related to women's heart health. Can you please clarify your question?"],
    ["Fallback", "what health", "This is a placeholder response generated for your question."],
    ["multiple triggers", "what is cholesterol and what is angina", "Cholesterol is a type of fat found in your blood. \n\n Angina is chest pain caused by reduced blood flow to the heart."],
    ["multiple triggers and multiple intent", "what is cholesterol and how is angina caused", "Cholesterol is a type of fat found in your blood. Eat a low-fat diet, exercise regularly, and take prescribed medications. \n\n Angina is chest pain caused by reduced blood flow to the heart. Manage stress, avoid heavy meals, and follow a healthy lifestyle."],
    ["only intent", "how", "I'm sorry, I can only answer questions related to women's heart health. Can you please clarify your question?"],
    ["Spell check", "wat is angina", "Angina is chest pain caused by reduced blood flow to the heart.\n For personalized advice or concerns about your health, Please consult our healthcare professional. We can provide you with the best guidance based on your specific needs."],
    ["Greetings", "hi", "I'm sorry, I can only answer questions related to women's heart health. Can you please clarify your question?"],
    ["Edge Case", "cardiovascular", "Cardiovascular refers to the heart and blood vessels.\n For personalized advice or concerns about your health, Please consult our healthcare professional. We can provide you with the best guidance based on your specific needs."],
    ["Edge Case", "cardiovascular?", "Cardiovascular refers to the heart and blood vessels.\n For personalized advice or concerns about your health, Please consult our healthcare professional. We can provide you with the best guidance based on your specific needs."]
]

def create_csv(csv_file):
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(data)

def get_bot_response(user_input):
    payload = {"user_input": user_input}
    response = requests.post(url, headers=headers, json=payload)
    return response.json().get("response", "")

def test_chatbot_responses(csv_file):
    with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
    
    for row in rows:
        user_input = row["Input"]
        expected_output = row["Expected Output"]
        bot_response = get_bot_response(user_input)
        
        print(f"Testing input: {user_input}")
        print(f"Expected Output: {expected_output}")
        print(f"Bot Response: {bot_response}")
        
        result = "PASS" if bot_response.strip() == expected_output.strip() else "FAIL"
        print("Test Passed: ", result)
        print("-" * 50)
        
        row["Result"] = result

    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        fieldnames = ["Concept", "Input", "Expected Output", "Result"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

csv_file = "test.csv"
create_csv(csv_file)

test_chatbot_responses(csv_file)
