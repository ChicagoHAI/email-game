# 🚀 Deployment Guide for Email.io

## Deploy to Streamlit Community Cloud

### Prerequisites
- GitHub account
- Streamlit Community Cloud account (free)

### Steps

1. **Create GitHub Repository**
   ```bash
   # In your local project directory
   git init
   git add .
   git commit -m "Initial commit: Email.io game"
   
   # Create repo on GitHub and push
   git remote add origin https://github.com/YOUR_USERNAME/email-io-game.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Community Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository: `YOUR_USERNAME/email-io-game`
   - Set main file path: `experiments/email_game/app.py`
   - Click "Deploy!"

3. **Set Environment Variables**
   - In Streamlit Cloud dashboard, go to your app settings
   - Add secrets in the "Secrets" section:
   ```toml
   OPENAI_API_KEY_CLAB = "your-openai-api-key-here"
   ```

4. **Custom Domain (Optional)**
   - You can set a custom URL in the app settings
   - Format: `your-app-name.streamlit.app`

### Files Required for Deployment
- ✅ `app.py` - Main application
- ✅ `requirements.txt` - Dependencies
- ✅ `.streamlit/config.toml` - Configuration
- ✅ `README.md` - Documentation

### Environment Variables
The app looks for these environment variables:
- `OPENAI_API_KEY_CLAB` - Your OpenAI API key (required)

### Troubleshooting
- **Import errors**: Check `requirements.txt` has all dependencies
- **API key errors**: Verify the secret is set correctly in Streamlit Cloud
- **File not found**: Ensure the main file path is correct in deployment settings

### Alternative Deployment Options
- **Railway**: Great for more complex deployments
- **Heroku**: Classic platform (requires Procfile)
- **DigitalOcean App Platform**: Good performance
- **Google Cloud Run**: For enterprise usage 