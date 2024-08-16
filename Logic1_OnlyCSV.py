import os
import pandas as pd
import logging
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from spellchecker import SpellChecker
from dotenv import load_dotenv

# Set the TOKENIZERS_PARALLELISM environment variable to avoid deadlock warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'rand'  # Use a secure method to handle secret keys
CORS(app)

# Initialize models and spellchecker
embedding_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
spellchecker = SpellChecker()

# Load the CSV file into a DataFrame
csv_file = 'heart_health_triggers.csv'  # Replace with the path to your CSV file
df = pd.read_csv(csv_file)
df.fillna('', inplace=True)

# Create a database list from the DataFrame
database = []
for index, row in df.iterrows():
    item = {
        "trigger_word": row['trigger_word'],
        "synonyms": row['synonyms'].split(','),  # Assuming synonyms are comma-separated
        "keywords": row['keywords'].split(','),  # Assuming keywords are comma-separated
        "response": row['response']
    }
    database.append(item)

# Precompute embeddings for each question-related field in batches
trigger_embeddings = embedding_model.encode(df['trigger_word'].tolist(), batch_size=32)
synonyms_embeddings = [embedding_model.encode(syn.split(','), batch_size=32) for syn in df['synonyms']]
keywords_embeddings = [embedding_model.encode(kw.split(','), batch_size=32) for kw in df['keywords']]

db_embeddings = []
for idx in range(len(df)):
    db_embeddings.append({
        "trigger_embedding": trigger_embeddings[idx],
        "synonyms_embeddings": synonyms_embeddings[idx],
        "keywords_embeddings": keywords_embeddings[idx]
    })

# Precompute embeddings for domain keywords
domain_keywords = ['heart', 'cardiac', 'women', 'health', 'cardiology']
domain_embeddings = embedding_model.encode(domain_keywords)

def correct_spelling(text):
    """
    Corrects spelling errors in the given text using a spell checker.
    """
    # Correct only for longer texts or obvious typos
    if len(text.split()) > 1:
        corrected_words = [
            spellchecker.correction(word) if spellchecker.correction(word) else word
            for word in text.split()
        ]
        corrected_text = ' '.join(corrected_words)
        return corrected_text
    return text

def find_best_context(query, threshold=0.5):
    """
    Takes a query and returns the best matching context from the database based on cosine similarity.
    If no match is found above the threshold, it returns None.
    """
    # Encode the query
    query_embedding = embedding_model.encode([query.lower()])

    # Initialize best match variables
    best_match_score = 0
    best_match_response = None
    best_match_type = None  # To track whether the match is from trigger, synonym, or keyword

    for index, item_embeddings in enumerate(db_embeddings):
        # Calculate cosine similarity scores
        trigger_scores = [cosine_similarity(query_embedding, [syn_emb]).flatten()[0] for syn_emb in item_embeddings['synonyms_embeddings']]
        synonyms_scores = [cosine_similarity(query_embedding, [syn_emb]).flatten()[0] for syn_emb in item_embeddings['synonyms_embeddings']]
        keywords_scores = [cosine_similarity(query_embedding, [kw_emb]).flatten()[0] for kw_emb in item_embeddings['keywords_embeddings']]

        # Determine maximum scores
        max_trigger_score = max(trigger_scores) if synonyms_scores else 0
        max_synonym_score = max(synonyms_scores) if synonyms_scores else 0
        max_keyword_score = max(keywords_scores) if keywords_scores else 0

        # Find the maximum score among trigger, synonym, and keyword scores
        max_score = max(max_trigger_score, max_synonym_score, max_keyword_score)

        # Determine the type of match (trigger, synonym, keyword)
        if max_score == max_trigger_score:
            match_type = 'Trigger'
        elif max_score == max_synonym_score:
            match_type = 'Synonym'
        elif max_score == max_keyword_score:
            match_type = 'Keyword'
        else:
            continue

        # Log each entry with a significant match
        if max_score >= threshold-0.2:  # Log entries where the score is above 0.7
            logging.info(
                f"Query: '{query}',"
                f"Scores - Trigger: {max_trigger_score:.4f}, Synonym: {max_synonym_score:.4f}, "
                f"Keyword: {max_keyword_score:.4f}, Type: {match_type} "
                f"Response: {database[index]['response']}"
            )

        # Update best match if a higher score is found
        if max_score > best_match_score and max_score >= threshold:
            best_match_score = max_score
            best_match_response = database[index]['response']
            best_match_type = match_type

    # Log the best match score and response
    if best_match_score >= threshold:
        logging.info(
            f"Query: '{query}', Best Match Score: {best_match_score:.4f}, "
            f"Best Match Response: '{best_match_response}', Match Type: {best_match_type}"
        )
    else:
        logging.warning(f"No suitable match found for query: '{query}' with score above threshold: {threshold}")

    return best_match_response
 

