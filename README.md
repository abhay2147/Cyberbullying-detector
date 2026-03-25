# 🛡️ Cyberbullying Detection Discord Bot

A Discord bot that automatically detects and removes cyberbullying messages using a fine-tuned DistilBERT model.

## Features
- 🤖 AI-powered cyberbullying detection (DistilBERT)
- 🗑️ Auto-deletes flagged messages
- ⚠️ Warns users via DM
- ⏰ Auto-timeout after 3 violations
- 📊 Mod logging to #mod-logs channel

## Bot Commands
| Command | Who | Description |
|---|---|---|
| `!check <text>` | Everyone | Test if a message is cyberbullying |
| `!botstatus` | Everyone | Show bot settings |
| `!violations` | Mods | See top violators |
| `!reset @user` | Mods | Reset a user's violations |
| `!sensitivity 0.6` | Admins | Change detection threshold |

## Setup
1. Clone this repo
2. Install dependencies: `pip install -r requirements.txt`
3. Train the model by running the Colab notebook
4. Paste your Discord bot token into `bot.py`
5. Run: `python bot.py`

## Model
- Base: `distilbert-base-uncased`
- Fine-tuned on cyberbullying/hate speech datasets
- Accuracy: ~96% on test set

## Built with
- 🤗 HuggingFace Transformers
- 🔥 PyTorch
- 🤖 discord.py
