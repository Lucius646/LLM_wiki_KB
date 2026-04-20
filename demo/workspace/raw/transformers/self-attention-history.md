# Self-Attention History

The self-attention story in transformers is partly an architectural response to the bottlenecks of recurrent models. Recurrent networks process tokens step by step, while self-attention exposes pairwise token interactions in parallel.

Historically, this mattered because training throughput improved and long-distance dependencies became easier to model. The tradeoff is that naive attention cost grows quadratically with sequence length.

Background references:
- https://arxiv.org/abs/1409.0473
- https://arxiv.org/abs/1706.03762
