use chrono::{NaiveDate, Timelike};
use colored::Colorize;
use std::collections::HashMap;
use std::io;
use std::time::Instant;
use vader_sentimental::SentimentIntensityAnalyzer;
use whatsapp_chat_parser::{parse_chats_log, Author, WhatsAppChatMessage};

const WHATSAPP_FILENAME: &str = "chata.txt";
const DISPLAY_CHATS: bool = false;
const MINIMUM_USER_ACTIVITY_PER_DAY_CHAT_COUNT: usize = 100;
const MINIMUM_CONVERSATION_FREQUENCY_PER_DAY_CHAT_COUNT: usize = 150;
const MINIMUM_ACTIVE_HOUR_PER_USER_CHAT_COUNT: usize = 500;
const MINIMUM_SILENCE_THRESHOLD_IN_SEC: i64 = 3600;

#[derive(Default)]
struct SentimentData {
    positive_count: usize,
    negative_count: usize,
    neutral_count: usize,
    most_positive_message: Option<String>,
    most_negative_message: Option<String>,
}

fn main() -> io::Result<()> {
    let start_time = Instant::now();
    let chat = parse_chats_log(WHATSAPP_FILENAME)?;

    let parse_duration = start_time.elapsed();

    let mut user_message_count: HashMap<String, usize> = HashMap::new();
    let mut user_activity_per_day: HashMap<String, HashMap<String, usize>> = HashMap::new();
    let mut active_hours: HashMap<String, HashMap<u32, usize>> = HashMap::new();
    let mut message_lengths: Vec<usize> = Vec::new();

    let user_activity = analyze_user_activity(&chat);
    let conversation_frequency = analyze_conversation_frequency(&chat);
    let active_hours_per_user = analyze_active_hours(&chat);

    let mut sentiment_analysis: HashMap<String, SentimentData> = HashMap::new();

    for msg in &chat {
        if let Author::User(username) = &msg.author {
            *user_message_count.entry(username.clone()).or_insert(0) += 1;

            let date = msg.datetime.date();

            let user_activity_per_day = user_activity_per_day.entry(username.clone()).or_default();
            *user_activity_per_day.entry(date.to_string()).or_insert(0) += 1;

            let hour = msg.datetime.hour();
            let user_hours = active_hours.entry(username.clone()).or_default();
            *user_hours.entry(hour).or_insert(0) += 1;

            message_lengths.push(msg.message.len());

            let sentiment = analyze_sentiment(&msg.message);
            let entry = sentiment_analysis.entry(username.clone()).or_default();

            match sentiment.as_str() {
                "Positive" => entry.positive_count += 1,
                "Negative" => entry.negative_count += 1,
                "Neutral" => entry.neutral_count += 1,
                _ => {}
            };

            if sentiment == "Positive"
                && (entry.most_positive_message.is_none()
                    || analyze_sentiment(&entry.most_positive_message.clone().unwrap())
                        < analyze_sentiment(&msg.message))
            {
                entry.most_positive_message = Some(msg.message.clone());
            }

            if sentiment == "Negative"
                && (entry.most_negative_message.is_none()
                    || analyze_sentiment(&entry.most_negative_message.clone().unwrap())
                        > analyze_sentiment(&msg.message))
            {
                entry.most_negative_message = Some(msg.message.clone());
            };

            if DISPLAY_CHATS {
                println!(
                    "{} {}: {}",
                    msg.datetime
                        .format("[%-m/%-d/%y, %-I:%M:%S %p]")
                        .to_string()
                        .magenta(),
                    username.green(),
                    msg.message
                );
            }
        }
    }

    println!("\n\n====================SUMMARY====================");
    println!("Total chats: {}", chat.len().to_string().cyan());
    println!("Time taken to parse: {:.2?}", parse_duration);
    println!("Unique users and their message counts:");
    for (user, count) in &user_message_count {
        println!("{}: {}", user.green(), count.to_string().purple());
    }

    println!("\nUser activity per day:");
    for (user, activity) in &user_activity {
        println!("{}", user.green());
        for (date, count) in activity {
            if *count < MINIMUM_USER_ACTIVITY_PER_DAY_CHAT_COUNT {
                continue;
            }
            println!(
                "    {}: {}",
                date.to_string().yellow(),
                count.to_string().purple()
            );
        }
    }

    println!("\nConversation frequency per day:");
    for (day, count) in &conversation_frequency {
        if *count < MINIMUM_CONVERSATION_FREQUENCY_PER_DAY_CHAT_COUNT {
            continue;
        }
        println!("    {}: {} messages", day.yellow(), count);
    }

    println!("\nActive hours per user:");
    for (user, hours) in &active_hours_per_user {
        println!("{}", user.green());
        for (hour, count) in hours {
            if *count < MINIMUM_ACTIVE_HOUR_PER_USER_CHAT_COUNT {
                continue;
            }

            println!("    Hour {}: {} messages", hour.to_string().yellow(), count);
        }
    }

    println!("\nSentiment Analysis:");
    for (user, data) in &sentiment_analysis {
        println!(
            "{}: Positive: {}, Negative: {}, Neutral: {}",
            user.green(),
            data.positive_count.to_string().purple(),
            data.negative_count.to_string().purple(),
            data.neutral_count.to_string().purple()
        );
        if let Some(msg) = &data.most_positive_message {
            println!("    Most Positive Message: {}", msg.green());
        }
        if let Some(msg) = &data.most_negative_message {
            println!("    Most Negative Message: {}", msg.red());
        }
    }

    if let Some(first_msg) = chat.first() {
        println!(
            "First Message Date: {}",
            first_msg.datetime.to_string().yellow()
        );
    }

    if let Some(last_msg) = chat.last() {
        println!(
            "Last Message Date: {}",
            last_msg.datetime.to_string().yellow()
        );
    }

    detect_silence(&chat, MINIMUM_SILENCE_THRESHOLD_IN_SEC);
    Ok(())
}

