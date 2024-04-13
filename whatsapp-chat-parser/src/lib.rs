use chrono::NaiveDateTime;
use regex::Regex;
use std::fs::File;
use std::io::{self, prelude::*, BufReader};

#[derive(Debug)]
pub enum Author {
    User(String),
    System,
}

#[derive(Debug)]
pub struct WhatsAppChatMessage {
    message: String,
    author: Author,
    datetime: NaiveDateTime,
}

pub fn parse_chats_log(filename: &str) -> io::Result<Vec<WhatsAppChatMessage>> {
    let file = File::open(filename)?;
    let reader = BufReader::new(file);

    let start_with_date_regex =
        Regex::new(r"(?m)(?<datetime>.+, .+) - (?:(?<author>.+):)?(?<message>[\s\S]+)").unwrap();
    let mut buffer_text: String = String::new();

    let mut chat_db: Vec<WhatsAppChatMessage> = Vec::new();

    for line in reader.lines() {
        let line = line?;
        if start_with_date_regex.is_match(&line) {
            if !buffer_text.is_empty() {
                chat_db.push(parse_message(buffer_text).unwrap());
            }
            buffer_text = line;
        } else {
            buffer_text.push('\n');
            buffer_text.push_str(&line);
        }
    }

    if !buffer_text.is_empty() {
        chat_db.push(parse_message(buffer_text).unwrap());
    }

    Ok(chat_db)
}

// Parses one single message and return a struct 
fn parse_message(line: String) -> Option<WhatsAppChatMessage> {
    let regex =
        Regex::new(r"(?m)(?:(?<datetime>.+, .+) - )?(?:(?<author>.+): )?(?<message>[\s\S]+)")
            .unwrap();

    // result will be an iterator over tuples containing the start and end indices for each match in the string
    let mut result = regex.captures_iter(&line);
    
    if let Some(mat) = result.next() {
        return Some(WhatsAppChatMessage {
            datetime: mat.name("datetime").map_or(NaiveDateTime::default(), |m| {
                NaiveDateTime::parse_from_str(m.as_str(), "%-m/%-d/%y, %-I:%M %p").unwrap()
            }),
            author: mat
                .name("author")
                .map_or(Author::System, |m| Author::User(m.as_str().to_string())),
            message: mat.name("message").map_or("", |m| m.as_str()).to_string(),
        });
    }

    None
}
