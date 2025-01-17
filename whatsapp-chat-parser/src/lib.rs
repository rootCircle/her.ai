use chrono::NaiveDateTime;
use regex::Regex;
use std::fmt;
use std::fs::File;
use std::io::{self, prelude::*, BufReader};

#[derive(Debug, Clone, PartialEq)]
pub enum Author {
    User(String),
    System,
}

impl fmt::Display for Author {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Author::User(string) => write!(f, "{}", string),
            Author::System => write!(f, ""),
        }
    }
}

#[derive(Debug, Clone)]
pub struct WhatsAppChatMessage {
    pub message: String,
    pub author: Author,
    pub datetime: NaiveDateTime,
}

fn parse_datetime_from_multiple_formats(
    datetime_str: &str,
    cached_format: &mut Option<String>,
) -> NaiveDateTime {
    // List of date formats to try

    let date_formats = [
        // Group 1: MM/DD/YY
        "%-m/%-d/%y, %-I:%M %p", // Sample: 4/22/24, 12:30 PM
        "%-m/%-d/%y %-I:%M %p",  // Sample: 4/22/24 12:30 PM
        "%-m/%-d/%y, %H:%M",     // Sample: 4/22/24, 23:30
        "%-m/%-d/%y %H:%M",      // Sample: 4/22/24 23:30
        // Group 2: MM/DD/YYYY
        "%-m/%-d/%-Y, %-I:%M %p", // Sample: 4/22/2024, 12:30 PM
        "%-m/%-d/%-Y %-I:%M %p",  // Sample: 4/22/2024 12:30 PM
        "%-m/%-d/%-Y, %H:%M",     // Sample: 4/22/2024, 23:30
        "%-m/%-d/%-Y %H:%M",      // Sample: 4/22/2024 23:30
        // Group 3: MM-DD-YY
        "%-m-%-d-%y, %-I:%M %p", // Sample: 04-22-24, 12:30 PM
        "%-m-%-d-%y %-I:%M %p",  // Sample: 04-22-24 12:30 PM
        "%-m-%-d-%y, %H:%M",     // Sample: 04-22-24, 23:30
        "%-m-%-d-%y %H:%M",      // Sample: 04-22-24 23:30
        // Group 4: MM-DD-YYYY
        "%-m-%-d-%-Y, %-I:%M %p", // Sample: 04-22-2024, 12:30 PM
        "%-m-%-d-%-Y %-I:%M %p",  // Sample: 04-22-2024 12:30 PM
        "%-m-%-d-%-Y, %H:%M",     // Sample: 04-22-2024, 23:30
        "%-m-%-d-%-Y %H:%M",      // Sample: 04-22-2024 23:30
        // Group 5: DD/MM/YYYY
        "%-d/%-m/%-Y, %-I:%M %p", // Sample: 22/4/2024, 12:30 PM
        "%-d/%-m/%-Y %-I:%M %p",  // Sample: 22/4/2024 12:30 PM
        "%-d/%-m/%-Y, %H:%M",     // Sample: 22/4/2024, 23:30
        "%-d/%-m/%-Y %H:%M",      // Sample: 22/4/2024 23:30
        // Group 6: DD/MM/YY
        "%-d/%-m/%y, %-I:%M %p", // Sample: 22/4/24, 12:30 PM
        "%-d/%-m/%y %-I:%M %p",  // Sample: 22/4/24 12:30 PM
        "%-d/%-m/%y, %H:%M",     // Sample: 22/4/24, 23:30
        "%-d/%-m/%y %H:%M",      // Sample: 22/4/24 23:30
        // Group 7: DD-MM-YYYY
        "%-d-%-m-%-Y, %-I:%M %p", // Sample: 22-04-2024, 12:30 PM
        "%-d-%-m-%-Y %-I:%M %p",  // Sample: 22-04-2024 12:30 PM
        "%-d-%-m-%-Y, %H:%M",     // Sample: 22-04-2024, 23:30
        "%-d-%-m-%-Y %H:%M",      // Sample: 22-04-2024 23:30
        // Group 8: DD-MM-YY
        "%-d-%-m-%y, %-I:%M %p", // Sample: 22-04-24, 12:30 PM
        "%-d-%-m-%y %-I:%M %p",  // Sample: 22-04-24 12:30 PM
        "%-d-%-m-%y, %H:%M",     // Sample: 22-04-24, 23:30
        "%-d-%-m-%y %H:%M",      // Sample: 22-04-24 23:30
        // Group 9: YYYY-MM-DD
        "%-Y-%-m-%-d, %-I:%M %p", // Sample: 2024-04-22, 12:30 PM
        "%-Y-%-m-%-d %-I:%M %p",  // Sample: 2024-04-22 12:30 PM
        "%-Y-%-m-%-d, %H:%M",     // Sample: 2024-04-22, 23:30
        "%-Y-%-m-%-d %H:%M",      // Sample: 2024-04-22 23:30
        // Group 10: YYYY/MM/DD
        "%-Y/%-m/%-d, %-I:%M %p", // Sample: 2024/04/22, 12:30 PM
        "%-Y/%-m/%-d %-I:%M %p",  // Sample: 2024/04/22 12:30 PM
        "%-Y/%-m/%-d, %H:%M",     // Sample: 2024/04/22, 23:30
        "%-Y/%-m/%-d %H:%M",      // Sample: 2024/04/22 23:30
    ];

    // Use cached format if available
    if let Some(format) = cached_format {
        if let Ok(datetime) = NaiveDateTime::parse_from_str(datetime_str, format) {
            return datetime;
        }
    }

    // Try all formats and cache the first successful one
    for format in &date_formats {
        if let Ok(datetime) = NaiveDateTime::parse_from_str(datetime_str, format) {
            *cached_format = Some(format.to_string());
            return datetime;
        }
    }

    // If none of the formats succeed, return default datetime
    NaiveDateTime::default()
}

