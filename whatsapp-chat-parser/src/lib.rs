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
    pub message: String,
    pub author: Author,
    pub datetime: NaiveDateTime,
}

fn parse_datetime_from_multiple_formats(datetime_str: &str) -> NaiveDateTime {
    // List of date formats to try
    let date_formats = [
        "%-m/%-d/%y, %-I:%M %p",        // 4/22/24, 12:30 PM
        "%-m/%-d/%Y, %-I:%M %p",        // 4/22/24, 12:30 PM
        "%-m-%-d-%y %-I:%M %p",         // 04-22-24 12:30 PM
        "%-m-%-d-%Y %-I:%M %p",         // 04-22-2024 12:30 PM
        "%Y-%-m-%-d %-I:%M %p",         // 2024-04-22 12:30 PM
        "%Y/%-m/%-d %-I:%M %p",         // 2024/04/22 12:30 PM
        "%-d/%-m/%Y, %-I:%M %p",        // 22/4/2024, 12:30 PM
        "%-d/%-m/%y, %-I:%M %p",        // 22/4/24, 12:30 PM
        "%-d-%-m-%Y %-I:%M %p",         // 04-22-2024 12:30 PM
        "%-d-%-m-%y %-I:%M %p",         // 04-22-24 12:30 PM
    ];

    // Attempt to parse datetime with each format
    for format in &date_formats {
        if let Ok(datetime) = NaiveDateTime::parse_from_str(datetime_str, *format) {
            return datetime;
        }
    }

    // If none of the formats succeed, return default datetime
    NaiveDateTime::default()
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
                parse_datetime_from_multiple_formats(m.as_str())
            }),
            author: mat
                .name("author")
                .map_or(Author::System, |m| Author::User(m.as_str().to_string())),
            message: mat.name("message").map_or("", |m| m.as_str()).to_string(),
        });
    }

    None
}
