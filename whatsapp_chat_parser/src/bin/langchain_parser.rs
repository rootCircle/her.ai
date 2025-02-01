use colored::Colorize;
use std::env;
use std::io;
use whatsapp_chat_parser::{parse_chats_log, Author, Message};

const DEFAULT_WHATSAPP_FILENAME: &str = "chat.txt";

fn main() -> io::Result<()> {
    let args: Vec<String> = env::args().collect();
    let filename = args
        .get(1)
        .map_or(DEFAULT_WHATSAPP_FILENAME, String::as_str);

    let chat = parse_chats_log(filename)?;

    for msg in &chat {
        if let Author::User(username) = &msg.author {
            match &msg.message {
                Message::Conversation(conversation) | Message::EditedConversation(conversation) => {
                    println!(
                        "{} {}: {}",
                        msg.datetime
                            .format("[%-m/%-d/%y, %-I:%M:%S %p]")
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
