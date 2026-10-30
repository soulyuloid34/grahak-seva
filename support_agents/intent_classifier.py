"""Intent classifier for customer queries using TF-IDF and logistic regression."""
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder


class IntentClassifier:
    """Classify customer instructions into intents."""
    
    def __init__(self):
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=500, stop_words='english', ngram_range=(1, 2))),
            ('classifier', LogisticRegression(max_iter=200, random_state=42, multi_class='multinomial'))
        ])
        self.label_encoder = LabelEncoder()
        self.intents = None
        
    def fit(self, instructions, intents):
        """Train the classifier on instruction-intent pairs."""
        self.intents = self.label_encoder.fit_transform(intents)
        self.pipeline.fit(instructions, self.intents)
        self.intent_names = self.label_encoder.classes_
        return self
    
    def predict(self, instructions):
        """Predict intents for instructions."""
        intent_indices = self.pipeline.predict(instructions)
        return self.label_encoder.inverse_transform(intent_indices)
    
    def predict_proba(self, instructions):
        """Get probability estimates for each intent."""
        probas = self.pipeline.named_steps['classifier'].predict_proba(
            self.pipeline.named_steps['tfidf'].transform(instructions)
        )
        return probas
    
    def get_confidence_scores(self, instructions):
        """Get max confidence score for predictions."""
        probas = self.predict_proba(instructions)
        return np.max(probas, axis=1)
