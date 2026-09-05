import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Data file paths
STORIES_FILE = "stories.json"
USERS_FILE = "users.json"

# Default genres
GENRES = [
    "Fantasy",
    "Sci-Fi",
    "Mystery",
    "Romance",
    "Adventure",
    "Horror",
    "Comedy",
    "Drama"
]

# Story starters for each genre
STORY_STARTERS = {
    "Fantasy": "🏰 Once upon a time, in a realm of eternal twilight...",
    "Sci-Fi": "🚀 In the year 2154, humanity's last hope was a lone spaceship...",
    "Mystery": "🔍 The old mansion had stood empty for 50 years, until last night...",
    "Romance": "💕 It was a rainy Tuesday when their eyes first met across the crowded café...",
    "Adventure": "🗺️ The ancient map was hidden in the attic, waiting to be discovered...",
    "Horror": "👻 The clock struck midnight, and the old house began to creak...",
    "Comedy": "😂 It all started when my cat learned to talk and demanded a raise...",
    "Drama": "🎭 The curtains rose on the final act, and the audience held their breath..."
}

# Data management functions
def load_data(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def load_stories():
    return load_data(STORIES_FILE)

def save_stories(stories):
    save_data(STORIES_FILE, stories)

def load_users():
    return load_data(USERS_FILE)

def save_users(users):
    save_data(USERS_FILE, users)

# Story management class
class StoryManager:
    def __init__(self):
        self.stories = load_stories()
        self.users = load_users()

    def create_story(self, story_id, user_id, genre, title):
        """Create a new story"""
        if story_id in self.stories:
            return False, "Story already exists!"
        
        starter = STORY_STARTERS.get(genre, "Once upon a time...")
        
        self.stories[story_id] = {
            "id": story_id,
            "title": title,
            "genre": genre,
            "starter": starter,
            "lines": [{"user_id": user_id, "text": starter, "timestamp": datetime.now().isoformat()}],
            "created_by": user_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "votes": {},
            "view_count": 0,
            "is_completed": False
        }
        save_stories(self.stories)
        return True, "Story created successfully!"

    def add_line(self, story_id, user_id, text):
        """Add a line to an existing story"""
        if story_id not in self.stories:
            return False, "Story not found!"
        
        story = self.stories[story_id]
        if story["is_completed"]:
            return False, "This story is completed and cannot be added to!"
        
        # Check if user has already contributed (prevent spam)
        user_contributions = [line for line in story["lines"] if line["user_id"] == user_id]
        if len(user_contributions) > 3:
            return False, "You've already contributed 3 lines to this story! Vote on others' contributions instead."
        
        # Add the line
        story["lines"].append({
            "user_id": user_id,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        story["last_updated"] = datetime.now().isoformat()
        save_stories(self.stories)
        
        # Update user stats
        self.update_user_stats(user_id, story_id)
        
        return True, "Line added successfully!"

    def get_story(self, story_id):
        """Get a story by ID"""
        return self.stories.get(story_id)

    def get_all_stories(self):
        """Get all stories"""
        return self.stories

    def get_genres(self):
        """Get available genres"""
        return GENRES

    def vote_line(self, story_id, user_id, line_index):
        """Vote on a line"""
        if story_id not in self.stories:
            return False, "Story not found!"
        
        story = self.stories[story_id]
        if line_index >= len(story["lines"]):
            return False, "Line not found!"
        
        # Initialize votes for this user if not exists
        if story_id not in self.users.get(str(user_id), {}).get("votes", {}):
            self.ensure_user_votes(user_id)
        
        # Check if user already voted on this story
        user_votes = self.users[str(user_id)]["votes"]
        if story_id in user_votes:
            return False, "You've already voted on this story!"
        
        # Add vote
        if "votes" not in story:
            story["votes"] = {}
        
        line_key = str(line_index)
        if line_key not in story["votes"]:
            story["votes"][line_key] = 0
        story["votes"][line_key] += 1
        
        # Record user vote
        user_votes[story_id] = line_index
        save_stories(self.stories)
        save_users(self.users)
        
        return True, "Vote recorded successfully!"

    def get_top_stories(self, limit=5):
        """Get top voted stories"""
        stories_with_votes = []
        for story_id, story in self.stories.items():
            total_votes = sum(story.get("votes", {}).values())
            stories_with_votes.append((story_id, story, total_votes))
        
        stories_with_votes.sort(key=lambda x: x[2], reverse=True)
        return stories_with_votes[:limit]

    def update_user_stats(self, user_id, story_id):
        """Update user statistics"""
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                "stories_created": 0,
                "lines_written": 0,
                "votes_received": 0,
                "stories_participated": [],
                "votes": {}
            }
        
        self.users[user_id]["lines_written"] += 1
        if story_id not in self.users[user_id]["stories_participated"]:
            self.users[user_id]["stories_participated"].append(story_id)
        save_users(self.users)

    def ensure_user_votes(self, user_id):
        """Ensure user has votes tracking"""
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                "stories_created": 0,
                "lines_written": 0,
                "votes_received": 0,
                "stories_participated": [],
                "votes": {}
            }
        elif "votes" not in self.users[user_id]:
            self.users[user_id]["votes"] = {}
        save_users(self.users)

# Initialize story manager
story_manager = StoryManager()

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message"""
    user = update.effective_user
    
    welcome_text = (
        f"📖 *Hi {user.first_name}! Welcome to The Interactive Storyteller!*\n\n"
        f"Together, we create epic tales! 🎨\n\n"
        f"*How it works:*\n"
        f"1️⃣ Start a new story with /newstory\n"
        f"2️⃣ Add a line with /addline [your text]\n"
        f"3️⃣ Read stories with /read\n"
        f"4️⃣ Vote on your favorite lines!\n\n"
        f"*Featured Commands:*\n"
        f"📝 /newstory - Begin a new adventure\n"
        f"➕ /addline - Add your line\n"
        f"📖 /read - Read current stories\n"
        f"🎭 /genres - See available genres\n"
        f"🏆 /top - Top voted stories\n"
        f"📊 /mystats - Your contributions\n"
        f"❓ /help - More details\n\n"
        f"✨ *Let's create something amazing together!*"
    )
    
    keyboard = [
        [InlineKeyboardButton("📝 New Story", callback_data="new_story")],
        [InlineKeyboardButton("📖 Read Stories", callback_data="read_stories")],
        [InlineKeyboardButton("🏆 Top Stories", callback_data="top_stories")],
        [InlineKeyboardButton("🎭 Genres", callback_data="genres")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def newstory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a new story"""
    user = update.effective_user
    
    # Check if user has a story in progress (limit to prevent spam)
    user_stories = [s for s in story_manager.stories.values() if s["created_by"] == user.id and not s["is_completed"]]
    if len(user_stories) >= 3:
        await update.message.reply_text(
            "❌ *You have too many active stories!*\n\n"
            "You can have up to 3 active stories at once.\n"
            "Complete or close one before starting another.",
            parse_mode="Markdown"
        )
        return
    
    # Show genre selection
    keyboard = []
    for genre in story_manager.get_genres():
        keyboard.append([InlineKeyboardButton(f"🎭 {genre}", callback_data=f"genre_{genre}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 *Choose a genre for your new story:*\n\n"
        "Select the type of story you want to create:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def addline_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a line to a story"""
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text(
            "❌ *Please provide your line!*\n\n"
            "Usage: `/addline Your story line here`\n\n"
            "Example: `/addline The dragon emerged from the mist`",
            parse_mode="Markdown"
        )
        return
    
    # Join all args into one text
    line_text = " ".join(context.args)
    
    # Check if there are active stories
    active_stories = [s for s in story_manager.stories.values() if not s["is_completed"]]
    if not active_stories:
        await update.message.reply_text(
            "❌ *No active stories found!*\n\n"
            "Start a new story with `/newstory` first.",
            parse_mode="Markdown"
        )
        return
    
    # If only one active story, add to it
    if len(active_stories) == 1:
        story = active_stories[0]
        success, message = story_manager.add_line(story["id"], user.id, line_text)
        if success:
            # Show the updated story
            await update.message.reply_text(
                f"✅ *Line added successfully!*\n\n"
                f"📖 *Story:* {story['title']}\n"
                f"📝 *Your line:* {line_text}\n\n"
                f"Use /read to see the full story!",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ *Failed to add line!*\n\n{message}",
                parse_mode="Markdown"
            )
        return
    
    # Multiple active stories - let user choose
    keyboard = []
    for story in active_stories:
        line_count = len(story["lines"])
        keyboard.append([InlineKeyboardButton(
            f"📖 {story['title']} ({line_count} lines)",
            callback_data=f"add_to_{story['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data="cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Store the line text in context for later use
    context.user_data['pending_line'] = line_text
    
    await update.message.reply_text(
        "📖 *Choose a story to add your line to:*\n\n"
        f"Your line: *{line_text}*\n\n"
        "Select which story you want to contribute to:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def read_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Read stories"""
    stories = story_manager.get_all_stories()
    
    if not stories:
        await update.message.reply_text(
            "📖 *No stories yet!*\n\n"
            "Be the first to start a story with `/newstory`!",
            parse_mode="Markdown"
        )
        return
    
    # Show list of stories
    keyboard = []
    for story_id, story in list(stories.items())[:10]:  # Show last 10
        line_count = len(story["lines"])
        status = "✅ Completed" if story["is_completed"] else "🔄 Active"
        keyboard.append([InlineKeyboardButton(
            f"📖 {story['title']} ({line_count} lines) - {status}",
            callback_data=f"read_{story_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📚 *Available Stories:*\n\n"
        "Select a story to read:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def genres_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available genres"""
    genres_text = "🎭 *Available Genres:*\n\n"
    
    for genre in story_manager.get_genres():
        # Count stories in this genre
        genre_stories = [s for s in story_manager.stories.values() if s["genre"] == genre]
        count = len(genre_stories)
        genres_text += f"• *{genre}* - {count} stories\n"
    
    genres_text += "\n💡 Start a new story with `/newstory` and choose your genre!"
    
    await update.message.reply_text(genres_text, parse_mode="Markdown")

async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show top voted stories"""
    top_stories = story_manager.get_top_stories(5)
    
    if not top_stories:
        await update.message.reply_text(
            "🏆 *No stories with votes yet!*\n\n"
            "Start voting on your favorite stories!",
            parse_mode="Markdown"
        )
        return
    
    top_text = "🏆 *Top Voted Stories*\n\n"
    
    for i, (story_id, story, votes) in enumerate(top_stories, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
        line_count = len(story["lines"])
        top_text += f"{medal} *{story['title']}*\n"
        top_text += f"   Genre: {story['genre']} | Lines: {line_count} | Votes: {votes}\n\n"
    
    top_text += "💡 Vote on stories by reading them and using the vote buttons!"
    
    await update.message.reply_text(top_text, parse_mode="Markdown")

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics"""
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id not in story_manager.users:
        await update.message.reply_text(
            "📊 *No stats yet!*\n\n"
            "Start contributing to stories to build your stats!",
            parse_mode="Markdown"
        )
        return
    
    stats = story_manager.users[user_id]
    
    stats_text = (
        f"📊 *Your Stats*\n\n"
        f"📝 Stories Created: {stats.get('stories_created', 0)}\n"
        f"✍️ Lines Written: {stats.get('lines_written', 0)}\n"
        f"👍 Votes Received: {stats.get('votes_received', 0)}\n"
        f"📚 Stories Participated: {len(stats.get('stories_participated', []))}\n"
        f"🗳️ Stories Voted On: {len(stats.get('votes', {}))}\n\n"
        f"💪 Keep writing and voting to become a legendary storyteller!"
    )
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message"""
    help_text = (
        "📖 *The Interactive Storyteller - Help*\n\n"
        "📝 *Commands:*\n"
        "• /start - Welcome menu\n"
        "• /newstory - Start a new story\n"
        "• /addline [text] - Add your line\n"
        "• /read - Read stories\n"
        "• /genres - See genres\n"
        "• /top - Top voted stories\n"
        "• /mystats - Your stats\n"
        "• /help - This menu\n\n"
        "🎯 *How to Play:*\n"
        "1. Start a story with /newstory\n"
        "2. Others add lines with /addline\n"
        "3. Vote on the best lines\n"
        "4. Watch the story grow!\n\n"
        "💡 *Tips:*\n"
        "• Keep lines short (max 200 chars)\n"
        "• Build on what others wrote\n"
        "• Be creative and fun!\n"
        "• Vote on lines you like\n\n"
        "⚠️ *Limits:*\n"
        "• 3 stories per user\n"
        "• 3 lines per story per user\n"
        "• 1 vote per story per user\n\n"
        "✨ *Let's create amazing stories together!*"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "new_story":
        await newstory_command(update, context)
        return
    
    elif query.data == "read_stories":
        await read_command(update, context)
        return
    
    elif query.data == "top_stories":
        await top_command(update, context)
        return
    
    elif query.data == "genres":
        await genres_command(update, context)
        return
    
    elif query.data == "back_to_menu":
        await start(update, context)
        return
    
    elif query.data == "cancel":
        if 'pending_line' in context.user_data:
            del context.user_data['pending_line']
        await query.edit_message_text(
            "✅ *Operation cancelled.*\n\n"
            "Send /start to begin again.",
            parse_mode="Markdown"
        )
        return
    
    # Handle genre selection
    elif query.data.startswith("genre_"):
        genre = query.data.replace("genre_", "")
        await query.edit_message_text(
            f"📝 *Creating a {genre} story*\n\n"
            f"Please send the title of your story in this format:\n"
            f"`/title Your story title here`\n\n"
            f"💡 Example: `/title The Dragon's Secret`",
            parse_mode="Markdown"
        )
        # Store genre in context
        context.user_data['selected_genre'] = genre
        return
    
    # Handle story title
    elif query.data.startswith("title_"):
        # This is handled by the title command
        pass
    
    # Handle adding to story
    elif query.data.startswith("add_to_"):
        story_id = query.data.replace("add_to_", "")
        pending_line = context.user_data.get('pending_line')
        
        if not pending_line:
            await query.edit_message_text(
                "❌ *No line to add!*\n\n"
                "Please use /addline first.",
                parse_mode="Markdown"
            )
            return
        
        success, message = story_manager.add_line(story_id, user_id, pending_line)
        if success:
            story = story_manager.get_story(story_id)
            await query.edit_message_text(
                f"✅ *Line added successfully!*\n\n"
                f"📖 *Story:* {story['title']}\n"
                f"📝 *Your line:* {pending_line}\n\n"
                f"Use /read to see the full story!",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"❌ *Failed to add line!*\n\n{message}",
                parse_mode="Markdown"
            )
        
        # Clean up
        if 'pending_line' in context.user_data:
            del context.user_data['pending_line']
        return
    
    # Handle reading story
    elif query.data.startswith("read_"):
        story_id = query.data.replace("read_", "")
        story = story_manager.get_story(story_id)
        
        if not story:
            await query.edit_message_text(
                "❌ *Story not found!*",
                parse_mode="Markdown"
            )
            return
        
        # Format the story
        story_text = f"📖 *{story['title']}*\n"
        story_text += f"🎭 Genre: {story['genre']}\n"
        story_text += f"👤 By: {story['created_by']}\n"
        story_text += f"📝 Lines: {len(story['lines'])}\n"
        story_text += f"{'─' * 30}\n\n"
        
        # Show lines
        for i, line in enumerate(story["lines"], 1):
            line_votes = story.get("votes", {}).get(str(i-1), 0)
            story_text += f"*{i}.* {line['text']}\n"
            story_text += f"   👍 {line_votes} votes\n\n"
        
        # Add voting buttons
        keyboard = []
        for i in range(len(story["lines"])):
            keyboard.append([InlineKeyboardButton(
                f"👍 Vote on Line {i+1}",
                callback_data=f"vote_{story_id}_{i}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Stories", callback_data="read_stories")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update story view count
        story["view_count"] += 1
        save_stories(story_manager.stories)
        
        # Check if message is too long (Telegram limit is 4096)
        if len(story_text) > 4000:
            story_text = story_text[:4000] + "...\n\n(Story truncated, use /read to see full)"
        
        await query.edit_message_text(
            story_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return
    
    # Handle voting
    elif query.data.startswith("vote_"):
        parts = query.data.split("_")
        story_id = parts[1]
        line_index = int(parts[2])
        
        success, message = story_manager.vote_line(story_id, user_id, line_index)
        
        if success:
            await query.edit_message_text(
                f"✅ *Vote recorded!*\n\n"
                f"Line {line_index + 1} got your vote! 👍",
                parse_mode="Markdown"
            )
            # Refresh the story view
            await read_command(update, context)
        else:
            await query.edit_message_text(
                f"❌ *Vote failed!*\n\n{message}",
                parse_mode="Markdown"
            )
        return

async def title_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set the title for a new story"""
    user = update.effective_user
    
    if not context.args:
        await update.message.reply_text(
            "❌ *Please provide a title!*\n\n"
            "Usage: `/title Your story title here`\n\n"
            "Example: `/title The Dragon's Secret`",
            parse_mode="Markdown"
        )
        return
    
    title = " ".join(context.args)
    genre = context.user_data.get('selected_genre')
    
    if not genre:
        await update.message.reply_text(
            "❌ *No genre selected!*\n\n"
            "Please use `/newstory` first to select a genre.",
            parse_mode="Markdown"
        )
        return
    
    # Create story ID
    story_id = f"{user.id}_{int(datetime.now().timestamp())}"
    
    success, message = story_manager.create_story(story_id, user.id, genre, title)
    
    if success:
        # Update user stats
        user_id = str(user.id)
        if user_id not in story_manager.users:
            story_manager.users[user_id] = {
                "stories_created": 0,
                "lines_written": 0,
                "votes_received": 0,
                "stories_participated": [],
                "votes": {}
            }
        story_manager.users[user_id]["stories_created"] += 1
        save_users(story_manager.users)
        
        await update.message.reply_text(
            f"✅ *Story created successfully!*\n\n"
            f"📖 *Title:* {title}\n"
            f"🎭 *Genre:* {genre}\n"
            f"📝 *Starter:* {STORY_STARTERS[genre]}\n\n"
            f"✨ *Share the story ID with others:* `{story_id}`\n\n"
            f"Add your first line with `/addline`!\n"
            f"Others can add to this story too!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ *Failed to create story!*\n\n{message}",
            parse_mode="Markdown"
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ *An error occurred!*\n\n"
            "Please try again or contact support.\n"
            "If this persists, try using /start to begin a new session.",
            parse_mode="Markdown"
        )

def main() -> None:
    """Start the bot"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("❌ No TELEGRAM_BOT_TOKEN found in environment variables!")
        return
    
    logger.info("🚀 Starting The Interactive Storyteller bot...")
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("newstory", newstory_command))
    application.add_handler(CommandHandler("addline", addline_command))
    application.add_handler(CommandHandler("read", read_command))
    application.add_handler(CommandHandler("genres", genres_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("mystats", mystats_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("title", title_command))
    
    # Add button callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start polling
    logger.info("✅ Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
