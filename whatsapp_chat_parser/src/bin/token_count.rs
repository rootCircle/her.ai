use std::env;
use std::io;
use tiktoken_rs::num_tokens_from_messages;
use tiktoken_rs::ChatCompletionRequestMessage;
use whatsapp_chat_parser::{parse_chats_log, Author, Message};

fn main() -> io::Result<()> {
    let args: Vec<String> = env::args().collect();
    
    if args.len() < 2 {
        eprintln!("Usage: {} <input_file>", args[0]);
        eprintln!("Counts tokens in WhatsApp chat for GPT models");
        eprintln!("Example: cargo run --bin token_count chat.txt");
        std::process::exit(1);
    }
    
    let filename = &args[1];

    let chat = parse_chats_log(filename)?;
    let mut messages = vec![];
    for msg in &chat {
        if let Author::User(username) = &msg.author {
            match &msg.message {
                Message::Conversation(conversation) | Message::EditedConversation(conversation) => {
                    messages.push(ChatCompletionRequestMessage {
                        content: Some(format!(
                            "{}: {}",
                            msg.datetime.format("[%-m/%-d/%y, %-I:%M:%S %p]"),
                            conversation
                        )),
                        role: username.to_string(),
                        name: None,
                        function_call: None,
                    });
                }
                // Suppress Media Omitted/System messages
                Message::MediaOmitted
                | Message::PinnedMessage
                | Message::E2EEncryptedMessage
                | Message::TimerUpdatedMessage => {}
            }
        }
    }
    let max_tokens = num_tokens_from_messages("gpt-4o", &messages).unwrap();
    println!("max_tokens: {}", max_tokens);

    Ok(())
}
