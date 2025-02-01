use chrono::{NaiveDate, NaiveDateTime, NaiveTime};
use std::io::Write;
use tempfile::NamedTempFile;
use whatsapp_chat_parser::{parse_chats_log, Author};

#[test]
fn test_parse_chats_log_basic() {
    let chat_data = r#"1/17/25, 10:00 AM - Alice: Hello there!
1/17/25, 10:01 AM - Bob: Hi!
1/17/25, 10:02 AM - This is a system message.
1/17/25, 10:03 AM - Alice: Multiline
message
1/17/25, 10:04 AM - Charlie: Message with - and :
1/17/25, 10:05 AM - Bob: Another message.
"#;

    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "{}", chat_data).expect("Failed to write to temp file");

    let chat =
        parse_chats_log(temp_file.path().to_str().unwrap()).expect("Failed to parse chat log");

    assert_eq!(chat.len(), 6);

    assert_eq!(
        chat[0].datetime.format("%-m/%-d/%y, %-I:%M %p").to_string(),
        "1/17/25, 10:00 AM"
    );
    assert_eq!(chat[0].author, Author::User("Alice".to_string()));
    assert_eq!(chat[0].message, "Hello there!");

    assert_eq!(chat[1].author, Author::User("Bob".to_string()));
    assert_eq!(chat[1].message, "Hi!");

    assert!(matches!(chat[2].author, Author::System));
    assert_eq!(chat[2].message, "This is a system message.");

    assert_eq!(chat[3].author, Author::User("Alice".to_string()));
    assert_eq!(chat[3].message, "Multiline\nmessage");

    assert_eq!(chat[4].author, Author::User("Charlie".to_string()));
    assert_eq!(chat[4].message, "Message with - and :");

    assert_eq!(chat[5].author, Author::User("Bob".to_string()));
    assert_eq!(chat[5].message, "Another message.\n");
}

#[test]
fn test_parse_chats_log_empty_file() {
    let temp_file = NamedTempFile::new().expect("Failed to create temp file");

    let chat = parse_chats_log(temp_file.path().to_str().unwrap())
        .expect("Failed to parse empty chat log");

    assert!(chat.is_empty());
}

#[test]
fn test_parse_chats_log_special_characters() {
    let chat_data = r#"1/17/25, 10:00 AM - Alice: Special characters !@#$%^&*()_+=
1/17/25, 10:01 AM - Bob: Multiline
Message
With special @characters
"#;
    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "{}", chat_data).expect("Failed to write to temp file");
    let chat =
        parse_chats_log(temp_file.path().to_str().unwrap()).expect("Failed to parse chat log");

    assert_eq!(chat.len(), 2);

    assert_eq!(chat[0].author, Author::User("Alice".to_string()));
    assert_eq!(chat[0].message, "Special characters !@#$%^&*()_+=");

    assert_eq!(chat[1].author, Author::User("Bob".to_string()));
    assert_eq!(
        chat[1].message,
        "Multiline\nMessage\nWith special @characters\n"
    );
}

#[test]
fn test_parse_chats_log_system_messages() {
    let chat_data = r#"1/17/25, 10:00 AM - This is a system message.
1/17/25, 10:01 AM - Alice: Hello!
1/17/25, 10:02 AM - Another system event occurred.
"#;

    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "{}", chat_data).expect("Failed to write to temp file");

    let chat =
        parse_chats_log(temp_file.path().to_str().unwrap()).expect("Failed to parse chat log");

    assert_eq!(chat.len(), 3);

    assert!(matches!(chat[0].author, Author::System));
    assert_eq!(chat[0].message, "This is a system message.");

    assert_eq!(chat[1].author, Author::User("Alice".to_string()));
    assert_eq!(chat[1].message, "Hello!");

    assert!(matches!(chat[2].author, Author::System));
    assert_eq!(chat[2].message, "Another system event occurred.\n");
}

