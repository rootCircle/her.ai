use std::io::Write;
use tempfile::NamedTempFile;
use whatsapp_chat_parser::{parse_chats_log, Author, Message};

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
    assert_eq!(
        chat[0].message,
        Message::Conversation("Hello there!".to_string())
    );

    assert_eq!(chat[1].author, Author::User("Bob".to_string()));
    assert_eq!(chat[1].message, Message::Conversation("Hi!".to_string()));

    assert!(matches!(chat[2].author, Author::System));
    assert_eq!(
        chat[2].message,
        Message::Conversation("This is a system message.".to_string())
    );

    assert_eq!(chat[3].author, Author::User("Alice".to_string()));
    assert_eq!(
        chat[3].message,
        Message::Conversation("Multiline\nmessage".to_string())
    );

    assert_eq!(chat[4].author, Author::User("Charlie".to_string()));
    assert_eq!(
        chat[4].message,
        Message::Conversation("Message with - and :".to_string())
    );

    assert_eq!(chat[5].author, Author::User("Bob".to_string()));
    assert_eq!(
        chat[5].message,
        Message::Conversation("Another message.\n".to_string())
    );
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
    assert_eq!(
        chat[0].message,
        Message::Conversation("Special characters !@#$%^&*()_+=".to_string())
    );

    assert_eq!(chat[1].author, Author::User("Bob".to_string()));
    assert_eq!(
        chat[1].message,
        Message::Conversation("Multiline\nMessage\nWith special @characters\n".to_string())
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
    assert_eq!(
        chat[0].message,
        Message::Conversation("This is a system message.".to_string())
    );

    assert_eq!(chat[1].author, Author::User("Alice".to_string()));
    assert_eq!(chat[1].message, Message::Conversation("Hello!".to_string()));

    assert!(matches!(chat[2].author, Author::System));
    assert_eq!(
        chat[2].message,
        Message::Conversation("Another system event occurred.\n".to_string())
    );
}
