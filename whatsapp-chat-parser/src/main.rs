use colored::Colorize;
use std::collections::HashMap;
use std::io;
use std::time::Instant;
use whatsapp_chat_parser::{parse_chats_log, Author};

const WHATSAPP_FILENAME: &str = "chat.txt";
const DISPLAY_CHATS: bool = true;

fn main() -> io::Result<()> {
    let start_time = Instant::now();

    let chat = parse_chats_log(WHATSAPP_FILENAME)?;

    let parse_duration = start_time.elapsed();

    let mut user_message_count: HashMap<String, usize> = HashMap::new();

    for msg in &chat {
        if let Author::User(username) = &msg.author {
            *user_message_count.entry(username.clone()).or_insert(0) += 1;
            if DISPLAY_CHATS {
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
    }

    println!("\n\n====================SUMMARY====================");
    println!("Total chats: {}", chat.len().to_string().cyan());
    println!("Time taken to parse: {:.2?}", parse_duration);
    println!("Unique users and their message counts:");
    for (user, count) in &user_message_count {
        println!("{}: {}", user.green(), count.to_string().purple());
    }
    println!(
        "First Message Date: {}",
        chat.first().unwrap().datetime.to_string().yellow()
    );
    println!(
        "Last Message Date: {}",
        chat.last().unwrap().datetime.to_string().yellow()
    );

    Ok(())
}