pub fn parse_chats_log(filename: &str) -> io::Result<Vec<WhatsAppChatMessage>> {
    let file = File::open(filename)?;
    let reader = BufReader::new(file);

    let start_with_date_regex = Regex::new(
        r"(?m)(?<datetime>[0-9-/]+,? [^-]+) - (?:(?<author>[^:]+): )?(?<message>[\s\S]+)",
    )
    .unwrap();
    let mut buffer_text: String = String::new();

    let mut chat_db: Vec<WhatsAppChatMessage> = Vec::new();
    let mut cached_format: Option<String> = None;

    for line in reader.lines() {
        let line = line?;
        if start_with_date_regex.is_match(&line) {
            if !buffer_text.is_empty() {
                chat_db.push(parse_message(buffer_text, &mut cached_format).unwrap());
            }
            buffer_text = line;
        } else {
            buffer_text.push('\n');
            buffer_text.push_str(&line);
        }
    }

    if !buffer_text.is_empty() {
        chat_db.push(parse_message(buffer_text, &mut cached_format).unwrap());
    }

    Ok(chat_db)
}

// Parses one single message and return a struct
fn parse_message(line: String, cached_format: &mut Option<String>) -> Option<WhatsAppChatMessage> {
    let regex = Regex::new(
        r"(?m)(?:(?<datetime>[0-9-/]+,? [^-]+) - )?(?:(?<author>[^:]+): )?(?<message>[\s\S]+)",
    )
    .unwrap();

    let mut result = regex.captures_iter(&line);

    if let Some(mat) = result.next() {
        return Some(WhatsAppChatMessage {
            datetime: mat.name("datetime").map_or(NaiveDateTime::default(), |m| {
                parse_datetime_from_multiple_formats(m.as_str(), cached_format)
            }),
            author: mat
                .name("author")
                .map_or(Author::System, |m| Author::User(m.as_str().to_string())),
            message: mat.name("message").map_or("", |m| m.as_str()).to_string(),
        });
    }
    None
}
