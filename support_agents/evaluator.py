"""Evaluation metrics for the multi-agent system."""
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import json


class SystemEvaluator:
    """Evaluate system performance on validation data."""
    
    def __init__(self, system):
        self.system = system
        
    def evaluate(self, validation_df, confidence_threshold=0.3):
        """Evaluate system on validation dataset."""
        results = self.system.batch_process(
            validation_df['instruction'].values,
            confidence_threshold
        )
        
        # Extract predictions
        predictions = [r['predicted_intent'] for r in results]
        true_intents = validation_df['intent'].values
        confidence_scores = [r['intent_confidence'] for r in results]
        
        # Calculate metrics
        accuracy = accuracy_score(true_intents, predictions)
        precision = precision_score(true_intents, predictions, average='weighted', zero_division=0)
        recall = recall_score(true_intents, predictions, average='weighted', zero_division=0)
        f1 = f1_score(true_intents, predictions, average='weighted', zero_division=0)
        
        # Count queries above threshold
        above_threshold = sum(1 for r in results if r['above_threshold'])
        
        metrics = {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'total_samples': len(validation_df),
            'above_threshold_count': above_threshold,
            'above_threshold_percentage': float(above_threshold / len(validation_df) * 100),
            'avg_intent_confidence': float(np.mean(confidence_scores)),
            'avg_response_confidence': float(np.mean([r['response_confidence'] for r in results]))
        }
        
        return metrics, results
    
    def save_results(self, metrics, results, output_path):
        """Save evaluation results to file."""
        # Save metrics as JSON
        with open(output_path / 'metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)
        
        # Save detailed results
        results_df = pd.DataFrame(results)
        results_df.to_csv(output_path / 'detailed_results.csv', index=False)
        
        # Save summary
        with open(output_path / 'summary.txt', 'w') as f:
            f.write("Multi-Agent Customer Support System - Evaluation Summary\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Accuracy:  {metrics['accuracy']:.4f}\n")
            f.write(f"Precision: {metrics['precision']:.4f}\n")
            f.write(f"Recall:    {metrics['recall']:.4f}\n")
            f.write(f"F1 Score:  {metrics['f1_score']:.4f}\n\n")
            f.write(f"Samples above confidence threshold: {metrics['above_threshold_count']}/{metrics['total_samples']} ")
            f.write(f"({metrics['above_threshold_percentage']:.1f}%)\n")
            f.write(f"Avg Intent Confidence: {metrics['avg_intent_confidence']:.4f}\n")
            f.write(f"Avg Response Confidence: {metrics['avg_response_confidence']:.4f}\n")
        
        print(f"Results saved to {output_path}/")
