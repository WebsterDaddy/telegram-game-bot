import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# In-memory database to store our game state
game_state = {
    "group_chat_id": None,
    "answers": {},  # Maps user_id to their text answer
    "names": {},     # Maps user_id to their first name
    "current_question": "",
    "imposter_id": None,  # Tracks the actual author
    "votes": {}           # Tracks who voted for who
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
    """Picks a random answer and displays a voting keyboard."""
    if update.message.chat.type == "private":
        await update.message.reply_text("Run this command in the Group Chat!")
        return

    if not game_state["answers"]:
        await update.message.reply_text("No one has submitted an answer yet!")
        return
        
    # Pick the imposter and save their ID
    imposter_id = random.choice(list(game_state["answers"].keys()))
    game_state["imposter_id"] = imposter_id
    imposter_answer = game_state["answers"][imposter_id]
    game_state["votes"] = {} # Clear old votes
    
    # Generate a button for each player
    keyboard = []
    for uid, name in game_state["names"].items():
        # The callback_data stores the user_id of the suspect
        keyboard.append([InlineKeyboardButton(name, callback_data=str(uid))])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🚨 *INTERROGATION PHASE* 🚨\n\n"
        f"Question: *\"{game_state['current_question']}\"*\n\n"
        f"Someone answered: *\"{imposter_answer}\"*\n\n"
        f"Who do you think wrote this? Discuss and cast your vote below!",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Records a vote and updates the keyboard tallies."""
    query = update.callback_query
    voter_id = query.from_user.id
    suspect_id = int(query.data)

    # Record the vote
    game_state["votes"][voter_id] = suspect_id
    
    # Flash a temporary alert on the user's screen
    await query.answer(f"You voted for {game_state['names'][suspect_id]}!")

    # Tally all votes
    vote_counts = {}
    for v_id, s_id in game_state["votes"].items():
        vote_counts[s_id] = vote_counts.get(s_id, 0) + 1

    # Rebuild the keyboard with live vote counts
    keyboard = []
    for uid, name in game_state["names"].items():
        count = vote_counts.get(uid, 0)
        button_text = f"{name} ({count} votes)" if count > 0 else name
        keyboard.append([InlineKeyboardButton(button_text, callback_data=str(uid))])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Edit the original message to show the new tallies
    try:
        await query.edit_message_reply_markup(reply_markup=reply_markup)
    except:
        pass # Ignores errors if someone clicks the exact same button twice

async def reveal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reveals the true author of the answer."""
    if not game_state.get("imposter_id"):
        await update.message.reply_text("There is no active interrogation to reveal!")
        return

    imposter_name = game_state["names"][game_state["imposter_id"]]

    await update.message.reply_text(
        f"🎭 *THE TRUTH IS REVEALED!* 🎭\n\n"
        f"The answer was actually written by: *{imposter_name}*!\n\n"
        f"Type /endgame to clear the board.",
        parse_mode="Markdown"
    )

async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ends the current game and clears the stored state."""
    if update.message.chat.type == "private":
        await update.message.reply_text("Run this command in the Group Chat!")
        return

    # Clear out absolutely everything
    game_state["answers"] = {}
    game_state["names"] = {}
    game_state["current_question"] = ""
    game_state["imposter_id"] = None    # <--- ADD THIS
    game_state["votes"] = {}            # <--- ADD THIS
    
    await update.message.reply_text(
        "🛑 *GAME ENDED!* 🛑\n\n"
        "All previous answers have been cleared. Type /startgame whenever you're ready for a new round!",
        parse_mode="Markdown"
    )
def main():
    # Insert your BotFather token here
    application = Application.builder().token("8955952216:AAGQnW3XpFjppWW1aTYqYyXm6egy2bDNd8s").build()

    application.add_handler(CommandHandler("startgame", start_game))
    application.add_handler(CommandHandler("answer", answer))
    application.add_handler(CommandHandler("interrogate", interrogate))
    application.add_handler(CommandHandler("reveal", reveal))          # <-- New
    application.add_handler(CallbackQueryHandler(handle_vote))
    application.add_handler(CommandHandler("endgame", end_game))

    print(f"Bot is running! Loaded {len(QUESTIONS)} questions from file. Press Ctrl+C to stop.")
    application.run_polling()

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Simple dummy server to satisfy Render's web service port requirement
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    # Grabs Render's assigned port, defaults to 10000 locally
    port = int(os.environ.get("PORT", 10000))
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHandler)
    httpd.serve_forever()

# Run the web server in a background thread so it doesn't block the Telegram bot
threading.Thread(target=run_web_server, daemon=True).start()

if __name__ == '__main__':
    main()
