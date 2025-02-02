use serde::{Deserialize, Serialize};
use std::env;
use std::fs::{create_dir_all, File};
use std::io;
use std::path::Path;
use whatsapp_chat_parser::{get_unique_author, parse_chats_log, Author, Message};

#[derive(Serialize, Deserialize, Clone)]
#[serde(rename_all = "lowercase")]
enum Sender {
    Gpt,
    Human,
}

#[derive(Serialize, Deserialize, Clone)]
struct Conversation<'a> {
    from: Sender,
    value: &'a str,
}

#[derive(Serialize, Deserialize)]
struct Conversations<'a> {
    #[serde(borrow)]
    conversations: Vec<Conversation<'a>>,
}

fn write_conversations_to_json(
    conversations: Vec<Conversation>,
    base_output_path: &str,
) -> io::Result<()> {
    // If the conversation is too long (more than 40), we split it into smaller chunks
    if conversations.len() > 40 {
        let base_output_prefix = base_output_path.trim_end_matches(".txt");
        for (i, chunk) in conversations.chunks(40).enumerate() {
            // Skip too short chunks (less than 3 messages)
            if chunk.len() < 3 {
                continue;
            }

            let output_path = format!("{}-{}.json", base_output_prefix, i);
            let conversations_to_write = Conversations {
                conversations: chunk.to_vec(),
            };

            let file = File::create(&output_path)?;
            serde_json::to_writer_pretty(file, &conversations_to_write)?;
        }
    } else {
        // If the conversation is not too long, just write to a single file
        if conversations.len() < 3 {
            return Ok(()); // Skip conversations with less than 3 messages
        }

        let file = File::create(base_output_path)?;
        let conversations_to_write = Conversations { conversations };

        serde_json::to_writer_pretty(file, &conversations_to_write)?;
    }

    Ok(())
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
    let valid_authors = authors
        .iter()
        .filter_map(|author| match author {
            Author::User(name) => Some(name),
            _ => None,
        })
        .collect::<Vec<&String>>();

    if valid_authors.len() != 2 {
        eprintln!("Only 2 people are allowed in the chat");
        std::process::exit(1);
    }

    if !valid_authors.contains(&your_name) {
        eprintln!("Your name is not in the chat");
        eprintln!("Valid names are: {:?}", valid_authors);
        std::process::exit(1);
    }

    // Collect valid conversations
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
                        Sender::Human
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

    // Output path handling
    let output_folder = "data/preprocessed";
    let base_output_path = format!("{}/{}", output_folder, filename);

    // Create the output folder if it doesn't exist
    if !Path::new(output_folder).exists() {
        create_dir_all(output_folder)?;
    }
    // Write the conversations to JSON files
    write_conversations_to_json(conversations, &base_output_path)?;
    println!("Writted to {}", output_folder);
    Ok(())
}
