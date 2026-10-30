"""Multi-agent customer support system router."""
import pandas as pd
from support_agents.intent_classifier import IntentClassifier
from support_agents.response_generator import ResponseGenerator


class MultiAgentSystem:
    """Route customer queries to specialized agents based on intent."""
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.response_generator = ResponseGenerator()
        self.agent_specs = {}
        
    def fit(self, train_df):
        """Train the system on training data."""
        # Train intent classifier
        self.intent_classifier.fit(
            train_df['instruction'].values,
            train_df['intent'].values
        )
        
        # Train response generator
        self.response_generator.fit(
            train_df['instruction'],
            train_df['response'],
            train_df['intent'].values
        )
        
        # Store agent specs by intent
        for intent in train_df['intent'].unique():
            intent_data = train_df[train_df['intent'] == intent]
            self.agent_specs[intent] = {
                'category': intent_data['category'].mode()[0] if len(intent_data) > 0 else None,
                'sample_count': len(intent_data),
                'categories': intent_data['category'].unique().tolist()
            }
        
        return self
    
    def process_query(self, query, confidence_threshold=0.3):
        """Process a customer query through the agent system.
        
        Returns:
            dict with intent, response, confidence, and agent info
        """
        # Classify intent
        predicted_intent = self.intent_classifier.predict([query])[0]
        confidence = float(self.intent_classifier.get_confidence_scores([query])[0])
        
        # Generate response
        response_result = self.response_generator.generate(query, predicted_intent)
        
        # Get agent specs
        agent_info = self.agent_specs.get(predicted_intent, {})
        
        return {
            'query': query,
            'predicted_intent': predicted_intent,
            'intent_confidence': confidence,
            'response': response_result['response'],
            'response_confidence': response_result['confidence'],
            'matched_instruction': response_result['matched_instruction'],
            'agent': agent_info.get('category', 'unknown'),
            'above_threshold': confidence >= confidence_threshold
        }
    
    def batch_process(self, queries, confidence_threshold=0.3):
        """Process multiple queries."""
        results = []
        for query in queries:
            result = self.process_query(query, confidence_threshold)
            results.append(result)
        return results
    
    def get_system_stats(self):
        """Get statistics about the multi-agent system."""
        return {
            'total_agents': len(self.agent_specs),
            'agents': self.agent_specs,
            'intent_names': list(self.intent_classifier.intent_names)
        }
