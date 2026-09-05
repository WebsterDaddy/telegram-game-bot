import os
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# In-memory database to store our game state
game_state = {
    "group_chat_id": None,
    "answers": {},  # Maps user_id to their text answer
    "names": {},     # Maps user_id to their first name
    "current_question": ""
}

def load_questions():
    """Reads questions from questions.txt file if it exists."""
    if os.path.exists("questions.txt"):
        with open("questions.txt", "r", encoding="utf-8") as file:
            # Read lines, strip extra spaces/newlines, and ignore empty lines
            questions = [line.strip() for line in file if line.strip()]
            if questions:
                return questions
                
    # Fallback default questions if the text file isn't found
    return [
        "What is your absolute favorite thing to do on a lazy Sunday?",
        "If you could only eat one food item for the rest of your life, what would it be?",
        "What is a weird habit you have when you're home alone?"
    ]

# Load questions into memory when the bot launches
QUESTIONS = load_questions()

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the game in a group chat with a random question."""
    if update.message.chat.type == "private":
        await update.message.reply_text("Please run this command in a Group Chat!")
        return
        
    game_state["group_chat_id"] = update.message.chat_id
    game_state["answers"] = {}
    
    # Pick a random question from our loaded list
    game_state["current_question"] = random.choice(QUESTIONS)
    
    bot_username = context.bot.username
    
    message = (
        f"🕵️‍♂️ *SOCIAL DEDUCTION GAME STARTED!* 🕵️‍♀️\n\n"
        f"The question is: *{game_state['current_question']}*\n\n"
        f"Send me a Private Message with your answer using the command:\n"
        f"`/answer your answer here`\n\n"
        f"Example: `/answer your_answer_here`\n"
        f"[Click here to DM me](https://t.me/{bot_username})"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collects answers secretly from players in DMs."""
    if update.message.chat.type != "private":
        await update.message.reply_text("Shh! Send your answers to me in a Private Message!")
        return

    user = update.message.from_user
    user_answer = " ".join(context.args)

    if not user_answer:
        await update.message.reply_text("Please include your answer. Example: `/answer sleeping`")
        return

    game_state["answers"][user.id] = user_answer
    game_state["names"][user.id] = user.first_name
    
    await update.message.reply_text("Got it! Wait in the group chat for the interrogation phase.")
    
    if game_state["group_chat_id"]:
        await context.bot.send_message(
            chat_id=game_state["group_chat_id"], 
            text=f"✅ {user.first_name} has submitted their answer!"
        )

async def interrogate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Picks a random answer and starts the debate."""
    if update.message.chat.type == "private":
        await update.message.reply_text("Run this command in the Group Chat to start the debate!")
        return

    if not game_state["answers"]:
        await update.message.reply_text("No one has submitted an answer yet!")
        return
        
    imposter_id = random.choice(list(game_state["answers"].keys()))
    imposter_answer = game_state["answers"][imposter_id]
    
    await update.message.reply_text(
        f"🚨 *INTERROGATION PHASE* 🚨\n\n"
        f"Question was: *\"{game_state['current_question']}\"*\n\n"
        f"Someone answered: *\"{imposter_answer}\"*\n\n"
        f"Who do you think it is? Discuss in the chat! The imposter must try to blend in.",
        parse_mode="Markdown"
    )

def main():
    # Insert your BotFather token here
    application = Application.builder().token("8625371369:AAHtXLWOI6VKfRB3Vq8d3cBQ1H0Dp_G_5GY").build()

    application.add_handler(CommandHandler("startgame", start_game))
    application.add_handler(CommandHandler("answer", answer))
    application.add_handler(CommandHandler("interrogate", interrogate))

    print(f"Bot is running! Loaded {len(QUESTIONS)} questions from file. Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == '__main__':
    main()