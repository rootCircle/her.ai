# WhatsApp Chat Parser

A Rust-based WhatsApp chat parser with multiple analysis and conversion tools.

## Prerequisites

Export your WhatsApp chat from the mobile app and save it as a text file.

## Available Tools

### `langchain_parser`

Converts WhatsApp chat from `[date, time]` format to LangChain-compatible format (`date, time - sender: message`).

**Usage:**

```bash
cargo run --bin langchain_parser <input_file> > <output_file>
# Example:
cargo run --bin langchain_parser chat.txt > chat_langchain.txt
```

### `analysis`

Analyzes WhatsApp chat for metrics like user activity, sentiment, message frequency, and conversation patterns.

**Usage:**

```bash
cargo run --bin analysis <input_file>
# Example:
cargo run --bin analysis chat.txt
```

### `token_count`

Counts tokens in WhatsApp chat messages for GPT model usage estimation.

**Usage:**

```bash
cargo run --bin token_count <input_file>
# Example:
cargo run --bin token_count chat.txt
```

### `finetune_preprocess`

Preprocesses WhatsApp chat for fine-tuning LLMs by converting to conversation format with role labels.

**Usage:**

```bash
cargo run --bin finetune_preprocess <input_file> <your_name>
# Example:
cargo run --bin finetune_preprocess chat.txt John
```

## Performance [Highly Recommended for big files]

For faster execution, build with the `--release` flag:

```bash
cargo run --release --bin <target> <input_file>
```
