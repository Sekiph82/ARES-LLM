# Ares Self-Learning

People train LLMs for 24-72 hours because model learning is slow and expensive:
the model sees many batches, compares its predictions with the next token,
updates millions or billions of weights, and repeats until validation loss
improves. Long runs are normal when the dataset is large or the model has many
parameters.

Ares should not silently retrain itself forever on your laptop. That can:

- overfit to a tiny local dataset
- learn bad outputs or mistakes
- forget useful behavior
- consume power and slow the laptop
- create a model that looks better on training loss but behaves worse in real
  tasks

Instead, Ares now uses a safer practical self-learning loop:

1. Keep a local memory file at `data/ares_memory.md`.
2. Save durable lessons, preferences, workflows, and shop snapshots there.
3. Include that memory in future Ares prompts.
4. Use scratch-model training as an experiment, not as the main coding brain.

This gives Ares continuity without risky unattended model mutation.

## Does Self-Learning Mean No Training?

Not exactly.

There are two meanings people mix together:

- **Memory learning**: Ares saves useful facts, preferences, lessons, and shop
  snapshots, then reads them in future prompts. This changes Ares' behavior
  immediately without changing model weights.
- **Weight learning**: training changes the neural network parameters. This is
  slower, riskier, and needs evaluation.

So Ares can "learn itself" safely through local memory. But if you mean "become
a better neural model," that still requires training or fine-tuning. A good
self-learning agent uses memory first, collects approved examples second, and
only retrains after the data is clean enough to trust.

## Future Upgrade

Later, Ares can add a supervised learning queue:

- collect approved examples
- remove private/sensitive data
- run a scheduled training job
- evaluate before accepting the new checkpoint
- keep rollback checkpoints

That is the responsible path to a more self-improving local model.