#[test]
fn test_parse_chats_log_with_various_date_formats() {
    // Chat log with messages in different datetime formats

    let chat_data = r#"4/22/24, 12:30 PM - Alice: Hello!
4/22/2024, 12:30 PM - Bob: Hi!
04-22-24 12:30 PM - Alice: How are you?
04-22-2024 12:30 PM - Bob: I'm good, thanks.
2024-04-22 12:30 PM - Alice: Great!
2024/04/22 12:30 PM - A system event occurred.
22/4/2024, 12:30 PM - Alice: Let's meet tomorrow.
22/4/24, 12:30 PM - Bob: Sure, sounds good.
22-04-2024 12:30 PM - Alice: Don't forget the presentation.
22-04-24 12:30 PM - Reminder: Meeting at 3 PM.
4/22/24, 12:30 - Alice: Working late?
4/22/2024, 12:30 - Bob: Yeah, lots to do.
04-22-24 12:30 - Alice: Same here.
04-22-2024 12:30 - Bob: Let's finish it soon.
2024-04-22 12:30 - End of day summary.
2024/04/22 12:30 - Alice: Goodnight!
22/4/2024, 12:30 - Bob: See you tomorrow.
22/4/24, 12:30 - Alice: Take care.
22-04-2024 12:30 - Bye!
22-04-24 12:30 - System maintenance scheduled.
4/22/24 12:30 PM - Alice: This is a 12-hour format without comma.
4/22/24 12:30 - Alice: This is a 24-hour format without comma.
2024-04-22 12:30 - Alice: This is a 12-hour format with dash and no AM/PM.
2024-04-22 12:30 - Bob: Another 24-hour format, no AM/PM.
2024/04/22 12:30 PM - Alice: Testing with slash and 12-hour format.
2024/04/22 12:30 - Alice: This is a 24-hour format with slash, no AM/PM.
2024-04-22 12:30 - Bob: This is another 24-hour format with dash, no AM/PM.
22/4/2024 12:30 PM - Alice: Let's meet at noon.
22/4/24 12:30 PM - Alice: Meeting in the afternoon.
22-04-2024 12:30 - Alice: Working late at night.
22-04-24 12:30 - System maintenance scheduled.
4/22/24, 12:30 PM - Bob: Morning meeting.
4/22/24, 12:30 - Alice: Checking in late.
2024-04-22, 12:30 PM - Reminder: Don't forget the meeting at 2 PM.
2024/04/22 12:30 PM - Alice: How's everything going today?
22/4/2024, 12:30 - Bob: All good, wrapping up.
04-22-24 12:30 PM - System: Logoff time reached.
2024/04/22 12:30 - Bob: Let's finish the report.
2024/04/22 12:30 PM - Alice: Testing edge cases.
22/4/2024, 12:30 PM - Alice: Test message in 12-hour format.
22-04-2024, 12:30 PM - System: System event processed successfully.
2024-04-22 12:30 - End of workday summary.
4/22/24, 12:30 PM - Reminder: Meeting scheduled.
22-04-24 12:30 PM - Alice: Testing with dash and 12-hour format.
22-04-24 12:30 PM - Bob: Let's wrap up!
22-04-24 12:30 - Alice: Late-night work.
22/4/24 12:30 - System: Server restarted at 23:30.
2024/04/22, 12:30 - Alice: Good night!"#;

    // Write the chat data to a temporary file
    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "{}", chat_data).expect("Failed to write to temp file");

    // Parse the chat log
    let chat =
        parse_chats_log(temp_file.path().to_str().unwrap()).expect("Failed to parse chat log");

    assert_eq!(chat.len(), 48); // Total messages in the chat log

    let default_datetime = NaiveDateTime::default();
    let message_datetime = NaiveDateTime::new(
        NaiveDate::from_ymd_opt(2024, 4, 22).expect("Failed to create NaiveDate"),
        NaiveTime::from_hms_opt(12, 30, 00).expect("Failed to create NaiveTime"),
    );

    let message_datetime_year_trimmed = NaiveDateTime::new(
        NaiveDate::from_ymd_opt(24, 4, 22).expect("Failed to create NaiveDate"),
        NaiveTime::from_hms_opt(12, 30, 00).expect("Failed to create NaiveTime"),
    );

    for (i, msg) in chat.iter().enumerate() {
        assert!(
            msg.datetime != default_datetime,
            "Failed to parse datetime for message at index {}: {:?}",
            i,
            msg
        );
        assert!(
            msg.datetime == message_datetime || msg.datetime == message_datetime_year_trimmed,
            "Incorrect datetime for message at index {}: {:?}",
            i,
            msg
        );
        assert!(
            !msg.message.is_empty(),
            "Message content missing for message at index {}",
            i
        );
    }

    // Check specific cases
    assert_eq!(chat[0].message, "Hello!");
    assert!(matches!(chat[5].author, Author::System));
    assert_eq!(chat[5].message, "A system event occurred.");
    assert!(matches!(chat[19].author, Author::System));
    assert_eq!(chat[19].message, "System maintenance scheduled.");
}
