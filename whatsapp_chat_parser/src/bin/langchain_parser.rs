use colored::Colorize;
use std::env;
use std::io;
use whatsapp_chat_parser::{parse_chats_log, Author, Message};

fn main() -> io::Result<()> {
    let args: Vec<String> = env::args().collect();
    
    if args.len() < 2 {
        eprintln!("Usage: {} <input_file>", args[0]);
        eprintln!("Converts WhatsApp chat from [date, time] format to LangChain format");
        eprintln!("Example: cargo run --bin langchain_parser chat.txt > output.txt");
        std::process::exit(1);
    }
    
    let filename = &args[1];

    let chat = parse_chats_log(filename)?;

    for msg in &chat {
        if let Author::User(username) = &msg.author {
            match &msg.message {
                Message::Conversation(conversation) | Message::EditedConversation(conversation) => {
                    println!(
                        "{} - {}: {}",
                        msg.datetime
                            .format("%-m/%-d/%y, %-I:%M %p")
                            .to_string()
                            .magenta(),
                        username.green(),
                        conversation
                    );
                }
                // Suppress Media Omitted/System messages
                Message::MediaOmitted
                | Message::PinnedMessage
                | Message::E2EEncryptedMessage
                | Message::TimerUpdatedMessage => {}
            }
        }
    }

    Ok(())
}
