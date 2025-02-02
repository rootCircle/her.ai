use serde::{Deserialize, Serialize};
use std::env;
use std::io;
use whatsapp_chat_parser::get_unique_author;
use whatsapp_chat_parser::{parse_chats_log, Author, Message};

#[derive(Serialize, Deserialize)]
enum Sender<'a> {
    Gpt,
    Human(&'a str),
}

#[derive(Serialize, Deserialize)]
struct Conversation<'a> {
    from: Sender<'a>,
    value: &'a str,
}

fn main() -> io::Result<()> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("Usage: <program> <filename> <your_name>");
        eprintln!("Your name is the one which will turn into AI responses");
        std::process::exit(1);
    }

    let filename = &args[1];
    let your_name = &args[2];
    let chat = parse_chats_log(filename)?;

    let authors = get_unique_author(&chat);

    if !authors.contains(&Author::User(your_name.to_string())) {
        eprintln!("Your name is not in the chat");
        eprintln!(
            "Valid names are: {:?}",
            authors
                .iter()
                .filter_map(|author| {
                    match author {
                        Author::User(name) => Some(name),
                        _ => None,
                    }
                })
                .collect::<Vec<&String>>()
        );
        std::process::exit(1);
    }

    let conversations: Vec<Conversation> = chat
        .iter()
        .filter_map(|msg| {
            if let Author::User(username) = &msg.author {
                if let Message::Conversation(conversation)
                | Message::EditedConversation(conversation) = &msg.message
                {
                    let sender = if username == your_name {
                        Sender::Gpt
                    } else {
                        Sender::Human(username)
                    };
                    return Some(Conversation {
                        from: sender,
                        value: conversation,
                    });
                }
            }
            None
        })
        .collect();

    let json_output = serde_json::to_string_pretty(&conversations)?;
    println!("{}", json_output);

    Ok(())
}
