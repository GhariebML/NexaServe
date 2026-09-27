# Models

Repository defaults are chat `qwen2.5:3b` and embedding `nomic-embed-text`; vectors are 768-dimensional. The chat model is not replaced by this bundle. Model tags are mutable registry labels; record pulled model digests/manifests and Ollama version in deployment change control.

Benchmark actual Arabic groundedness, no-answer behavior, latency, GPU/RAM and concurrent request load. A model listing or English one-word response is insufficient. Offline export copies Ollama model store from a matching Ollama release; run generation and vector-dimension checks after import.
