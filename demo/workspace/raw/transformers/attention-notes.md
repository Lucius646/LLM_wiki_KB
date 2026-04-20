# Attention Notes

Transformers use attention to let each token weigh information from other positions in the sequence. Instead of compressing everything into a fixed hidden state, attention computes context-sensitive interactions at every layer.

In practice, attention is useful because it creates dynamic routing. A token can emphasize nearby words, long-range dependencies, or special markers depending on the current query and the learned key-value structure.

For the original architecture and terminology, see:
- https://arxiv.org/abs/1706.03762
- https://jalammar.github.io/illustrated-transformer/