def generate_response_with_placeholder(prompt):
    """
    Placeholder for the generative API response.
    Replaces the actual API call with a fixed response for development purposes.
    """
    response = "This is a placeholder response generated for your question."
    return response

def is_domain_relevant(query, threshold=0.4):
    """
    Checks if the query is relevant to the domain using cosine similarity.
    Returns True if any similarity score with domain keywords is above the threshold.
    """
    query_embedding = embedding_model.encode([query.lower()])
    relevance_scores = [cosine_similarity(query_embedding, [dom_emb]).flatten()[0] for dom_emb in domain_embeddings]

    # Log the domain relevance scores
    logging.info(f"Domain Relevance Scores for '{query}': {relevance_scores}")

    return any(score >= threshold for score in relevance_scores)

def get_response(user_input, threshold=0.7):
    """
    Handles the logic to decide whether to use a pre-defined response or generate one with the API.
    Returns a response and updates the context history.
    """
    logging.info(f"Direct Match")
    # Direct match with original input
    context_response = find_best_context(user_input, threshold)
    if context_response:
        return context_response
    
    logging.info(f"After Spell Correction")
    # Correct spelling and try matching again (skip correction for very short inputs)
    corrected_input = correct_spelling(user_input)
    if corrected_input != user_input:
        logging.info(f"Corrected Input: {corrected_input}")
        context_response = find_best_context(corrected_input, threshold)
        if context_response:
            return context_response
    logging.info(f"Checking Domain relevance")
    # Check for domain relevance
    if is_domain_relevant(corrected_input):
        prompt = f"User asked: {corrected_input}. Please provide a helpful response related to women's heart health."
        logging.info(f"Prompt for Generative API: {prompt}")

        # Send corrected input to the Generative API
        response = generate_response_with_placeholder(prompt)
        return response

    # Fallback response for unrelated queries
    fallback_response = "I'm sorry, I can only answer questions related to women's heart health. Can you please clarify your question?"
    return fallback_response 

# Setup logging
logging.basicConfig(level=logging.INFO, filename='chatbot.log', filemode='a', format='%(asctime)s - %(message)s')

@app.route('/chatbot', methods=['POST'])
def chat():
    try:
        recieved_api_key = request.headers.get('X-API-KEY') 
        expected_api_key= 'fpv74NMceEzy.5OsNsX43uhfa2GSGPPOB1/o2ABXg0mMwniAef02'
        
        if recieved_api_key != expected_api_key:
            return jsonify({"unauthorized_access":"invalid api key"}), 401

        user_input = request.json.get("user_input", "").strip()

        if not user_input:
            return jsonify({"error": "Missing user input"}), 400

        response= get_response(user_input)

        return jsonify({"response": response}), 200

    except Exception as exception:
        logging.error(f"Error occurred: {str(exception)}")
        return jsonify({"error": str(exception)}), 500

if __name__ == '__main__':
    app.run(debug=True)
