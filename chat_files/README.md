# Chat Files Directory

This directory stores your WhatsApp chat exports for use with the persona chat system.

## File Format

Chat files must be in **LangChain format**:

```text
date, time AM/PM - sender: message
```

Example:

```text
5/26/23, 2:04 AM - John: Hey there!
5/26/23, 2:05 AM - Wick: Hi! How are you?
```

## Converting Your WhatsApp Exports

WhatsApp exports use square brackets `[date, time]` format. Convert them using the parser:

```bash
cd whatsapp_chat_parser
cargo run --release --bin langchain_parser "path/to/export.txt" > "../chat_files/converted_chat.txt"
```

## Usage

1. Export your WhatsApp chat from the mobile app
2. Convert it to LangChain format using the command above
3. Place the converted file in this directory
4. Set `CHAT_FILE` in your `.env` to the filename:

   ```bash
   CHAT_FILE=converted_chat.txt
   ```

## Verifying Your Files

To verify a chat file is properly formatted, run the parser again - it should output clean, readable messages:

```bash
cd whatsapp_chat_parser
cargo run --bin langchain_parser "../chat_files/your_chat.txt"
```

If you see parsing errors or unexpected output, the file format may be incorrect.
