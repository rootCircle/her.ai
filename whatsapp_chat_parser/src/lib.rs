use chrono::NaiveDateTime;
use parser::parse_message;
use regex::Regex;
use std::collections::HashSet;
use std::fs::File;
use std::io::{self, BufRead, BufReader};

mod parser;

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

#[derive(Debug, Clone, Eq, Hash, PartialEq)]
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

pub fn get_unique_author(message: &[WhatsAppChatMessage]) -> HashSet<&Author> {
    HashSet::<&Author>::from_iter(message.iter().map(|msg| &msg.author))
        .into_iter()
        .collect()
}

pub fn parse_chats_log(filename: &str) -> io::Result<Vec<WhatsAppChatMessage>> {
    let file = File::open(filename)?;
    let reader = BufReader::new(file);

    let regex = Regex::new(
        r"(?ms)^(?P<datetime>[0-9/-]+,?\s[^\r\n-]+) - (?:(?P<author>[^\r\n:]+): )?(?P<message>.*)$",
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
