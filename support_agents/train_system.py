"""Train and evaluate the multi-agent customer support system."""
import sys
from pathlib import Path
from support_agents.data_loader import load_train_validation, get_intent_distribution
from support_agents.multi_agent_system import MultiAgentSystem
from support_agents.evaluator import SystemEvaluator


def main():
    """Train multi-agent system and evaluate on validation data."""
    # Paths
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("Multi-Agent Customer Support System")
    print("=" * 60)
    
    # Load data
    print("\n[1/4] Loading datasets...")
    train_df, validation_df = load_train_validation()
    
    print("\nIntent Distribution (Train):")
    print(get_intent_distribution(train_df))
    
    # Train system
    print("\n[2/4] Training multi-agent system...")
    system = MultiAgentSystem()
    system.fit(train_df)
    
    stats = system.get_system_stats()
    print(f"✓ Trained {stats['total_agents']} agents")
    print(f"✓ Intents: {', '.join(stats['intent_names'][:5])}{'...' if len(stats['intent_names']) > 5 else ''}")
    
    # Evaluate
    print("\n[3/4] Evaluating on validation set...")
    evaluator = SystemEvaluator(system)
    metrics, results = evaluator.evaluate(validation_df, confidence_threshold=0.3)
    
    print(f"\n✓ Accuracy:  {metrics['accuracy']:.4f}")
    print(f"✓ Precision: {metrics['precision']:.4f}")
    print(f"✓ Recall:    {metrics['recall']:.4f}")
    print(f"✓ F1 Score:  {metrics['f1_score']:.4f}")
    print(f"✓ Avg Intent Confidence: {metrics['avg_intent_confidence']:.4f}")
    
    # Save results
    print("\n[4/4] Saving results...")
    evaluator.save_results(metrics, results, results_dir)
    print(f"✓ Results saved to {results_dir}/")
    
    return system, metrics


if __name__ == "__main__":
    main()
