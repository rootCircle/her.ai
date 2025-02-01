use colored::Colorize;
use std::io;
use whatsapp_chat_parser::{parse_chats_log, Author};

const WHATSAPP_FILENAME: &str = "chata.txt";

fn main() -> io::Result<()> {
    let chat = parse_chats_log(WHATSAPP_FILENAME)?;

    for msg in &chat {
        if let Author::User(username) = &msg.author {
            println!(
                "{} {}: {}",
                msg.datetime
                    .format("[%-m/%-d/%y, %-I:%M:%S %p]")
                    .to_string()
                    .magenta(),
                username.green(),
                msg.message
            );
        }
    }

    Ok(())
}