fn analyze_sentiment(message: &str) -> String {
    let analyzer = SentimentIntensityAnalyzer::new();
    let sentiment = analyzer.polarity_scores(message);

    if sentiment.compound > 0.1 {
        "Positive".to_string()
    } else if sentiment.compound < -0.1 {
        "Negative".to_string()
    } else {
        "Neutral".to_string()
    }
}

fn detect_silence(chat: &[WhatsAppChatMessage], silence_threshold: i64) {
    let mut silence_durations = Vec::new();

    for window in chat.windows(2) {
        let msg1 = &window[0];
        let msg2 = &window[1];
        let time_diff = msg2
            .datetime
            .signed_duration_since(msg1.datetime)
            .num_seconds();

        if time_diff > silence_threshold {
            silence_durations.push((msg1, msg2, time_diff));
        }
    }

    silence_durations.sort_by(|a, b| b.2.cmp(&a.2));

    for (i, (msg1, msg2, time_diff)) in silence_durations.iter().take(5).enumerate() {
        println!(
            "Top {} longest silence: {} to {} ({} hours)",
            i + 1,
            msg1.datetime,
            msg2.datetime,
            time_diff / 3600
        );
    }
}

fn analyze_user_activity(
    chat: &[WhatsAppChatMessage],
) -> HashMap<String, HashMap<NaiveDate, usize>> {
    chat.iter().fold(HashMap::new(), |mut acc, msg| {
        let date = msg.datetime;
        *acc.entry(msg.author.to_string())
            .or_default()
            .entry(date.into())
            .or_insert(0) += 1;
        acc
    })
}

fn analyze_conversation_frequency(chat: &[WhatsAppChatMessage]) -> HashMap<String, usize> {
    chat.iter().fold(HashMap::new(), |mut acc, msg| {
        let day = msg.datetime.format("%Y-%m-%d").to_string();
        *acc.entry(day).or_insert(0) += 1;
        acc
    })
}

fn analyze_active_hours(chat: &[WhatsAppChatMessage]) -> HashMap<String, HashMap<u32, usize>> {
    chat.iter().fold(HashMap::new(), |mut acc, msg| {
        let hour = msg.datetime.hour();
        *acc.entry(msg.author.to_string())
            .or_default()
            .entry(hour)
            .or_insert(0) += 1;
        acc
    })
}
