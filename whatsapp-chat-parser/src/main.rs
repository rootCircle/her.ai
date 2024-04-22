use std::io;
use whatsapp_chat_parser::parse_chats_log;

fn main() -> io::Result<()>{
    let chat = parse_chats_log("chat.txt")?;
    for msg in chat {
        println!("{:#?}", msg);
    }
    
    Ok(())
}
