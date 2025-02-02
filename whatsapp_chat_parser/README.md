## To run

For first time:

Create a file containing the exported whatsapp chat and name it `chat.txt`.

```bash
cargo run --bin=langchain_parser -- ./chat.txt > output_chat.txt
cargo run --bin=analysis -- ./chat.txt
cargo run --bin=token_count -- ./chat.txt
❯ cargo run --bin=finetune_preprocess ./chat.txt MY_NAME > output.json
```
For faster runtimes, use `--release` flag
