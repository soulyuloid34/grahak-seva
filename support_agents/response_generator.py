"""Generate or retrieve responses for customer queries."""
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ResponseGenerator:
    """Match queries to existing responses using similarity."""
    
    def __init__(self):
        self.instruction_vectorizer = TfidfVectorizer(max_features=300, stop_words='english')
        self.instruction_vectors = None
        self.responses = None
        self.intents = None
        
    def fit(self, instructions, responses, intents=None):
        """Build response database from training data."""
        self.instructions = instructions
        self.responses = responses
        self.intents = intents
        self.instruction_vectors = self.instruction_vectorizer.fit_transform(instructions)
        return self
    
    def generate(self, query, intent=None, top_k=1):
        """Find and return similar response from training data."""
        query_vector = self.instruction_vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, self.instruction_vectors)[0]
        
        # Filter by intent if provided
        if intent is not None and self.intents is not None:
            mask = self.intents == intent
            similarities = similarities * mask
        
        # Get top matching response
        top_idx = np.argmax(similarities)
        response = self.responses.iloc[top_idx]
        confidence = float(similarities[top_idx])
        
        return {
            'response': response,
            'confidence': confidence,
            'matched_instruction': self.instructions.iloc[top_idx]
        }
    
    def batch_generate(self, queries, intents=None):
        """Generate responses for multiple queries."""
        results = []
        for i, query in enumerate(queries):
            intent = intents[i] if intents is not None else None
            result = self.generate(query, intent)
            results.append(result)
        return results
