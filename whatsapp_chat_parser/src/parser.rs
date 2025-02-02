use crate::{
    Author, Message, WhatsAppChatMessage, MEDIA_OMITTED, MESSAGE_E2E_ENCRYPTED, MESSAGE_EDITED,
    MESSAGE_TIMER_UPDATED, PINNED_MESSAGE,
};
use chrono::NaiveDateTime;
use regex::Regex;

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

pub(crate) fn parse_message(
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
