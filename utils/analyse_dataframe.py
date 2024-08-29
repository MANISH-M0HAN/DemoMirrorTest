from sklearn.metrics.pairwise import cosine_similarity



def find_best_context(query, threshold):

    query_embedding = embedding_model.encode([query.lower()])

    best_match_score = 0
    best_max_match_score = 0
    best_match_response = None
    best_max_match_response = None
    best_match_type = None
    best_max_match_type = None

    for index, item_embeddings in enumerate(db_embeddings):
        trigger_score = cosine_similarity(query_embedding, item_embeddings['trigger_embedding'].reshape(1, -1)).flatten()[0]
        synonym_scores = [cosine_similarity(query_embedding, syn_emb.reshape(1, -1)).flatten()[0] for syn_emb in item_embeddings['synonyms_embeddings']]
        keyword_scores = [cosine_similarity(query_embedding, kw_emb.reshape(1, -1)).flatten()[0] for kw_emb in item_embeddings['keywords_embeddings']]

        max_synonym_score = max(synonym_scores) if synonym_scores else 0
        max_keyword_score = max(keyword_scores) if keyword_scores else 0

        max_scores_sum = trigger_score + max_synonym_score + max_keyword_score
        avg_score = max_scores_sum / 3

        if trigger_score >= 0.65 or max_synonym_score >= 0.65 or max_keyword_score >= 0.65:
            logging.info(
                f"Strong direct match found. Query: '{query}', Trigger Score: {trigger_score:.4f}, "
                f"Synonym Score: {max_synonym_score:.4f}, Keyword Score: {max_keyword_score:.4f} "
                f"Response: {database[index]}"
            )
            best_max_match_score = max(trigger_score, max_synonym_score, max_keyword_score)
            best_max_match_response = database[index]
            best_max_match_type = "Max Match"
        
        if avg_score > best_match_score and trigger_score < 0.65 and max_synonym_score < 0.65 and max_keyword_score < 0.65:
            logging.info(
                f"Strong direct match found. Query: '{query}', Trigger Score: {trigger_score:.4f}, "
                f"Synonym Score: {max_synonym_score:.4f}, Keyword Score: {max_keyword_score:.4f} "
                f"Response: {database[index]}"
            )
            best_match_score = avg_score
            best_match_response = database[index]
            best_match_type = "Avg Max Match"
            
    if best_match_score >= threshold and best_max_match_score < best_match_score:
        logging.info(
            f"Query: '{query}', Best Match Score: {best_match_score:.4f}, "
            f"Best Match Response: '{best_match_response}', Match Type: {best_match_type}"
        )
        return best_match_response
    
    elif best_max_match_score > best_match_score:
        logging.info(
            f"Query: '{query}', Max Match Score: {best_max_match_score:.4f}, "
            f"Best Match Response: '{best_max_match_response}', Match Type: {best_max_match_type}"
        )
        return best_max_match_response
    
    else:
        logging.warning(f"No suitable match found for query: '{query}' with score above threshold: {threshold}")
        return None

def match_columns(query, best_match_response):
    query_lower = query.lower()
    query_lower = process_user_input.correct_spelling(query_lower)

    intent_words = {
        "What": [
            "What",
            "Define",
            "Identify",
            "Describe",
            "Clarify",
            "Specify",
            "Detail",
            "Outline",
            "State",
            "Explain",
            "Determine",
            "Depict",
            "Summarize",
            "Designate",
            "Distinguish",
        ],
        "Symptoms": [
            "Symptoms",
            "Signs",
            "Indications",
            "Manifestations",
            "Warning",
            "Clues",
            "Evidence",
            "Redflags",
            "Markers",
            "Presentations",
            "Outcomes",
            "Patterns",
            "Phenomena",
            "Traits",
            "Occurrences",
        ],
        "Why": [
            "Why",
            "Causes",
            "Reason",
            "Purpose",
            "Explain",
            "Justification",
            "Origin",
            "Motive",
            "Trigger",
            "Rationale",
            "Grounds",
            "Basis",
            "Excuse",
            "Source",
            "Factor",
        ],
        "How": [
            "How",
            "Method",
            "Means",
            "Procedure",
            "Steps",
            "Technique",
            "Process",
            "Way",
            "Approach",
            "Strategy",
            "System",
            "Manner",
            "Framework",
            "Form",
            "Mode",
            "Prevention",
            "Avoidance",
            "Safeguard",
            "Protection",
            "Mitigation",
            "Reduction",
            "Intervention",
            "Defense",
            "Deterrence",
            "Shielding",
        ],
    }

    # Collect matching columns and their first occurrence positions
    matching_columns = []
    match_found = False  # Variable to track if a match is found

    for column, keywords in intent_words.items():
        for keyword in keywords:
            keyword_lower = keyword.lower()
            position = query_lower.find(keyword_lower)
            if position != -1 and best_match_response.get(column):
                matching_columns.append((position, best_match_response[column]))
                match_found = True  # Set match_found to True when a match is found
                break  # Move to the next column once a match is found

# If no match was found, add the response from the first column
    if not match_found and intent_words:
        first_column = next(iter(intent_words))  # Get the first column
        if best_match_response.get(first_column):
            matching_columns.append((0, best_match_response[first_column]))  # Add the first column's response

    # Sort the matched columns by the position of their first occurrence in the query
    matching_columns.sort(key=lambda x: x[0])

    # Combine responses in the order of their appearance in the query
    responses = [response for _, response in matching_columns]

    # Return the combined response
    if responses:
        return " ".join(responses)

    # Fallback to the best matching column if no intent word is matched
    query_embedding = embedding_model.encode([query_lower])
    column_scores = cosine_similarity(query_embedding, column_embeddings).flatten()

    best_column_index = column_scores.argmax()
    best_column_name = column_names[best_column_index]
    logging.info(
        f"Best column match (fallback): {best_column_name} with score {column_scores[best_column_index]:.4f}"
    )

    return best_match_response.get(best_column_name, "")

