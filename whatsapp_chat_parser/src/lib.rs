use chrono::NaiveDateTime;
use regex::Regex;
use std::fs::File;
use std::io::{self, BufRead, BufReader};

const MEDIA_OMITTED: &str = "<Media omitted>";
const MESSAGE_EDITED: &str = "<This message was edited>";
const PINNED_MESSAGE: &str = "You pinned a message";
const MESSAGE_E2E_ENCRYPTED: & str = "Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them. Tap to learn more.";
const MESSAGE_TIMER_UPDATED: &str = "The message timer was updated. New messages will disappear from this chat 7 days after they're sent, except when kept. Tap to change.";

#[derive(Debug, Clone, PartialEq)]
pub enum Message {
    MediaOmitted,
    PinnedMessage,
    E2EEncryptedMessage,
    TimerUpdatedMessage,
    Conversation(String),
    EditedConversation(String),
}

#[derive(Debug, Clone, PartialEq)]
pub enum Author {
    User(String),
    System,
}

#[derive(Debug, Clone)]
pub struct WhatsAppChatMessage {
    pub datetime: NaiveDateTime,
    pub author: Author,
    pub message: Message,
}

fn parse_datetime(datetime_str: &str, cached_format: &mut Option<String>) -> NaiveDateTime {
    static DATE_FORMATS: [&str; 40] = [
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

    if let Some(format) = cached_format {
        if let Ok(datetime) = NaiveDateTime::parse_from_str(datetime_str, format) {
            return datetime;
        }
    }

    for format in &DATE_FORMATS {
        if let Ok(datetime) = NaiveDateTime::parse_from_str(datetime_str, format) {
            *cached_format = Some(format.to_string());
            return datetime;
        }
    }

    NaiveDateTime::default()
}

fn parse_message(
    line: &str,
    regex: &Regex,
    cached_format: &mut Option<String>,
) -> Option<WhatsAppChatMessage> {
    regex.captures(line).map(|cap| {
        let datetime = cap.name("datetime").map_or(NaiveDateTime::default(), |m| {
            parse_datetime(m.as_str(), cached_format)
        });

        let author = cap
            .name("author")
            .map_or(Author::System, |m| Author::User(m.as_str().to_string()));

        let message = cap
            .name("message")
            .map_or(Message::Conversation("".to_string()), |m| {
                let msg = m.as_str();
                if msg == MEDIA_OMITTED {
                    Message::MediaOmitted
                } else if msg == PINNED_MESSAGE {
                    Message::PinnedMessage
                } else if msg == MESSAGE_E2E_ENCRYPTED {
                    Message::E2EEncryptedMessage
                } else if msg == MESSAGE_TIMER_UPDATED {
                    Message::TimerUpdatedMessage
                } else if msg.ends_with(MESSAGE_EDITED) {
                    Message::EditedConversation(
                        msg.trim_end_matches(MESSAGE_EDITED).trim().to_string(),
                    )
                } else {
                    Message::Conversation(msg.to_string())
                }
            });

        WhatsAppChatMessage {
            datetime,
            author,
            message,
        }
    })
}

pub fn parse_chats_log(filename: &str) -> io::Result<Vec<WhatsAppChatMessage>> {
    let file = File::open(filename)?;
    let reader = BufReader::new(file);

    let regex = Regex::new(
        r"(?ms)^(?P<datetime>[0-9/-]+,?\s[^-]+) - (?:(?P<author>[^:]+): )?(?P<message>.*)$",
    )
    .unwrap();

    let mut chat_db = Vec::new();
    let mut buffer_text = String::new();
    let mut cached_format: Option<String> = None;

    for line in reader.lines() {
        let line = line?;

        if regex.is_match(&line) {
            if !buffer_text.is_empty() {
                if let Some(msg) = parse_message(&buffer_text, &regex, &mut cached_format) {
                    chat_db.push(msg);
                }
            }
            buffer_text = line;
        } else {
            buffer_text.push('\n');
            buffer_text.push_str(&line);
        }
    }

    if !buffer_text.is_empty() {
        if let Some(msg) = parse_message(&buffer_text, &regex, &mut cached_format) {
            chat_db.push(msg);
        }
    }

    Ok(chat_db)
}
